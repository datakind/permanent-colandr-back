# Production Deployment Guide

Simple guide for deploying Colandr backend to a single EC2 instance with RDS.

## Architecture

- **EC2 Instance:** API, Worker (Celery), and Redis
- **RDS:** PostgreSQL database
- **Nginx:** Reverse proxy with SSL (proxies `/api/*` to backend)

## Prerequisites

- EC2 instance (t3.medium+ recommended)
- RDS PostgreSQL 17 instance
- Domain name for SSL (**API host is** `api.colandrapp.com`)

## 1. EC2 Setup

**Install Docker:**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose docker-buildx
sudo systemctl start docker
sudo systemctl enable docker

# Enable BuildKit by default (required for Dockerfile build caching)
sudo mkdir -p /etc/docker
echo '{"features":{"buildkit":true}}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

sudo usermod -aG docker ubuntu
```

**Log out and back in for group changes.**

## 2. Deploy Application

**Clone and Configure:**

```bash
cd ~
git clone https://github.com/datakind/permanent-colandr-back.git
cd permanent-colandr-back

# Create .env file
cp .env.example .env
nano .env  # Edit with production values
chmod 600 .env
```

**Generate keys:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Build and Start:**

```bash
docker compose -f compose.prod.yaml build
docker compose -f compose.prod.yaml up -d
```

## 3. Database Setup

**Run Migrations:**

```bash
docker compose -f compose.prod.yaml run --rm api flask db upgrade
```

## 4. Nginx Setup

**Install Nginx:**

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

**Configure Nginx:**

Create a symlink to the nginx configuration from the repository:

```bash
sudo ln -sf ~/permanent-colandr-back/deployment/nginx/colandr.conf /etc/nginx/conf.d/colandr.conf
sudo nginx -t
sudo systemctl reload nginx
```

**Why symlink:** Keeps config in sync with git. Updates: `git pull` then `sudo nginx -t && sudo systemctl reload nginx`.

The configuration includes:

- Frontend routing: (optional) if you run a separate frontend on this host, configure it separately
- API routing: Proxies `/api/*` requests to backend API on port 5000
- Static assets: (optional) depends on your frontend deployment
- Proper proxy headers (including `X-Forwarded-Proto` for HTTPS detection)
- HTTP/1.1 with keepalive for better performance
- Let's Encrypt validation path

**Start Nginx:**

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
sudo nginx -t  # Verify configuration
```

**Get SSL Certificate with Certbot:**

**Prerequisites:** Ensure DNS is configured before running certbot:

- `api.colandrapp.com` A record → EC2 instance public IP

**Option 1: Standard Certificates (HTTP Challenge - Recommended for initial setup):**

```bash
sudo certbot --nginx -d api.colandrapp.com
```

**Option 2: Wildcard Certificate (DNS Challenge - Covers all subdomains):**

For a wildcard certificate that covers `*.colandrapp.com` and `colandrapp.com`:

```bash
# Install DNS plugin (if using Route53)
sudo apt install -y python3-certbot-dns-route53

# Request wildcard cert with DNS challenge
sudo certbot certonly --dns-route53 -d "*.colandrapp.com" -d "colandrapp.com"
```

Then manually configure nginx to use the certificate (certbot won't auto-configure with DNS challenge).

**For migration scenarios:** Use a test subdomain first:

```bash
# Set up a test subdomain (e.g. v2.colandrapp.com) DNS pointing to this instance
sudo certbot --nginx -d v2.colandrapp.com
```

**What certbot does automatically (HTTP challenge only):**

- Obtains SSL certificate from Let's Encrypt
- Updates `/etc/nginx/conf.d/colandr.conf` (via symlink) to add HTTPS server block
- Configures SSL certificate paths
- Sets up automatic HTTP to HTTPS redirect
- Configures SSL best practices (TLS versions, ciphers, etc.)

**After certbot runs:**

1. Review changes: `git diff deployment/nginx/colandr.conf`
2. Commit the updated config: `git add deployment/nginx/colandr.conf && git commit -m "Add HTTPS config from certbot"`
3. Verify HTTPS: `curl https://api.colandrapp.com/api/health`

**Auto-renewal:** Certbot sets up automatic renewal. Verify:

```bash
sudo systemctl status certbot.timer
```

## 5. Verification

Verify the installation is working.

**Check containers are running:**

```bash
docker compose -f compose.prod.yaml ps
```

Should show all containers (api, worker, broker) as "Up".

**Check API health endpoint:**

```bash
curl -fsSL https://api.colandrapp.com/api/health
```

Should return JSON with status information.

**Check API documentation (visual verification):**

Open in your browser:

- `https://api.colandrapp.com/docs`

Should show Swagger UI with interactive API documentation. This confirms the API is running and accessible.

**Check logs for errors:**

```bash
docker compose -f compose.prod.yaml logs api
```

Verify no critical errors in the logs.

## 6. Auto-start on Boot

We run production via a systemd unit that calls Docker Compose.

Follow the systemd install doc (kept DRY here):

- `deployment/systemd/README.md`

After installing, these are the common commands:

```bash
sudo systemctl enable --now colandr-api.service
sudo systemctl status colandr-api.service --no-pager
sudo systemctl restart colandr-api.service
sudo journalctl -u colandr-api.service -f
```

## Common Commands

```bash
# View container logs
docker compose -f compose.prod.yaml logs -f

# Update application
git pull
docker compose -f compose.prod.yaml build
docker compose -f compose.prod.yaml up -d

# Run migrations
docker compose -f compose.prod.yaml run --rm api flask db upgrade

# Check status
docker compose -f compose.prod.yaml ps
curl -fsSL https://api.colandrapp.com/api/health
```

## Troubleshooting

**Container won't start:**

```bash
docker compose -f compose.prod.yaml logs api
docker compose -f compose.prod.yaml ps
```

**Database connection issues:**

- Verify RDS security group allows EC2 security group
- Check credentials in `.env`
- Test: `psql -h <rds-endpoint> -U <user> -d <dbname>`

**Redis issues:**

```bash
docker compose -f compose.prod.yaml exec broker redis-cli ping
```

## Security Notes

- Keep `.env` file permissions at 600
- Restrict SSH access in security groups
- Keep Docker and system packages updated
- Monitor logs regularly

---
