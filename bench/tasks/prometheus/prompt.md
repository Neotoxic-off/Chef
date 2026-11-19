This folder holds a Python HTTP service (`app.py`, port 8000). In production it exposes Prometheus metrics on `/metrics`: a counter `http_requests_total` with labels `route` and `status`, and a histogram `http_request_duration_seconds` with label `route`.

Write the Prometheus setup to monitor it: `prometheus.yml` at the folder root scraping the service, and alerting rules for: the service is down, the 5xx error ratio is above 5% over 5 minutes, and the p95 latency is above 500 ms. Add a `docker-compose.yml` that runs Prometheus next to the service.

Work autonomously: nobody will answer questions.
