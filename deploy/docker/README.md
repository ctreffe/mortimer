# Mortimer Docker assets

This directory contains Docker resources for running Mortimer with a properly
configured MongoDB instance. The focus here is providing a secure, reusable
MongoDB service that mirrors production expectations. A follow-up step can add
the Mortimer web application container to the same stack.

## Files

- `docker-compose.yml` – spins up a MongoDB 7 container with authentication,
  health checks, and persistent storage.
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

1. Start MongoDB:

   ```bash
   docker compose up -d
   ```

  MongoDB will bind to `localhost:${HOST_MONGO_PORT:-27017}`. Data lives in the
  named volume `mortimer-mongo-data`.

1. Inspect the logs if you want to confirm the initialization ran:

   ```bash
   docker compose logs mongo
   ```

1. When you are done:

   ```bash
   docker compose down
   ```

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

  The script attaches the container to the `mortimer-net` network, injects the
  environment variables from `.env`, and forwards port `8000` to the host.

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

- Create an application image for Mortimer (multi-stage build containing the
  Python project and static assets) and add it as a service to the compose file.
- Provide an Nginx or Caddy reverse proxy for TLS termination.
- Externalize configuration through environment variables or mounted config
  files.
- Add backup/restore automation for the MongoDB volume.
- Wire up monitoring/metrics (e.g., integrate with MongoDB exporter or logs).
