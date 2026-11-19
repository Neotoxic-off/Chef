This folder holds a small Python HTTP service and its `Dockerfile`: `app.py`, standard library only, listens on port 8000, `GET /health` returns 200.

Write a Helm chart in `chart/` that deploys it on Kubernetes:
- a Deployment that runs the image set by the values `image.repository` and `image.tag`, with `replicaCount` replicas (default 2);
- the container listens on port 8000;
- a `ClusterIP` Service on port 80 that forwards to the container's port 8000.

Work autonomously: nobody will answer questions.
