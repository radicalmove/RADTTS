# RADTTS Deployment on `fld-mini` (Ubuntu 24.04)

This follows your existing baseline: `systemd + nginx + gunicorn`, with separate prod/dev services.

## 1. Target layout
- Prod checkout: `/home/fldadmin/radtts`
- Dev checkout: `/home/fldadmin/radtts-dev`
- Prod service port: `127.0.0.1:8010`
- Dev service port: `127.0.0.1:8011`
- Nginx routes:
  - `:80` -> prod (`8010`)
  - `:8080` -> dev (`8011`)

## 2. OS packages
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg nginx
```

## 3. App install (repeat for prod/dev folders)
```bash
cd /home/fldadmin/radtts
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-linux-cpu.txt
pip install -e .
```

## 4. Environment files
Create `/home/fldadmin/radtts/.env`:
```bash
RADTTS_PROJECTS_ROOT=/home/fldadmin/radtts/projects
RADTTS_HOST=127.0.0.1
RADTTS_PORT=8010
```

Create `/home/fldadmin/radtts-dev/.env` with `RADTTS_PORT=8011` and a dev projects root.

## 5. systemd services
- Copy from `deploy/systemd/radtts.service` and `deploy/systemd/radtts-dev.service`
- Install:
```bash
sudo cp deploy/systemd/radtts*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now radtts radtts-dev
```

## 6. nginx
- Copy `deploy/nginx/radtts.conf` to `/etc/nginx/sites-available/radtts`
- Link and reload:
```bash
sudo ln -s /etc/nginx/sites-available/radtts /etc/nginx/sites-enabled/radtts
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Verification
```bash
systemctl status radtts radtts-dev --no-pager
ss -ltnp | grep -E ':8010|:8011|:80|:8080'
curl -I http://127.0.0.1:8010/
curl -I http://127.0.0.1:8011/
curl -I http://127.0.0.1/
curl -I http://127.0.0.1:8080/
```

## 8. Sharing options
- Admin access: use Tailscale + SSH.
- Public temporary share: Cloudflare Quick Tunnel (ephemeral URL).
- Stable public URL: named tunnel + owned domain.

## 9. Notes
- This app is local-first and writes outputs under `RADTTS_PROJECTS_ROOT`.
- Voice cloning requires authorization acknowledgment per request.
