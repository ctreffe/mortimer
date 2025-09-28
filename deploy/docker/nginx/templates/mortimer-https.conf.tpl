map $LOG_FORMAT $access_format { default combined; json json; }

upstream mortimer { server mortimer-app:8000; keepalive 32; }

# HTTP -> HTTPS (+ ACME webroot)
server {
  listen 80;
  server_name ${SERVER_NAME};

  location ^~ /.well-known/acme-challenge/ { root /var/www/certbot; }
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl http2;
  server_name ${SERVER_NAME};

  ssl_certificate     ${SSL_FULLCHAIN_PATH};
  ssl_certificate_key ${SSL_PRIVKEY_PATH};
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_session_cache shared:SSL:10m;

  access_log /dev/stdout $access_format;
  error_log  /dev/stderr warn;
  client_max_body_size ${CLIENT_MAX_BODY_SIZE};

  # security headers (+HSTS optional, erst in stabiler Prod aktivieren)
  add_header X-Frame-Options SAMEORIGIN always;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;
  add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
  # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

  # gzip
  gzip on; gzip_comp_level 5; gzip_min_length 1024; gzip_vary on;
  gzip_types text/plain text/css text/xml application/xml application/json application/javascript application/rss+xml image/svg+xml;

  # rate limit (optional)
  limit_req_zone $binary_remote_addr zone=req_zone:10m rate=${RATE_LIMIT_REQS}r/s;

  # static
  location /static/ {
    alias /srv/mortimer/;
    expires 7d;
    add_header Cache-Control "public, max-age=604800, immutable";
    try_files $uri =404;
  }

  # app proxy
  location / {
    limit_req zone=req_zone burst=${RATE_LIMIT_BURST} nodelay;

    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_read_timeout     ${PROXY_READ_TIMEOUT};
    proxy_send_timeout     ${PROXY_SEND_TIMEOUT};
    proxy_connect_timeout  ${PROXY_CONNECT_TIMEOUT};
    proxy_buffering        ${PROXY_BUFFERING};
    proxy_buffers 16 16k;
    proxy_busy_buffers_size 24k;

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_pass http://mortimer;
  }

  location = /healthz {
    allow 127.0.0.1; allow ::1; allow 172.16.0.0/12; deny all;
    proxy_pass http://mortimer/healthz;
    proxy_set_header Host $host;
  }
}
