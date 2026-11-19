# Application security

Verified against OWASP Top 10:2025, the OWASP Cheat Sheet Series, RFC 9700, RFC 8725, the OAuth 2.1 draft (-17), jose 6.2 (Nov 2026).

## OWASP Top 10:2025

A01 Broken Access Control (now includes SSRF) · A02 Security Misconfiguration · A03 Software Supply Chain Failures · A04 Cryptographic Failures · A05 Injection · A06 Insecure Design · A07 Authentication Failures · A08 Software or Data Integrity Failures · A09 Security Logging and Alerting Failures · A10 Mishandling of Exceptional Conditions.

## Input and output

- Validate every input at the trust boundary with a schema: type, length, range, format, allowlist. Reject, do not repair.
- Parameterized queries or the ORM's bound parameters only. No string-built SQL, shell commands or LDAP filters.
- Encode output for its context (HTML, attribute, URL, JS); let the template engine do it. Add a strict Content-Security-Policy.
- Fail closed (A10): an error in an auth or validation path denies the request. Never return stack traces.

## Authentication and sessions

- Use the platform's or a proven identity provider; never write your own crypto or session store.
- Passwords (OWASP Password Storage): Argon2id, at least 19 MiB memory, 2 iterations, 1 lane. Else scrypt (N=2^17, r=8, p=1); bcrypt only on legacy systems (cost >= 10, 72-byte limit); PBKDF2-HMAC-SHA-256 with 600,000 iterations when FIPS is required.
- Password rules (OWASP, NIST SP 800-63B): minimum 8 characters with MFA, 15 without; allow at least 64; no composition rules; check against breached-password lists.
- Session cookies: `Secure; HttpOnly; SameSite=Lax` (or `Strict`), `__Host-` prefix. Rotate the session ID on login.

## OAuth 2.1 / OIDC

- Follow RFC 9700 (OAuth 2.0 Security BCP, Jan 2025). OAuth 2.1 is still an Internet-Draft; it collects the same rules.
- Authorization code flow with PKCE (`S256`) for every client. No implicit flow, no password grant.
- Exact redirect URI matching. Validate `state` (or rely on PKCE) and the OIDC `nonce`.
- Public clients: sender-constrained (DPoP, RFC 9449) or rotated refresh tokens.
- Browser apps: prefer a backend-for-frontend that keeps tokens server-side over tokens in `localStorage`.

## JWT pitfalls (RFC 8725)

- Pin the allowed algorithms; never accept `none` or let the token header choose.
- Check `iss`, `aud`, `exp`, `nbf` on every token. Keep access tokens short-lived.
- A JWT is signed, not encrypted: no secrets in claims.

```ts
const jwks: RemoteJWKSet = createRemoteJWKSet(new URL(JWKS_URL));
const result: JWTVerifyResult = await jwtVerify(token, jwks, {
  issuer: ISSUER,
  audience: AUDIENCE,
  algorithms: ALLOWED_ALGORITHMS,
});
```

`jwtVerify` (jose 6) throws on any invalid token, so the auth middleware is the one place with a `try`/`catch`: catch, answer `401`, log.

## Authorization

- Deny by default. Check ownership on every object access (no IDOR), in the service layer, server-side.
- Tests per role: `get invoice of another tenant returns 404`.

## CSRF and SSRF

- CSRF (OWASP): use the framework's built-in protection; else synchronizer or signed double-submit tokens on every state-changing request. Fetch Metadata (`Sec-Fetch-Site`) and `SameSite` add defense in depth. Never change state on `GET`.
- SSRF: allowlist destination hosts. Resolve the name, reject private, loopback and link-local addresses, connect to the checked IP, turn off redirects.

## Supply chain and scanning

- Lockfiles committed; Dependabot or Renovate; fail CI on known vulnerabilities (`osv-scanner`, `npm audit`, `pip-audit`, `cargo audit`).
- SAST in CI: CodeQL or Semgrep. Secret scanning: gitleaks or the forge's push protection.
- Pin CI actions by SHA, generate an SBOM, sign release artifacts.
