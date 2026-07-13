# Systemd Service Files

Systemd service templates for Colandr services.

## Installation

Create a symlink to keep the service file in sync with the repository:

```bash
sudo ln -s /home/ubuntu/permanent-colandr-back/deployment/systemd/colandr-api.service /etc/systemd/system/colandr-api.service
sudo systemctl daemon-reload
sudo systemctl enable colandr-api.service
sudo systemctl start colandr-api.service
```

**Note:** Adjust the path in the symlink command to match your repository location.

## Customization

**If you need instance-specific changes:** Copy the file instead of symlinking, then customize:

```bash
sudo cp deployment/systemd/colandr-api.service /etc/systemd/system/colandr-api.service
# Edit /etc/systemd/system/colandr-api.service as needed
sudo systemctl daemon-reload
```

Common customizations:
- **WorkingDirectory**: Path to your application directory
- **User/Group**: User that owns the application files

## Usage

```bash
sudo systemctl start colandr-api
sudo systemctl stop colandr-api
sudo systemctl restart colandr-api
sudo systemctl status colandr-api
```

### Compose profile

The unit sets **`Environment=COMPOSE_PROFILES=develop`** so **`api-develop`** starts with **`api`**, **`worker`**, and **`broker`**. You still need **`COLANDR_DEVELOP_BUILD_CONTEXT`** and the worktree **`.env`** (see repo README).

View application logs:
```bash
cd /home/ubuntu/permanent-colandr-back
docker compose -f compose.prod.yaml --profile develop logs -f
```

**Note:** This service uses Docker Compose V2 (`docker compose` with space). Ensure Docker Compose plugin is installed:
```bash
sudo apt install docker-compose-plugin
```
