# Kubernetes Deployment (RegLens AI)

This folder contains Kubernetes manifests to deploy **RegLens AI** backend (FastAPI) and frontend (Streamlit).

## What you must provide
- `GROQ_API_KEY` via a Kubernetes Secret
- `ALLOWED_ORIGINS` (comma-separated) if you need strict CORS

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
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-service.yaml
```

## Notes
- The backend can use `/app/data` for SQLite audit logging.
- ChromaDB is disabled; the backend uses local keyword retrieval over bundled regulation context.
- The backend is served on port `8000`.
- The frontend is served on port `8501`.

