# Proxy security (X-Forwarded-* and host-header poisoning)

The Flask app uses [Werkzeug ProxyFix](https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/) so that behind a reverse proxy it sees the **public** scheme and host (`request.url`, OpenAPI “Try it out” / `SERVERS`, redirects, etc.). ProxyFix trusts `X-Forwarded-Proto` and `X-Forwarded-Host` (and related hop headers) as set by the proxy.

**Security requirement:** Those headers are only safe if **arbitrary clients cannot reach the Flask process**. If port 5000 is exposed to the internet, clients can spoof `X-Forwarded-*` and influence generated URLs (host-header poisoning). The API must be reachable only from nginx (or equivalent), on localhost or an internal network.

## Two common topologies

| Where TLS ends | Nginx → Flask hop | `X-Forwarded-Proto` toward Flask |
|----------------|-------------------|--------------------------------|
| **Nginx** (Let’s Encrypt on the instance) | Often HTTPS → HTTP to `127.0.0.1:5000` | Set from **`$scheme`** (overwrite client headers). |
| **ALB** (certificate on the load balancer) | ALB uses **HTTP** to nginx on the target port; nginx → Flask still HTTP | Must reflect the **client** TLS session, not `$scheme` on that hop (see below). |

When TLS terminates at the **ALB**, nginx’s connection from the load balancer is plain HTTP, so **`$scheme` is `http`**. If nginx redirects “HTTP → HTTPS” using only `$scheme`, or forwards `X-Forwarded-Proto: $scheme` to Flask, you get wrong redirects, wrong OpenAPI server URLs, or an **infinite redirect** loop. Use the ALB’s `X-Forwarded-Proto` (and normalize it) instead.

**ALB header quirks:** With [XFF header processing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-load-balancer-attributes.html) in **append** mode, `X-Forwarded-Proto` can be a comma-separated list (e.g. `http, https`). An nginx `map` that only matches the exact string `https` will miss that. A practical pattern is to treat the header as HTTPS if it **contains** `https` (regex map).

Example (conceptual; align with `deployment/nginx/colandr.conf` on the server):

```nginx
map $http_x_forwarded_proto $colandr_effective_scheme {
    default $scheme;
    ~*https https;
}

map $http_x_forwarded_proto $colandr_pass_x_forwarded_proto {
    default $scheme;
    ~*https https;
}

# On the port the ALB targets (often 80): redirect real cleartext clients, but not ALB-forwarded HTTPS.
location / {
    if ($colandr_effective_scheme != "https") {
        return 301 https://$host$request_uri;
    }
    proxy_pass http://colandr_api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $colandr_pass_x_forwarded_proto;
    proxy_set_header X-Forwarded-Host $host;
}
```

When **nginx** terminates TLS (no ALB in front of nginx for that hostname), keep overwriting client headers and derive proto from the TLS connection:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Prefer **not** forwarding client-supplied `X-Forwarded-*` into Flask; have nginx set them.

**Instance security groups:** When all public traffic goes **ALB → nginx**, restrict inbound **:80 on the instance** to the **ALB security group** (instead of `0.0.0.0/0`) so the Internet cannot bypass the ALB and spoof forwarded headers toward nginx.

## How to set it up

### Docker Compose (production)

- **Nginx on the same host:** Publish the API only on localhost so only nginx reaches it (see `compose.prod.yaml`).

- **Nginx in Docker (same network):** Do not publish port 5000 publicly. Nginx talks to the API by service name; only the internal network reaches the API.

### AWS

- **ECS/Fargate + ALB:** API listens on 5000 inside the task; target group to that port. Security group allows 5000 only from the ALB (or from nginx if nginx is in front).

- **EC2 + nginx on the instance:** API on `127.0.0.1:5000` (or container publish `127.0.0.1:5000:5000`). No public access to 5000.

- **EC2 + internet-facing ALB + nginx (TLS at ALB):** Target group to nginx (commonly **HTTP :80**). Use the ALB-aware `map` / `proxy_set_header` pattern above. ACM certificate lives on the **listener**, not necessarily on nginx for that hostname.

## Summary

| Requirement | Action |
|------------|--------|
| App only reachable by proxy | Do not expose 5000 to the public; bind to localhost or internal interfaces. |
| AWS security groups | Allow the API port only from nginx / ALB, not `0.0.0.0/0`. Prefer nginx :80 from ALB SG only when using an ALB. |
| TLS at nginx | `proxy_set_header X-Forwarded-Proto $scheme` (and related headers). |
| TLS at ALB | Use `X-Forwarded-Proto` from the ALB (regex / normalized), not raw `$scheme` on the ALB→nginx hop; avoid redirect loops on port 80. |
