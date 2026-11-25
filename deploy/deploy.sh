#!/usr/bin/env bash
set -euo pipefail

# One-command deployment & update script for Ubuntu / Oracle Cloud ARM VM.
# Usage:
#   ./deploy/deploy.sh                  # Pull, build, migrate, configure (if needed), restart
#   ./deploy/deploy.sh --skip-pull      # Deploy local checkout without git pull
#   ./deploy/deploy.sh --reconfigure    # Overwrite systemd & nginx configs from templates

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SKIP_PULL=false
RECONFIGURE=false
for arg in "$@"; do
  case "$arg" in
    --skip-pull) SKIP_PULL=true ;;
    --reconfigure) RECONFIGURE=true ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

APP_USER="${APP_USER:-$(id -un)}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
SERVER_NAME="${DOMAIN:-_}"

cd "$APP_ROOT"

if [[ ! -f "${APP_ROOT}/.env" ]]; then
  echo "ERROR: ${APP_ROOT}/.env not found. Copy .env.example to .env and configure production secrets first." >&2
  exit 1
fi

echo "==> [1/7] Checking repository state..."
if [[ "$SKIP_PULL" == "false" ]] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git pull --ff-only
fi

echo "==> [2/7] Setting up Python virtual environment & installing dependencies..."
if [[ ! -d "${APP_ROOT}/.venv" ]]; then
  python3 -m venv "${APP_ROOT}/.venv"
fi
"${APP_ROOT}/.venv/bin/pip" install --upgrade pip
"${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/backend/requirements.txt"

echo "==> [3/7] Running Django checks, database migrations & collectstatic..."
(
  cd "${APP_ROOT}/backend"
  "${APP_ROOT}/.venv/bin/python" manage.py check
  "${APP_ROOT}/.venv/bin/python" manage.py migrate --noinput
  "${APP_ROOT}/.venv/bin/python" manage.py collectstatic --noinput
)

echo "==> [4/7] Building React/TypeScript frontend..."
(
  cd "${APP_ROOT}/frontend"
  npm ci
  npm run build
)

echo "==> [5/7] Configuring systemd service (mca-compass.service)..."
SERVICE_TARGET="/etc/systemd/system/mca-compass.service"
if [[ ! -f "$SERVICE_TARGET" || "$RECONFIGURE" == "true" ]]; then
  TMP_SVC="$(mktemp)"
  sed \
    -e "s|__APP_USER__|${APP_USER}|g" \
    -e "s|__APP_ROOT__|${APP_ROOT}|g" \
    -e "s|__GUNICORN_WORKERS__|${GUNICORN_WORKERS}|g" \
    -e "s|__GUNICORN_THREADS__|${GUNICORN_THREADS}|g" \
    "${APP_ROOT}/deploy/mca-compass.service.template" > "$TMP_SVC"
  sudo cp "$TMP_SVC" "$SERVICE_TARGET"
  rm -f "$TMP_SVC"
  sudo systemctl daemon-reload
  sudo systemctl enable mca-compass
fi

echo "==> [6/7] Configuring Nginx site (mca-compass.conf)..."
NGINX_AVAIL="/etc/nginx/sites-available/mca-compass.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/mca-compass.conf"
if [[ ! -f "$NGINX_AVAIL" || "$RECONFIGURE" == "true" ]]; then
  TMP_NGX="$(mktemp)"
  sed \
    -e "s|__SERVER_NAME__|${SERVER_NAME}|g" \
    -e "s|__APP_ROOT__|${APP_ROOT}|g" \
    "${APP_ROOT}/deploy/nginx.conf.template" > "$TMP_NGX"
  sudo cp "$TMP_NGX" "$NGINX_AVAIL"
  rm -f "$TMP_NGX"
  sudo ln -sfn "$NGINX_AVAIL" "$NGINX_ENABLED"
  if [[ -L /etc/nginx/sites-enabled/default ]]; then
    sudo rm -f /etc/nginx/sites-enabled/default
  fi
fi

sudo nginx -t

echo "==> [7/7] Restarting Gunicorn & reloading Nginx..."
sudo systemctl restart mca-compass
sudo systemctl reload nginx

sleep 2
if curl -fsS http://127.0.0.1:8000/api/v1/health/ >/dev/null; then
  echo "Deployment succeeded! Backend health check returned OK."
else
  echo "WARNING: Backend health check did not return 200. Check: sudo journalctl -u mca-compass -n 50" >&2
  exit 1
fi

