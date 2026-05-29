# Kubernetes Deployment (RegLens AI)

This folder contains Kubernetes manifests to deploy **RegLens AI** backend (FastAPI) and frontend (Streamlit).

## What you must provide
- `GROQ_API_KEY` via a Kubernetes Secret
- `ALLOWED_ORIGINS` (comma-separated) if you need strict CORS
- A populated ChromaDB PVC. Use `ingest-job.yaml` before deploying the backend.

## Example Secret
Create a secret named `reglens-secrets`:

```bash
kubectl create secret generic reglens-secrets \
  --from-literal=GROQ_API_KEY="<your_groq_api_key>" \
  --from-literal=ALLOWED_ORIGINS="<comma-separated-origins>"
```

## Apply
```bash
kubectl apply -f configmap.yaml
kubectl apply -f pvc.yaml
kubectl apply -f ingest-job.yaml
kubectl wait --for=condition=complete job/reglens-ingest --timeout=20m
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-service.yaml
```

## Notes
- Both backend and frontend use PVCs for persistence:
  - `/app/data` for SQLite audit logging
  - `/app/chroma_db` for Chroma vector store
- `REQUIRE_VECTOR_STORE_READY=true` makes backend readiness fail if the Chroma index is empty.
- The backend is served on port `8000`.
- The frontend is served on port `8501`.

