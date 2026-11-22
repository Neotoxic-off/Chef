Write Kubernetes 1.37 manifests in `k8s/` for a stateless web app `shop-api` (image `ghcr.io/acme/shop-api:2.3.1`, port 8080, `/healthz` and `/readyz`): a Deployment, a Service, a HorizontalPodAutoscaler (2 to 10 replicas on 70% CPU), a PodDisruptionBudget and a ConfigMap for `LOG_LEVEL=info`.

Work autonomously: nobody will answer questions.
