# Ubuntu / Oracle Cloud Always Free Deployment Guide

This guide deploys **MCA Career Compass** (React + TypeScript + Vite frontend, Django + Gunicorn backend, PostgreSQL 15+ database, and Nginx HTTPS reverse proxy) directly from GitHub on an **Ubuntu 22.04 / 24.04** server (including **Oracle Cloud Always Free Ampere A1** with 2 OCPUs / 12 GB RAM).

---

## 1. Provision Server & Open Ports

1. Create an **Ubuntu 22.04 or 24.04** VM (Oracle Cloud Always Free ARM or any 2+ vCPU / 2+ GB RAM VPS).
2. In your cloud network security list / firewall, allow inbound TCP traffic on:
   - `22` (SSH)
   - `80` (HTTP, needed for Let's Encrypt)
   - `443` (HTTPS)
3. On Oracle Cloud Ubuntu images, also open ports `80` and `443` in host firewall rules if `iptables` drops them by default:
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save || true
   ```

---

## 2. Install System Prerequisites (One-Time)

SSH into the server and run:

```bash
sudo apt-get update
sudo apt-get install -y git curl python3 python3-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx

# Install Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## 3. Create PostgreSQL Database & Least-Privileged User

```bash
sudo -u postgres psql <<'SQL'
CREATE USER mca_compass_user WITH PASSWORD 'replace-with-strong-db-password';
CREATE DATABASE mca_career_compass OWNER mca_compass_user;
GRANT ALL PRIVILEGES ON DATABASE mca_career_compass TO mca_compass_user;
SQL
```

---

## 4. Clone from GitHub & Configure `.env`

```bash
sudo mkdir -p /opt/mca-career-compass
sudo chown "$USER":"$USER" /opt/mca-career-compass
git clone https://github.com/<your-org-or-user>/<your-repo>.git /opt/mca-career-compass
cd /opt/mca-career-compass
cp .env.example .env
```

Edit `/opt/mca-career-compass/.env` with production values (generate strong keys via `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`):

```dotenv
DJANGO_SECRET_KEY=<generated-50-char-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=compass.yourcollege.edu,YOUR_SERVER_IP
CSRF_TRUSTED_ORIGINS=https://compass.yourcollege.edu

POSTGRES_DB=mca_career_compass
POSTGRES_USER=mca_compass_user
POSTGRES_PASSWORD=replace-with-strong-db-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
BEHIND_HTTPS_PROXY=True
AUDIT_IP_HMAC_KEY=<generated-random-key>
```

*(If testing temporarily over HTTP IP without a domain/TLS yet, keep `SESSION_COOKIE_SECURE=False`, `CSRF_COOKIE_SECURE=False`, `BEHIND_HTTPS_PROXY=False`, and add `http://YOUR_SERVER_IP` to `CSRF_TRUSTED_ORIGINS` until HTTPS is enabled.)*

---

## 5. Run the Automated Deploy Script

```bash
cd /opt/mca-career-compass
chmod +x deploy/deploy.sh
DOMAIN=compass.yourcollege.edu ./deploy/deploy.sh
```

`deploy/deploy.sh` automatically:
1. Pulls the latest `main` commit (`git pull --ff-only`)
2. Creates/updates `.venv` and installs [backend/requirements.txt](../backend/requirements.txt) (including `gunicorn` on Linux)
3. Runs `manage.py check`, `manage.py migrate --noinput`, and `manage.py collectstatic --noinput`
4. Builds the production SPA (`frontend/dist/`)
5. Installs [mca-compass.service.template](../deploy/mca-compass.service.template) to `/etc/systemd/system/mca-compass.service`
6. Installs [nginx.conf.template](../deploy/nginx.conf.template) to `/etc/nginx/sites-available/mca-compass.conf`
7. Restarts Gunicorn, reloads Nginx, and verifies `/api/v1/health/`

---

## 6. Create Platform Super Admin & Enable HTTPS

```bash
cd /opt/mca-career-compass/backend
../.venv/bin/python manage.py create_platform_admin \
  --email superadmin@yourcollege.edu \
  --first-name Platform \
  --last-name Admin

# Enable free Let's Encrypt HTTPS (once DNS A-record points to server IP)
sudo certbot --nginx -d compass.yourcollege.edu
```

---

## 7. Optional: Auto-Deploy from GitHub on Every Push to `main`

The included workflow [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) runs all Django + PostgreSQL + React CI checks on every push/PR, and can automatically run `./deploy/deploy.sh` on your server when you add:
- **Repository Variable**: `ENABLE_AUTO_DEPLOY` = `true`
- **Repository Secrets**:
  - `DEPLOY_HOST`: Server IP or domain
  - `DEPLOY_USER`: SSH username (e.g. `ubuntu`)
  - `DEPLOY_SSH_KEY`: Private SSH key for that user
  - `DEPLOY_PATH`: `/opt/mca-career-compass`

