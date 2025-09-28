upstream mortimer { server mortimer-app:8000; keepalive 32; }

server {
  listen 80 default_server;
  server_name ${SERVER_NAME};

  # --- logging & limits ---
  access_log /dev/stdout combined;
  error_log  /dev/stderr warn;
  client_max_body_size ${CLIENT_MAX_BODY_SIZE};

  # --- security headers (HTTP: ohne HSTS) ---
  add_header X-Frame-Options SAMEORIGIN always;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;
  add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

  # --- gzip (sichere Texttypen) ---
  gzip on; gzip_comp_level 5; gzip_min_length 1024; gzip_vary on;
  gzip_types text/plain text/css text/xml application/xml application/json application/javascript application/rss+xml image/svg+xml;

  # static
  location /static/ {
    alias /srv/mortimer/static/;
    expires 7d;
    add_header Cache-Control "public, max-age=604800, immutable";
    try_files $uri =404;
  }

  # app proxy
  location / {
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

    # harmless for non-WS; enables WS if used
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
