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
