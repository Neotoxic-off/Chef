# Realtime: WebSockets and Server-Sent Events

Written for `ws` 8.23.0, RFC 6455, the WHATWG HTML Living Standard (Server-Sent Events) and the OWASP WebSocket Security Cheat Sheet (Nov 2026), not benchmarked.

## Pick the transport

- Server-to-client only (notifications, progress, LLM token streams): Server-Sent Events. Plain HTTP, automatic reconnect, `Last-Event-ID` resume.
- Two-way, low-latency messages (chat, collaboration, games): WebSockets.
- Rare updates: polling, or a webhook between servers.

## Server-Sent Events

- `Content-Type: text/event-stream`, `Cache-Control: no-cache`. Send an `id:` on each event and replay missed events from `Last-Event-ID`.
- Send a comment line (`: ping`) at a fixed interval (a named constant) so proxies keep the connection open; turn off proxy buffering.
- Serve over HTTP/2 or HTTP/3: on HTTP/1.1 browsers allow only 6 connections per origin, and SSE holds one.

## WebSocket security (OWASP)

- `wss://` only.
- Check the `Origin` header against an allowlist on every handshake (cross-site WebSocket hijacking). With `ws`, check in the HTTP server's `upgrade` event, not `verifyClient`.
- Authenticate during the handshake (session cookie plus the Origin check), or with a token in the first message. Never put tokens in the URL query: it ends up in logs. Close the socket if auth does not arrive in time.
- Authorize every message, not only the connection. Re-check or close when the session expires.
- Validate every message against a schema at the boundary. Cap message size, messages per second and connections per user.
- Log connects, disconnects, auth failures and limit hits, never message bodies or tokens.

```ts
const ALLOWED_ORIGINS: ReadonlySet<string> = new Set<string>(["https://app.example.com"]);
const MAX_PAYLOAD_BYTES: number = 64 * 1024;

const wss: WebSocketServer = new WebSocketServer({ noServer: true, maxPayload: MAX_PAYLOAD_BYTES });

server.on("upgrade", (request: IncomingMessage, socket: Duplex, head: Buffer): void => {
  if (!ALLOWED_ORIGINS.has(request.headers.origin ?? "")) {
    socket.end("HTTP/1.1 403 Forbidden\r\n\r\n");
    return;
  }
  wss.handleUpgrade(request, socket, head, (ws: WebSocket): void => {
    wss.emit("connection", ws, request);
  });
});
```

## Reliability

- Heartbeat with ping/pong; terminate sockets that miss a pong.
- Clients reconnect with exponential backoff and jitter, then resume from the last sequence number they processed.
- Delivery is at-least-once after a reconnect: give each message an ID and make handlers idempotent.
- Watch backpressure (`bufferedAmount` in browsers, the send callback in `ws`); drop or close slow consumers instead of buffering without limit.
- Version the message protocol (a `type` and `version` field per message, or a subprotocol in `Sec-WebSocket-Protocol`).

## Scaling and shutdown

- Keep connection state out of the process. Fan out between instances through Redis pub/sub, NATS or a broker (see `messaging.md`).
- Raise proxy and load balancer idle timeouts above the heartbeat interval.
- On deploy, stop accepting new sockets and close open ones with code `1001` (Going Away) so clients reconnect elsewhere.

## Tests

- Integration tests with a real server on a random port and a real client: `connection from unlisted origin is rejected with 403`, `oversized message closes the socket with 1009`.
- Test reconnect and resume: kill the server, restart it, assert that no message is lost or applied twice.
