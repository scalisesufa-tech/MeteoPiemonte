# Gateway API & Kubernetes Deployment

This folder contains the Kubernetes manifests to deploy the entire Meteo Platform using Cilium Gateway API.

## Requirements
- Kubernetes Cluster with **Cilium Gateway API** installed and active.
- Docker Hub access to pull the images:
  - `scalisufa/meteo-core`
  - `scalisufa/analysis-service`
  - `scalisufa/frontend`

## Deployment Strategy
All applications are declared in `all-manifests.yaml`. Run:
```bash
kubectl apply -f 04-kubernetes/all-manifests.yaml -n group-6
```

## Architecture Highlights
### Gateway API
The routing is handled by `Gateway` and `HTTPRoute` resources rather than standard `Ingress`.
- **`meteo-route`**: Binds to `/group-6/api/v1/meteo` and strips the prefix, forwarding traffic to the `meteo-core` service on port 8080.
- **`analysis-route`**: Binds to `/group-6/api/v1/analysis` and strips the prefix, forwarding traffic to the `analysis-service` service on port 8000.
- **`frontend-route`**: Binds to `/group-6` and exactly forwards to the React container serving statically. 
*Note on React*: The frontend Docker image was built with `"homepage": "."` to support this dynamic relative path mounting.

### Volume Resiliency
Stateful components (`meteo-db` and `grafana`) employ Persistent Volume Claims (PVC).
To prevent `Multi-Attach` errors during pod rollout on standard ReadWriteOnce (RWO) storage, these deployments/statefulsets use the **`Recreate`** deployment strategy. This ensures the old Pod is entirely terminated, releasing the volume lock before the new Pod is scheduled.
