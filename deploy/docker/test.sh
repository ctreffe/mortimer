docker run --rm \
  --network mortimer-net \
  --env-file .env \
  -e WEB_CONCURRENCY=1 \
  -e MORTIMER_MONGO_HOST=mortimer-mongo \
  -p 8000:8000 \
  mortimer-app:v1