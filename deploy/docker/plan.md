# Mortimer Dockerization Plan

## 1. Goals & Success Criteria

- Serve the Mortimer Flask application with Gunicorn behind an Nginx reverse proxy.
- Keep MongoDB reachable only on an internal Docker network while allowing Mortimer to connect to it.
- Supply a reproducible, environment-driven stack that can run both locally and in production with minimal changes.
- Provide observability hooks (logs, health checks) and clear upgrade paths for dependencies.

## 2. Target Architecture

- **Services**
  - `mongo`: official MongoDB image with authentication bootstrap (already exists).
  - `mortimer-app`: custom Mortimer image running Gunicorn.
  - `mortimer-nginx`: lightweight Nginx image terminating HTTP(S) and proxying to Gunicorn.
- **Networks**
  - `mortimer-internal` (internal/private) – shared by `mongo` and `mortimer-app`, `internal: true` so it is not exposed to Docker host.
  - `mortimer-edge` – shared by `mortimer-nginx` and `mortimer-app`; Nginx publishes ports on the host, Gunicorn stays internal.
- **Volumes**
  - Reuse `mongo-data` for persistent database storage.
  - New `mortimer-static` (optional) for collected static files if needed by Nginx.
  - Bind-mounted config/templates for local iteration only (toggle via Compose override file).

## 3. Implementation Phases

### Phase 0 – Repository & Secrets Preparation

1. Audit `.env` to ensure it covers all Mortimer and Mongo settings (no blank TLS paths, production-ready defaults).
2. Document how the single `.env` file is prepared for production (sanitized template, secure distribution, secret storage strategy such as Docker secrets or an external secret manager).
3. Decide on TLS certificate handling: use self-signed certificates for local development, and in production run an Nginx+Certbot companion to obtain Let’s Encrypt certificates, storing them in a shared `certs` volume with appropriate permissions.

### Phase 1 – Mortimer Application Image

1. Create `Dockerfile` (multi-stage):
   - Before building, generate a container-specific lock file (e.g., `deploy/docker/uv.app.lock`) by writing `mortimer==<release>` to `deploy/docker/requirements.app.in` and running `uv pip compile --python 3.13 --output deploy/docker/uv.app.lock deploy/docker/requirements.app.in` so the dependency resolves to the PyPI release rather than the editable source tree.
   - **Builder stage**: install minimal build requirements, copy the container lockfile, create a virtual environment with `uv venv`, and run `uv pip sync` so the published `mortimer` wheel (and dependencies) are pulled from PyPI without copying local source code.
   - **Runtime stage**: start from a slim Python base image, copy the prepared `/opt/venv`, add a non-root `mortimer` user, set `PATH`, and include runtime assets such as Gunicorn configuration and the entrypoint script.
   - If static assets need to be mounted by Nginx, ensure they are available from the installed package path.
2. Add Gunicorn configuration (`deploy/docker/gunicorn.conf.py`): bind to `0.0.0.0:8000`, derive worker count from `WEB_CONCURRENCY` (fallback `cpu_count * 2 + 1`), optionally set `threads = 2`, keep worker class `sync`, set `timeout = 60`/`graceful_timeout = 30`, log to stdout (`accesslog = "-"`, `errorlog = "-"`, `loglevel` from env), and allow proxy headers with `forwarded_allow_ips = "*"` (production reload disabled). Ship a dedicated WSGI module (e.g., `deploy/docker/wsgi.py`) that instantiates `app = create_app(instance_path=..., logfile=...)` using environment-driven paths, so Gunicorn loads `mortimer_docker.wsgi:app` instead of calling the factory directly.
3. Provide entrypoint script that:
   - Loads environment variables (already injected by Compose) and prints a concise startup banner/version.
   - Waits for MongoDB readiness with exponential backoff using `pymongo.MongoClient(...).admin.command("ping")` before starting the app (honouring `MORTIMER_MONGO_*`).
   - Optionally seeds static assets or instance folders if missing (create `/app/instance`, ensure log directory writable).
   - Runs any lightweight sanity checks (e.g., ensure `ALFRED_DB_NAME` is set) and exits with clear errors if configuration is incomplete.
   - Finally execs `gunicorn "mortimer_docker.wsgi:app" --config /app/gunicorn.conf.py` so PID 1 belongs to Gunicorn, signals propagate properly, and the application factory receives the correct arguments.
4. Ensure the container relies entirely on environment variables (injected via Compose `env_file`) by documenting the required keys (`MORTIMER_SECRET_KEY`, Mongo credentials, mail settings, `ALFRED_DB_NAME`, etc.) and validating them in the entrypoint with friendly error messages if any are missing.

### Phase 2 – Docker Compose Update

1. Add `mortimer-app` service:
   - `build: { context: ../.., dockerfile: deploy/docker/Dockerfile }`.
   - `env_file: .env` to reuse existing secrets.
   - `depends_on: { mongo: { condition: service_healthy } }`.
   - `networks: [mortimer-internal, mortimer-edge]` (Gunicorn listens on the edge network; Mongo traffic stays on the internal network).
   - `volumes`:
     - `mortimer-static:/app/static:ro` (read-only once assets are baked into the image).
     - `mortimer-uploads:/app/uploads` (optional persistent user uploads volume).
     - Mount `/app/log` only if log files must be extracted; prefer stdout logging by default.
   - `healthcheck`: `CMD-SHELL` running `curl -f http://localhost:8000/healthz || exit 1` with `interval: 30s`, `timeout: 5s`, `retries: 3`.
2. Modify `mongo` service:
   - Join only `mortimer-internal` network so the database is unreachable from the host by default.
   - Remove published port; rely on `docker compose exec mongo mongosh` for admin work.
   - Document an optional `docker-compose.override.yml` that re-adds `ports: ["27017:27017"]` for local debugging only.
3. Define networks section:

   ```yaml
   networks:
     mortimer-internal:
       internal: true
     mortimer-edge:
       driver: bridge
   ```

### Phase 3 – Nginx Reverse Proxy

1. Add `mortimer-nginx` service using official `nginx:alpine` image.
2. Create `deploy/docker/nginx/conf.d/mortimer.conf` with:
   - `upstream mortimer` pointing to `mortimer-app:8000` and `server` blocks for HTTP (redirect) and HTTPS.
   - Proxy headers for Flask (`X-Forwarded-For`, `X-Forwarded-Proto`, `Host`) and buffering disabled for streaming endpoints.
   - gzip/static caching rules where appropriate; serve `/static` directly from `mortimer-static` volume with cache headers.
   - TLS configuration (cert/key mounted from secret/volume) with HTTP→HTTPS redirect and automatic reload when certbot renews files.
3. Mount configuration via volume:

   ```yaml
   volumes:
     - ./nginx/conf.d:/etc/nginx/conf.d:ro
     - ./nginx/certs:/etc/nginx/certs:ro   # optional for TLS
     - mortimer-static:/srv/mortimer/static:ro
   ```

4. Publish ports `80:80` (and `443:443` if TLS).
5. Add healthcheck hitting `http://localhost/healthz` (returns from Gunicorn via upstream) to ensure both proxy and app are reachable.

### Phase 4 – CI/CD & Image Publishing

1. Write `docker-compose.override.yml` for local development (bind-mount source code, enable Flask auto-reload through a development service if needed).
   - Mount project source into the app container (`.:/workspace`) and set `command: flask run --reload` or a debug-specific entrypoint.
   - Re-expose Mongo on `localhost:27017` for quick inspection.
   - Mount self-signed certificates (generated once via helper script) and reuse the same HTTPS nginx config, keeping parity with production; optionally offer an additional `docker-compose.http.yml` override for developers who prefer plain HTTP.
2. Create GitHub Actions workflow to build and push images (`mortimer-app`, optionally `mortimer-nginx`) on tagged releases.
   - Steps: checkout → set up Python + uv → run tests/lint → build multi-arch image with `docker buildx bake` → push to registry → deploy manifest.
   - Reference registry credentials stored as GitHub Actions secrets (`REGISTRY_USERNAME`, `REGISTRY_PASSWORD`)—never commit them—and optionally sign images with cosign.
3. Optionally integrate container scanning (Trivy/Grype) before publishing.
   - Add a `trivy image --severity HIGH,CRITICAL` step that fails the build on actionable vulnerabilities.

### Phase 5 – Observability & Ops Hardening

1. Configure logging streams end-to-end:
   - Keep Gunicorn `accesslog = "-"` and `errorlog = "-"` so everything flows to stdout/stderr, and document how application-level logging already propagates through Gunicorn handlers.
   - In `mortimer-app`, ensure the entrypoint exports `PYTHONUNBUFFERED=1` (or `--capture-output` on Gunicorn) to avoid buffered logs.
   - Mount `/var/log/nginx` only in development; in production rely on Nginx’s default stdout/stderr streams so Compose or the orchestrator can ship logs to CloudWatch, Loki, or ELK. Note retention expectations (e.g., `docker logs --since 24h`).
   - Call out that any optional file-based logs must live on a writable volume (`mortimer-logs`) and rotated via `logrotate` or a sidecar.
2. Document day-to-day log access:
   - Add a short “log operations” section to `deploy/docker/README.md` showing `docker compose logs -f mortimer-app`, `docker compose logs -f mortimer-nginx`, and filtered variants (`--since`/`--tail`).
   - Mention structured logging hooks: if future integrations (Datadog, Sentry breadcrumbs) are enabled, they should be wired via environment variables (`LOG_FORMAT=json`) so no compose changes are required.
   - Encourage using `docker compose cp` or `docker compose exec` only for historical log files when a persistent volume is attached.
3. Harden health and metrics exposure:
   - Keep `/healthz` served by the Flask app but restrict external access via Nginx (e.g., `location /healthz { allow 127.0.0.1; allow mortimer-app; deny all; proxy_pass http://mortimer; }`).
   - Document optional Prometheus-style metrics: either enable Gunicorn’s `statsd`/`prometheus` integration via an environment flag or expose a `/metrics` endpoint guarded by basic auth.
   - Extend Compose healthchecks to cover TLS (`wget --no-verbose --spider https://mortimer-nginx/healthz || exit 1`) once certificates are provisioned.
4. Plan database backup and restore workflows:
   - Ship a lightweight `mongo-backup` service (or GitHub Action) that runs `mongodump --uri "$MONGO_BACKUP_URI" --archive=/backup/$(date +%F).gz` on a nightly cron (`restart: no` + `command: ["sh", "-c", "crond -f"]`).
   - Store archives in a dedicated volume or sync them to S3 using `aws s3 cp` with credentials injected via secrets; keep at least the last seven nightly snapshots and one monthly snapshot.
   - Document manual restore steps (`mongorestore --drop --archive=...`) and include them in `deploy/docker/README.md`, highlighting that restores must run against a maintenance environment before production.
   - For local development, provide a helper script to seed from the newest backup (`docker compose run mongo-backup restore latest`).
5. Automate TLS certificate renewal:
   - Add an `nginx-certbot` companion container (e.g., `docker-compose.certbot.yml`) that shares the `mortimer-nginx` `certs` volume, runs `certbot renew --deploy-hook "nginx -s reload"`, and bootstraps certificates via HTTP-01 challenge.
   - Document the initial `certbot certonly` command and DNS prerequisites (A records for production hostnames) in Phase 0/README.
   - For staging or air-gapped environments, describe using Let’s Encrypt’s staging endpoint or pre-provisioned certs copied into the same volume.

### Phase 6 – Validation & Documentation

1. Update `deploy/docker/README.md` with authoritative operator guidance:
   - Start with an architecture diagram/table that maps each service → image → ports → networks → volumes so new engineers can reason about connectivity quickly.
   - Include a configuration matrix that explains how `.env`, Compose overrides, and GitHub Actions secrets fit together; explicitly note required environment variables, default values, and which ones are safe to share in a template.
   - Provide separate quick-start paths for local (`docker compose -f docker-compose.yml -f docker-compose.override.yml up`) and production (registry-pulled images, certbot companion) while keeping the instructions DRY.
   - Document how to rotate secrets, recycle containers, and where to find static/log volumes; link back to Phases 1–5 for deeper technical details.
2. Codify smoke-test playbooks:
   - Describe the exact pre-flight checks (self-signed cert generation, ensuring `.env` matches expected keys, cleaning stale volumes with `docker compose down --volumes` when necessary).
   - Provide a canonical happy-path test flow: `docker compose up -d`, confirm container health via `docker compose ps` and `docker compose logs --since 1m`, hit `https://localhost` (accepting the self-signed cert) to verify the UI, and curl `https://localhost/healthz` from inside the Nginx container to confirm proxy wiring.
   - Add optional regression checks such as running `pytest tests/test_utils.py` on the host before building images, validating that static assets load without 404s, and verifying Mongo stays internal by attempting (and failing) to connect from the host.
   - Encourage writing a short checklist in the README that teams can reuse during release cut-overs or DR drills.
3. Author a troubleshooting appendix:
   - Enumerate common container issues (Gunicorn port already bound, Mongo authentication failures, certbot rate limits, Nginx `502 Bad Gateway`) and pair each with diagnostic commands (`docker compose logs mortimer-app`, `docker compose exec mongo mongosh`, etc.) and remediation steps.
   - Call out platform-specific quirks (e.g., macOS file permission mapping, SELinux relabeling on Linux hosts, Docker Desktop memory limits) with succinct fixes.
   - Provide a decision tree for unhealthy containers: check environment variables → inspect logs → retry with `docker compose down && docker compose up` → escalate to rebuild images.
   - Document how to recover from failed deployments in CI/CD (rollback to previous image tag, re-run certbot issuance, restore Mongo from latest snapshot).
4. Close the phase with a readiness review: ensure all docs are peer-reviewed, link them from the top-level `README.md`, and capture follow-up tasks (e.g., move observability items into a backlog ticket if not implemented immediately).

## 5. Decisions & Follow-ups

- **Background workers:** No dedicated Celery/RQ worker is required right now—the application performs all work synchronously within request/response cycles, and the codebase contains no long-running jobs. Revisit if exports or email workflows begin timing out; if that happens, add a queue-backed worker service (e.g., Celery with Redis) and surface it as a separate Compose service.
- **Static assets:** Continue baking static files into the `mortimer-app` image (they live under `mortimer/static` and are small). Nginx can serve them directly from the installed package path or the shared `mortimer-static` volume; only user uploads should live on a writable volume or external storage.
- **Production TLS:** Standardize on an `nginx-certbot` companion container that shares the `certs` volume, issues Let’s Encrypt certificates via HTTP-01, and renews automatically with an `nginx -s reload` deploy hook. Use the staging endpoint for dry runs and document the DNS prerequisites in the README.
- **Backups & logs compliance:** Treat Mongo dumps and logs as potentially sensitive research data—encrypt backups at rest (e.g., S3 with SSE or GPG), restrict access via secrets, and keep a retention window aligned with institutional policy (default 30–90 days for logs, seven rolling nightly DB snapshots plus monthly archives). Add a note in the README to confirm final retention/erasure rules with the data protection officer.
