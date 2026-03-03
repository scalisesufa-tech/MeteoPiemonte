# Kubernetes manifests (private cloud / OpenStack CSI)

This folder contains Kubernetes manifests to deploy the **meteo platform** on a cluster that provides:
- **Cinder CSI** (`cinder.csi.openstack.org`) for block storage (e.g. `csi-cinder-fast`)
- optionally **Manila CSI** (`manila.csi.openstack.org`) for shared NFS (not used by default)
- optionally **Gateway API** (HTTPRoute + a shared Gateway called `shared-gateway`)

## What gets deployed
- `timescaledb` (StatefulSet, PVC via `csi-cinder-fast`)
- `rabbitmq` (StatefulSet, PVC via `csi-cinder-fast`)
- `meteo-core` (Deployment)
- `analysis-service` (Deployment)
- `frontend` (Deployment)
- `grafana` (Deployment, PVC via `csi-cinder-fast`, provisioning via ConfigMap)

## Namespace
Manifests are written for namespace `group-6` to match your cluster exercises.
If you need another namespace, change it in:
- `manifests/namespace/namespace.yaml`
- all manifests `metadata.namespace:` fields

## Images
Kubernetes does **not** build images. You must build and push your images to a registry, then set the image names in:
- `meteo-core-deployment.yaml`
- `analysis-service-deployment.yaml`
- `frontend-deployment.yaml`

Search for `REPLACE_ME_REGISTRY`.

## Deploy (PowerShell)
```powershell
kubectl apply -f .\manifests\namespace\namespace.yaml
kubectl apply -f .\all-manifests.yaml
```

## Verify
```powershell
kubectl get all -n group-6
kubectl get pvc -n group-6
kubectl describe pvc <name> -n group-6
```

## Gateway API (optional)
If your cluster has a Gateway called `shared-gateway` in `default` namespace, you can apply the routes in `manifests/routing/`.
Otherwise, ignore that folder (or replace with an Ingress for your ingress controller).
