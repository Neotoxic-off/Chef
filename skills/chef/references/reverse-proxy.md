# Reverse proxies (Nginx, Caddy, Traefik, HAProxy)

## Lint and validate

- Test the config before every reload, in CI and on the host. A failed test blocks the reload.
- Nginx: `nginx -t` (add `-c <file>` outside the default path).
- Caddy: `caddy validate --config Caddyfile`; `caddy fmt --diff Caddyfile` shows formatting drift.
- HAProxy: `haproxy -c -f /etc/haproxy/haproxy.cfg`.
- Traefik: no config test command found in the docs (unverified). Validate static and file-provider YAML against SchemaStore: `check-jsonschema --schemafile https://www.schemastore.org/traefik-v3.json traefik.yml`.
- Run the test with the same proxy version you deploy (same image tag), not the one on your laptop.
- Reload, do not restart: `nginx -s reload`, `caddy reload`, `systemctl reload haproxy`.

## Practices

- Versions checked Nov 2026: Nginx 1.30 stable / 1.31 mainline, Caddy 2.11, Traefik 3.7, HAProxy 3.4 LTS. Look up the current one on nginx.org/news, haproxy.org, and the GitHub releases of caddyserver/caddy and traefik/traefik.
- Pin the proxy image by tag and digest; let Renovate or Dependabot bump it.
- TLS 1.2 and 1.3 only. Take ciphers from the Mozilla SSL Configuration Generator ("intermediate"), not from memory.
- Automate certificates: Caddy and Traefik do ACME natively; Nginx has `ngx_http_acme_module` (package `nginx-module-acme`); HAProxy 3.3+ has built-in ACME.
- Redirect HTTP to HTTPS. Set request size limits and timeouts (`client_max_body_size`, `timeout client/server`).
- Trust `X-Forwarded-For` only from known proxy IPs: Nginx `set_real_ip_from`, Traefik `forwardedHeaders.trustedIPs`, HAProxy `option forwardfor` plus an ACL on the source.
- Keep one file per site or route; keep TLS and header policy in one shared snippet.

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
server {
    listen 443 ssl;
    http2 on;
    ssl_protocols TLSv1.2 TLSv1.3;
    server_tokens off;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_req_status 429;
        proxy_pass http://app:8080;
    }
}
```

- Nginx: an `add_header` in a child block drops every `add_header` of the parent. Repeat the shared snippet with `include`.
- Rate limits: Nginx `limit_req`, Traefik `rateLimit` middleware (`average`, `burst`), HAProxy stick tables (`http_req_rate(10s)`). Caddy has no built-in rate limiter; it needs a plugin. Answer 429, not 503.

## Security

- Send HSTS, `X-Content-Type-Options: nosniff`, `Referrer-Policy` and a CSP (or `frame-ancestors`) on every response; use `always` in Nginx so errors carry them too.
- Hide versions: `server_tokens off` (Nginx), `-Server` header (Caddy).
- Run as a non-root user; bind 443 with `CAP_NET_BIND_SERVICE`, not root.
- Traefik: no `api.insecure=true`; protect the dashboard with auth. Do not mount the Docker socket read-write; use a socket proxy.
- Expose admin endpoints (HAProxy stats, Caddy admin API on `localhost:2019`) only on localhost or a private network.

## Tests

- CI: run the config test in the proxy image for every change.
- Smoke-test after deploy: `curl -sSf -o /dev/null -w '%{http_code}' https://host/health` and assert the security headers with `curl -sI`.
- Scan TLS with `testssl.sh` in CI or on a schedule; fail on any grade below the policy.
- Test the rate limit: a burst over the limit gets 429.
