# --- Sticky sessions via dedicated "route" cookie ---

# 1) Derive sticky key:
# - If the client already has a "route" cookie, use its value.
# - Otherwise, fall back to the client IP until a cookie is issued.
map $cookie_route $sticky_key {
    ""      $remote_addr;
    default $cookie_route;
}

# 2) Issue a persistent "route" cookie if the client doesn't have one yet.
# - Value format: "<ip>-<timestamp>" ensures uniqueness
# - Max-Age: 1 year, Path=/, HttpOnly, SameSite=Lax
map $cookie_route $set_route_cookie {
    ""      "route=$remote_addr-$msec; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax";
    default "";
}

# 3) Upstream pool: hash based on the sticky key
upstream mortimer {
${UPSTREAM_SERVERS}
  hash $sticky_key consistent;
  keepalive 32;
}

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

  access_log /dev/stdout combined;
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

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # Routing Cookie
    add_header Set-Cookie $set_route_cookie always;

    proxy_pass http://mortimer;
  }

  location = /healthz {
    allow 127.0.0.1; allow ::1; allow 172.16.0.0/12; deny all;
    proxy_pass http://mortimer/healthz;
    proxy_set_header Host $host;
  }
}
