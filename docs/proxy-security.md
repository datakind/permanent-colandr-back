# Proxy security (X-Forwarded-* and host-header poisoning)

The Flask app uses [Werkzeug ProxyFix](https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/) so that behind a reverse proxy (e.g. nginx) it correctly sees HTTPS and the public host (for `request.url`, OpenAPI "Try it out", redirects, etc.). ProxyFix trusts the `X-Forwarded-Proto` and `X-Forwarded-Host` headers.

**Security requirement:** Those headers are only safe to trust if the **only** client that can reach the Flask app is your reverse proxy. If the app is reachable directly by arbitrary clients (e.g. port 5000 exposed to the internet), a client could send spoofed `X-Forwarded-*` headers and influence generated URLs (host-header poisoning). So the app must **never** be exposed directly to the public.

## How to set it up

### Docker Compose (production)

- **Nginx on the same host:** Publish the API port only on localhost so only nginx on the host can connect:
  ```yaml
  ports:
    - "127.0.0.1:5000:5000"
  ```
  (This is already set in `compose.prod.yaml`.)

- **Nginx in Docker (same network):** Do **not** publish port 5000. Nginx should connect to the API using the service name, e.g. `http://colandr-api:5000`. Only nginx (and other containers on the same network) can reach the API.

### AWS

- **ECS/Fargate + ALB:** The API task should listen on 5000 only inside the task. The ALB target group points at the task’s port 5000. Ensure the API task’s security group allows inbound 5000 **only** from the ALB (or from the nginx task if nginx is in front of the ALB). Never allow 0.0.0.0/0 to port 5000 on the API.

- **EC2 + nginx on same instance:** Bind the API to 127.0.0.1:5000 (or run it in a container with `127.0.0.1:5000:5000`). Nginx on the instance proxies to localhost:5000. Port 5000 is not in the security group or is only allowed from localhost.

### Nginx

Have nginx **set** (overwrite) the headers instead of forwarding client values:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

That way the app only ever sees values from nginx, not from the client.

## Summary

| Requirement | Action |
|------------|--------|
| App only reachable by proxy | Do not expose 5000 to the public; use 127.0.0.1 or internal network only. |
| AWS security groups | Allow inbound 5000 to the API only from ALB/nginx, never 0.0.0.0/0. |
| Nginx | Set `X-Forwarded-Proto` and `X-Forwarded-Host` (overwrite client headers). |
