import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT: int = 8000
BUCKETS: tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
HEALTH_ROUTE: str = "/health"
METRICS_ROUTE: str = "/metrics"
KNOWN_ROUTES: frozenset[str] = frozenset({HEALTH_ROUTE, METRICS_ROUTE})
OTHER_ROUTE: str = "other"
TEXT_CONTENT_TYPE: str = "text/plain"
METRICS_CONTENT_TYPE: str = "text/plain; version=0.0.4"

requests_total: dict[tuple[str, int], int] = {}
duration_buckets: dict[str, list[int]] = {}
duration_sum: dict[str, float] = {}


def record(route: str, status: int, seconds: float) -> None:
    requests_total[(route, status)] = requests_total.get((route, status), 0) + 1
    counts: list[int] = duration_buckets.setdefault(route, [0] * len(BUCKETS))
    for index, bound in enumerate(BUCKETS):
        if seconds <= bound:
            counts[index] += 1
    duration_sum[route] = duration_sum.get(route, 0.0) + seconds


def histogram_lines(route: str) -> list[str]:
    total: int = sum(count for (counted_route, _), count in requests_total.items() if counted_route == route)
    lines: list[str] = [
        f'http_request_duration_seconds_bucket{{route="{route}",le="{bound}"}} {count}'
        for bound, count in zip(BUCKETS, duration_buckets[route], strict=True)
    ]
    lines.append(f'http_request_duration_seconds_bucket{{route="{route}",le="+Inf"}} {total}')
    lines.append(f'http_request_duration_seconds_sum{{route="{route}"}} {duration_sum[route]}')
    lines.append(f'http_request_duration_seconds_count{{route="{route}"}} {total}')
    return lines


def exposition() -> str:
    lines: list[str] = [
        "# HELP http_requests_total HTTP requests served.",
        "# TYPE http_requests_total counter",
        *(
            f'http_requests_total{{route="{route}",status="{status}"}} {count}'
            for (route, status), count in sorted(requests_total.items())
        ),
        "# HELP http_request_duration_seconds Time spent serving HTTP requests.",
        "# TYPE http_request_duration_seconds histogram",
    ]
    for route in sorted(duration_buckets):
        lines += histogram_lines(route)
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        started: float = time.perf_counter()
        route: str = self.path if self.path in KNOWN_ROUTES else OTHER_ROUTE
        status: int = self.respond(route)
        record(route, status, time.perf_counter() - started)

    def respond(self, route: str) -> int:
        if route == OTHER_ROUTE:
            self.send_error(HTTPStatus.NOT_FOUND)
            return HTTPStatus.NOT_FOUND
        body: bytes = b"ok"
        content_type: str = TEXT_CONTENT_TYPE
        if route == METRICS_ROUTE:
            body, content_type = exposition().encode(), METRICS_CONTENT_TYPE
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)
        return HTTPStatus.OK


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
