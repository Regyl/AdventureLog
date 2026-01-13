# AIO (All-In-One) deployment

This folder contains a simple all-in-one Docker setup that runs the AdventureLog frontend and backend inside a single container, fronted by nginx.

Files:

- `Dockerfile` – builds an image with Node + Python, builds the frontend and installs backend deps.
- `nginx.conf` – proxies `/api`, `/docs`, `/accounts`, `/admin`, `/media` to Django and everything else to the frontend node server.
- `supervisord.conf` – runs `nginx`, `gunicorn`, `node build`, `memcached`, and a small sync worker.
- `entrypoint.sh` – waits for Postgres, runs migrations, optionally creates a superuser, and runs `download-countries`.
- `docker-compose.yml` – example compose file to run `aio` and `db`.
- `.env.example` – example environment variables for the AIO deployment.

How to build and run (from repo root):

```bash
cp aio/.env.example aio/.env
cd aio
docker compose up --build -d
```

Notes:

- This setup intentionally copies project sources into the image and builds the frontend inside the image. It is designed to be simple and self-contained.
- The image exposes one port (`80`) and nginx reverse-proxies to the internal Node and Django processes.
