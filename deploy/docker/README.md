# Mortimer Docker assets

This directory contains Docker resources for running Mortimer with a properly
configured MongoDB instance. Phase 1 produced the Mortimer application image; in
Phase 2 the compose stack now wires it together with MongoDB.

## Files

- `docker-compose.yml` – starts MongoDB 7 **and** the Mortimer Gunicorn image,
  wiring them onto private/internal networks. It also provisions named
  volumes for MongoDB data, Mortimer's writable instance folder (experiment
  files), optional user uploads, and Mortimer's rotating logs so this state
  survives container rebuilds.
- `.env.example` – template for the environment variables consumed by the
  Compose file. Copy it to `.env` and adjust the secrets before starting the
  stack.
- `initdb/001-create-databases.js` – initialization script executed by MongoDB
  on first launch. It creates the Mortimer and Alfred databases and provisions
  a single Mortimer application user with `readWrite` on the Mortimer database
  plus `read` and `userAdmin` on the Alfred database.

The `docker-compose.yml` mounts the `initdb/` directory into the container at
`/docker-entrypoint-initdb.d`. The official MongoDB image automatically runs all
scripts in that folder the first time a fresh data directory is used, which is
why no manual step is required to trigger `001-create-databases.js`.

## Usage

1. Copy the example environment file and edit secrets:

    ```bash
    cp .env.example .env
    # then edit .env to set strong passwords
    ```

1. Build the Mortimer image (from the repository root):

  ```bash
  docker compose -f deploy/docker/docker-compose.yml build mortimer-app
  ```

1. Start the application stack (from this folder):

  ```bash
  docker compose up -d mortimer-app
  ```

  This starts both `mortimer-app` and `mongo`. Mortimer is reachable at
  `http://localhost:${MORTIMER_APP_PORT:-8000}` (exposed for Phase 2 testing;
  once Nginx is added the host binding will move to the proxy). Runtime
  state is stored in named volumes:

- `mortimer-mongo-data` → MongoDB databases
- `mortimer-instance` → Mortimer instance folder (`/app/instance`) that stores
  experiments and uploaded resources
- `mortimer-uploads` → legacy `/app/uploads` directory (kept for future UI
  features)
- `mortimer-logs` → Mortimer and Alfredo log files under `/app/log`

1. Inspect the logs if you want to confirm the initialization ran:

    ```bash
    docker compose logs mongo
    ```

1. When you are done:

    ```bash
    docker compose down
    ```

## Persistent storage locations

Docker keeps the named volumes declared in `docker-compose.yml` even if you
stop and remove the containers, so Mortimer's experiment directories and logs
survive restarts. To inspect them, list the volumes and mount any of them
temporarily, for example:

```bash
docker volume ls | grep mortimer
docker run --rm -it -v mortimer-instance:/data alpine ls /data
```

If you prefer binding to a host directory instead, edit the volume mapping for
`mortimer-instance` (and optionally the uploads/log volumes) to point to an
absolute path on the host.

## Phase 1 Mortimer smoke test

Once MongoDB is healthy you can exercise the Mortimer application image that
the Phase 1 work produced.

1. Build the image from the repository root (one directory above this README):

    ```bash
    docker build -f deploy/docker/Dockerfile -t mortimer-app:v1 .
    ```

1. Run a throwaway container on the same Docker network as MongoDB:

    ```bash
    cd deploy/docker
    sh test.sh
    ```

  The script invokes `docker compose up --build mortimer-app`, bringing up both
  services on the compose-defined networks and forwarding port `8000` to the
  host for the foreground run.

1. Visit `http://localhost:8000/login` in your browser. On the first run the
  app redirects `/` to `/login`, so browsing directly to the login page avoids
  the appearance of a blank screen while your browser follows the redirect.

1. Create the initial Mortimer account at `http://localhost:8000/register`. Use
  the parole password from `.env` (default: `changeme`) along with the email
  and password you want for the administrator. After registration you can log
  in and access the dashboard.

If you want to stop the app container, interrupt the `test.sh` script or run
`docker stop <container-name>` in another terminal.

## Connecting Mortimer locally

In your local `mortimer.conf`, point the `MONGODB_SETTINGS` to the database and
user created by the init script (defaults shown). The same credentials cover
both the Mortimer application database and the `alfred` database used for
experiment data. The user has `readWrite` on the Mortimer database and `read`
plus `userAdmin` on Alfred so Mortimer can manage per-experiment accounts:

```python
MONGODB_SETTINGS = {
    "host": "localhost",
    "port": 27017,
    "db": "mortimer",
    "username": "mortimer_app",
    "password": "changeMeToo!",  # replace with the value from .env
    "authentication_source": "mortimer",
    "ssl": False,
}
```

## Next steps for full dockerization

- Provide an Nginx or Caddy reverse proxy for TLS termination.
- Externalize configuration through environment variables or mounted config
  files.
- Add backup/restore automation for the MongoDB volume.
- Wire up monitoring/metrics (e.g., integrate with MongoDB exporter or logs).
