# Container Registry Information

## Current Cluster Configuration

The Kubernetes cluster uses:
- **Container Runtime**: containerd (Talos)
- **Existing Registries**: 
  - `registry.k8s.io` (Kubernetes official images)
  - `quay.io` (Cilium and other images)
  - **Docker Hub** (default registry - ✅ **ACCESSIBLE**)

**✅ Docker Hub is accessible from the cluster** - Images without a registry prefix (e.g., `rabbitmq:4.1.3-management`) are pulled from Docker Hub by default. **Public images work without any secret.**

## Image Registry Options

You need to push your Docker images to a registry accessible by the cluster. Here are the options:

### Option 1: Docker Hub (Public) - ✅ **RECOMMENDED**

**✅ Docker Hub is accessible from this cluster** - This is the simplest option.

#### For Public Images (No Secret Needed)

If your images are **public**, you don't need a secret:

```bash
# Login to Docker Hub (locally, for pushing)
docker login

# Tag images
docker tag catalog-service:latest <your-dockerhub-username>/catalog-service:latest
docker tag inventory-service:latest <your-dockerhub-username>/inventory-service:latest
docker tag api-gateway:latest <your-dockerhub-username>/api-gateway:latest

# Push images (make sure they're public in Docker Hub settings)
docker push <your-dockerhub-username>/catalog-service:latest
docker push <your-dockerhub-username>/inventory-service:latest
docker push <your-dockerhub-username>/api-gateway:latest

# Update deployment manifests
# Change image: catalog-service:latest
# To: <your-dockerhub-username>/catalog-service:latest
```

#### For Private Images or Rate Limiting (Secret Required)

If your images are **private** or you want to avoid Docker Hub rate limiting, create a secret:

```bash
# 1. Create secret in namespace group-1
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<your-dockerhub-username> \
  --docker-password=<your-dockerhub-password-or-token> \
  --docker-email=<your-email> \
  -n group-1

# 2. Update deployment manifests to use imagePullSecrets
# Add this to each deployment YAML:
# spec:
#   template:
#     spec:
#       imagePullSecrets:
#       - name: dockerhub-secret
#       containers:
#       - name: catalog-service
#         image: <your-dockerhub-username>/catalog-service:latest
```

**Note**: 
- For public images, no secret is needed
- For private images, you **must** create a secret
- Using a secret also helps avoid Docker Hub rate limiting (anonymous pulls are limited)

### Option 2: Quay.io

```bash
# Login to Quay.io
docker login quay.io

# Tag images
docker tag catalog-service:latest quay.io/<your-username>/catalog-service:latest
docker tag inventory-service:latest quay.io/<your-username>/inventory-service:latest
docker tag api-gateway:latest quay.io/<your-username>/api-gateway:latest

# Push images
docker push quay.io/<your-username>/catalog-service:latest
docker push quay.io/<your-username>/inventory-service:latest
docker push quay.io/<your-username>/api-gateway:latest

# Update deployment manifests
# Change image: catalog-service:latest
# To: quay.io/<your-username>/catalog-service:latest
```

### Option 3: Private Registry

If you have a private registry:

```bash
# Login to private registry
docker login <registry-url>

# Tag images
docker tag catalog-service:latest <registry-url>/catalog-service:latest
docker tag inventory-service:latest <registry-url>/inventory-service:latest
docker tag api-gateway:latest <registry-url>/api-gateway:latest

# Push images
docker push <registry-url>/catalog-service:latest
docker push <registry-url>/inventory-service:latest
docker push <registry-url>/api-gateway:latest

# Create image pull secret if needed
kubectl create secret docker-registry regcred \
  --docker-server=<registry-url> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n group-1

# Update deployment manifests to use imagePullSecrets
```

### Option 4: Local Registry (if available)

If there's a local registry in your cluster:

```bash
# Find registry URL (check with your cluster administrator)
# Common patterns:
# - registry.local:5000
# - <cluster-ip>:5000

# Tag images
docker tag catalog-service:latest <registry-url>/catalog-service:latest
docker tag inventory-service:latest <registry-url>/inventory-service:latest
docker tag api-gateway:latest <registry-url>/api-gateway:latest

# Push images
docker push <registry-url>/catalog-service:latest
docker push <registry-url>/inventory-service:latest
docker push <registry-url>/api-gateway:latest
```

## Updating Deployment Manifests

After pushing images, update the image references in:

- `manifests/deployments/catalog-service-deployment.yaml`
- `manifests/deployments/inventory-service-deployment.yaml`
- `manifests/deployments/api-gateway-deployment.yaml`

Change:
```yaml
image: catalog-service:latest
```

To:
```yaml
image: <registry>/catalog-service:latest
```

## Image Pull Secrets (if needed)

If using a private registry, add `imagePullSecrets` to deployments:

```yaml
spec:
  template:
    spec:
      imagePullSecrets:
      - name: regcred
      containers:
      - name: catalog-service
        image: <private-registry>/catalog-service:latest
```

---

## Quick Start (Docker Hub - Recommended)

Since Docker Hub is accessible, the quickest way to deploy:

```bash
# 1. Build images locally
cd ../03b-microservices-async
docker build -t catalog-service:latest -f catalog-service/Dockerfile catalog-service/
docker build -t inventory-service:latest -f inventory-service/Dockerfile inventory-service/
docker build -t api-gateway:latest -f api-gateway/Dockerfile api-gateway/

# 2. Tag for Docker Hub (replace 'yourusername' with your Docker Hub username)
docker tag catalog-service:latest yourusername/catalog-service:latest
docker tag inventory-service:latest yourusername/inventory-service:latest
docker tag api-gateway:latest yourusername/api-gateway:latest

# 3. Login and push (make images PUBLIC in Docker Hub settings)
docker login
docker push yourusername/catalog-service:latest
docker push yourusername/inventory-service:latest
docker push yourusername/api-gateway:latest

# 4. Update deployment manifests
# Edit manifests/deployments/*-deployment.yaml files
# Change: image: catalog-service:latest
# To: image: yourusername/catalog-service:latest
```

### Do I Need a Secret?

**Short answer**: 
- **Public images**: ❌ **NO secret needed**
- **Private images**: ✅ **YES, create a secret**

**Detailed answer**:

1. **If images are PUBLIC** (default):
   - ✅ No secret needed
   - Kubernetes can pull public images from Docker Hub without authentication
   - Just update the image name in deployment manifests

2. **If images are PRIVATE**:
   - ✅ **You MUST create a secret**
   - Run:
     ```bash
     kubectl create secret docker-registry dockerhub-secret \
       --docker-server=https://index.docker.io/v1/ \
       --docker-username=<your-username> \
       --docker-password=<your-password-or-token> \
       --docker-email=<your-email> \
       -n group-1
     ```
   - Then uncomment `imagePullSecrets` in deployment manifests

3. **To avoid rate limiting** (recommended):
   - Even for public images, using a secret helps avoid Docker Hub rate limits
   - Anonymous pulls: 100 pulls per 6 hours
   - Authenticated pulls: 200 pulls per 6 hours

**Example**: See `manifests/secrets/dockerhub-secret-example.yaml` for reference.

---

**✅ Docker Hub is confirmed accessible** - This is the recommended option for this cluster.
