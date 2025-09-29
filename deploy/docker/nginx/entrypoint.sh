#!/usr/bin/env sh
set -eu

# Required
: "${TLS_MODE:?missing TLS_MODE}"  # letsencrypt | off

# Defaults (override in .env when needed)
: "${SERVER_NAME:=localhost}"
: "${CLIENT_MAX_BODY_SIZE:=20m}"
: "${PROXY_READ_TIMEOUT:=75s}"
: "${PROXY_SEND_TIMEOUT:=75s}"
: "${PROXY_CONNECT_TIMEOUT:=5s}"
: "${PROXY_BUFFERING:=on}"
: "${RATE_LIMIT_REQS:=10}"
: "${RATE_LIMIT_BURST:=20}"
: "${LOG_FORMAT:=default}"
: "${ENABLE_WEBSOCKETS:=false}"

TEMPLATE_DIR=/etc/nginx/templates
CONF_OUT=/etc/nginx/conf.d/mortimer.conf

case "$TLS_MODE" in
  letsencrypt)
    : "${SSL_FULLCHAIN_PATH:?missing SSL_FULLCHAIN_PATH}"
    : "${SSL_PRIVKEY_PATH:?missing SSL_PRIVKEY_PATH}"
    export SERVER_NAME SSL_FULLCHAIN_PATH SSL_PRIVKEY_PATH
    ;;
  off)
    # no cert paths needed
    ;;
  *)
    echo "Unsupported TLS_MODE: $TLS_MODE (use 'letsencrypt' or 'off')" >&2
    exit 1
    ;;
esac

# Build upstream server list with real newlines
: "${UPSTREAM_BACKENDS:?missing UPSTREAM_BACKENDS}"
UPSTREAM_SERVERS="$(printf '    server %s;\n' $UPSTREAM_BACKENDS)"

# Export common variables for envsubst
export TLS_MODE SERVER_NAME \
  CLIENT_MAX_BODY_SIZE PROXY_READ_TIMEOUT PROXY_SEND_TIMEOUT \
  PROXY_CONNECT_TIMEOUT PROXY_BUFFERING RATE_LIMIT_REQS RATE_LIMIT_BURST \
  LOG_FORMAT ENABLE_WEBSOCKETS UPSTREAM_SERVERS

# Limit envsubst to the variables we actually export so nginx runtime
# variables such as $host or $uri stay intact in the rendered config.
ENV_VARS='${SERVER_NAME} ${CLIENT_MAX_BODY_SIZE} ${PROXY_READ_TIMEOUT} ${PROXY_SEND_TIMEOUT} \
${PROXY_CONNECT_TIMEOUT} ${PROXY_BUFFERING} ${RATE_LIMIT_REQS} ${RATE_LIMIT_BURST} \
${LOG_FORMAT} ${ENABLE_WEBSOCKETS} ${SSL_FULLCHAIN_PATH} ${SSL_PRIVKEY_PATH} \
${UPSTREAM_SERVERS}'

# Pick template based on TLS_MODE
if [ "$TLS_MODE" = "letsencrypt" ]; then
  envsubst "$ENV_VARS" < "$TEMPLATE_DIR/mortimer-https.conf.tpl" > "$CONF_OUT"
else
  envsubst "$ENV_VARS" < "$TEMPLATE_DIR/mortimer-http.conf.tpl" > "$CONF_OUT"
fi

# Remove the default site so Mortimer handles all traffic
rm -f /etc/nginx/conf.d/default.conf


# Validate config and start Nginx
nginx -t
exec nginx -g 'daemon off;'
