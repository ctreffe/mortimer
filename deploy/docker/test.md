# Mortimer Dockerization Testing Guide

This guide complements `deploy/docker/plan.md` by outlining how to verify that each implementation phase has been completed correctly. Run the checks in order; later phases often rely on artifacts introduced earlier.

## General prerequisites

- You have the repository cloned and are operating from its root (`/Users/johannesbrachem/Documents/git/mortimer`).
- Required tooling is installed: Docker Desktop (with Compose v2), Python 3.13 with `uv`, Node-less shell utilities (`bash`, `grep`, `jq`), and access to the GitHub Actions environment if CI steps need validation.
- Ensure the working tree is clean so test artifacts are obvious.

---

## Phase 0 – Repository & Secrets Preparation

### Phase 0 Preconditions

- `.env` file exists at the repo root and contains production-ready values.
- A sanitized template (for example `.env.template`) is available for distribution.

### Phase 0 Validation steps

1. Confirm required Mortimer variables are present and non-empty:

   ```bash
   cd /Users/johannesbrachem/Documents/git/mortimer
   grep -E '^(MORTIMER_SECRET_KEY|ALFRED_DB_NAME|MORTIMER_MONGO_URI|MAIL_SERVER)=' .env
   ```

   Verify that each key prints a value (no trailing `=` without content).

2. Verify TLS placeholder paths are not blank:

   ```bash
   grep -E 'TLS_(CERT|KEY)_PATH=' .env
   ```

   Ensure the values point to valid files or clearly documented placeholders (e.g., `/etc/ssl/certs/mortimer.crt`).

3. Check that the sanitized template omits secrets but retains the full key list:

   ```bash
   diff -u <(grep -v '^#' .env | cut -d= -f1 | sort) \
           <(grep -v '^#' .env.template | cut -d= -f1 | sort)
   ```

   The diff should be empty; if not, align the template.

4. Confirm the TLS strategy is documented for both development and production by locating the relevant section in `deploy/docker/README.md`:

   ```bash
   rg "TLS" deploy/docker/README.md
   ```

   Ensure instructions mention self-signed certificates for local use and Let’s Encrypt + Certbot for production.

### Phase 0 Acceptance criteria

- `.env` contains every required key with sensible defaults.
- A template exists and matches the key list.
- Documentation spells out certificate handling.

---

## Phase 1 – Mortimer Application Image

### Phase 1 Preconditions

- `deploy/docker/Dockerfile`, `deploy/docker/gunicorn.conf.py`, `deploy/docker/wsgi.py`, and the entrypoint script are present.
- `deploy/docker/uv.app.lock` (or equivalent lock file) exists.

### Phase 1 Validation steps

1. Build the image:

   ```bash
   cd /Users/johannesbrachem/Documents/git/mortimer
   docker build -f deploy/docker/Dockerfile -t mortimer-app:test .
   ```

   The build should succeed without copying the local source tree (verify layers reference only wheels).

2. Inspect the image for the virtual environment:

   ```bash
   docker run --rm mortimer-app:test python -c "import sys; print(sys.prefix)"
   ```

   Output should point to `/opt/venv` or the documented venv path.

3. Confirm Gunicorn config is available and logs to stdout:

   ```bash
   docker run --rm mortimer-app:test ls /app/gunicorn.conf.py
   docker run --rm mortimer-app:test grep accesslog /app/gunicorn.conf.py
   ```

4. Validate the entrypoint waits for Mongo:

   ```bash
   docker run --rm --entrypoint sh mortimer-app:test -c "grep -n MongoClient /app/entrypoint.sh"
   ```

   Ensure logic exists to probe Mongo readiness.

### Phase 1 Acceptance criteria

- Image builds successfully using the lock file.
- Runtime assets (Gunicorn config, WSGI wrapper, entrypoint) are present and configured per plan.

---

## Phase 2 – Docker Compose Update

### Phase 2 Preconditions

- `deploy/docker/docker-compose.yml` includes the new services and networks.

### Phase 2 Validation steps

1. Lint the Compose file:

   ```bash
   cd /Users/johannesbrachem/Documents/git/mortimer/deploy/docker
   docker compose config
   ```

   Command should output the merged configuration without errors.

2. Ensure `mongo` has no published ports:

   ```bash
   docker compose config --services | xargs -I{} sh -c 'echo "--- {}"; docker compose config | yq ".services."{}".ports"'
   ```

   For `mongo`, the result should be `null`.

3. Verify `mortimer-app` joins both networks and uses the health check:

   ```bash
   docker compose config | yq '.services."mortimer-app".networks'
   docker compose config | yq '.services."mortimer-app".healthcheck'
   ```

4. Run the stack and confirm Mongo is internal-only:

   ```bash
   docker compose up -d mongo mortimer-app
   nc -z localhost 27017 && echo "unexpected port" || echo "port closed as expected"
   docker compose logs mortimer-app | grep "Waiting for Mongo"
   docker compose down
   ```

### Phase 2 Acceptance criteria

- Compose validates cleanly.
- Mongo is not exposed publicly, and `mortimer-app` health checks are wired.

---

## Phase 3 – Nginx Reverse Proxy

### Phase 3 Preconditions

- `mortimer-nginx` service and config files exist (`deploy/docker/nginx/conf.d/mortimer.conf`).
- TLS cert mount points are defined.

### Phase 3 Validation steps

1. Syntax-check the Nginx config:

   ```bash
   docker run --rm -v $(pwd)/nginx/conf.d:/etc/nginx/conf.d:ro -v $(pwd)/nginx/certs:/etc/nginx/certs:ro nginx:alpine nginx -t
   ```

2. Bring up app + proxy and verify reverse proxying:

   ```bash
   docker compose up -d
   curl -k https://localhost/healthz
   docker compose logs mortimer-nginx --since 30s
   docker compose down
   ```

   Expect a `200 OK` from `/healthz` and Nginx access logs.

3. Confirm static files are served directly:

   ```bash
   docker compose up -d mortimer-app mortimer-nginx
   curl -kI https://localhost/static/main.css | grep -E "HTTP/|Cache-Control"
   docker compose down
   ```

4. If TLS certs are self-signed, confirm the README documents acceptance instructions for browsers.

### Phase 3 Acceptance criteria

- Nginx config passes `nginx -t`.
- HTTPS requests succeed and static assets return cached responses.

---

## Phase 4 – CI/CD & Image Publishing

### Phase 4 Preconditions

- `docker-compose.override.yml` (and optional HTTP override) exists.
- GitHub Actions workflow file (e.g., `.github/workflows/docker.yml`) is present.

### Phase 4 Validation steps

1. Validate override file for local dev:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.override.yml config | yq '.services."mortimer-app".volumes'
   ```

   Ensure source code is bind-mounted and reload command is in place.

2. Run local dev stack to confirm reload path works:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.override.yml up
   ```

   Modify a template and observe auto-reload (Ctrl+C afterwards).

3. Dry-run the GitHub Actions workflow locally with `act` (optional) or inspect key steps:

   ```bash
   yq '.jobs.build.steps[].name' .github/workflows/docker.yml
   ```

   Ensure build, test, `docker buildx`, push, and optional Trivy steps exist.

4. Confirm workflow references registry secrets only via `secrets.` prefix.

### Phase 4 Acceptance criteria

- Overrides support developer workflows without altering production config.
- CI workflow defines build, test, push, and scanning stages using secrets appropriately.

---

## Phase 5 – Observability & Ops Hardening

### Phase 5 Preconditions

- Logging guidance implemented (stdout, optional volumes).
- Backup automation scripts or Compose services exist.
- Certbot companion configuration available.

### Phase 5 Validation steps

1. Inspect logging behavior:

   ```bash
   docker compose up -d
   docker compose logs -f mortimer-app --since 10s &
   sleep 5
   curl -k https://localhost/healthz
   pkill -f "docker compose logs"
   docker compose down
   ```

   Ensure access/errors appear in stdout without buffering.

2. Check README contains log access instructions and structured logging notes:

   ```bash
   rg "log operations" -n deploy/docker/README.md
   ```

3. Test the backup job (if modeled as a service):

   ```bash
   docker compose run --rm mongo-backup backup
   ls deploy/docker/backups
   ```

   Confirm an archive is produced and encrypted if required.

4. Verify the Certbot companion shares the cert volume and renew hook:

   ```bash
   docker compose config | yq '.services."nginx-certbot".volumes'
   docker compose config | yq '.services."nginx-certbot".command'
   ```

### Phase 5 Acceptance criteria

- Logs flow via stdout and docs explain access patterns.
- Backup job produces encrypted artifacts with retention notes.
- Certbot container configuration matches renewal expectations.

---

## Phase 6 – Validation & Documentation

### Phase 6 Preconditions

- `deploy/docker/README.md` is updated with architecture, configuration matrices, playbooks, troubleshooting, and readiness review.

### Phase 6 Validation steps

1. Confirm architecture summary exists:

   ```bash
   rg "Architecture" -n deploy/docker/README.md
   ```

   Ensure the section documents services, ports, networks, and volumes.

2. Walk through the smoke test instructions end-to-end:

   ```bash
   docker compose down --volumes
   docker compose up -d
   docker compose ps
   docker compose logs --since 1m
   curl -k https://localhost
   docker compose exec mortimer-nginx curl -sS https://localhost/healthz
   docker compose down
   ```

   Record results in a test log.

3. Review the troubleshooting appendix for completeness (covers Gunicorn bind issues, Mongo auth errors, certbot limits, platform quirks).

4. Verify readiness review checklist is present and linked from the top-level `README.md`.

### Phase 6 Acceptance criteria

- Documentation fully reflects the deployed stack.
- Smoke test passes without manual edits.
- Troubleshooting guidance exists and is discoverable.

---

## Sign-off

Once all phases pass their respective checks, record the run date, Git commit SHA, and any deviations in your release notes. Re-run critical phases (1–3 and 5) after major dependency upgrades or infrastructure changes.
