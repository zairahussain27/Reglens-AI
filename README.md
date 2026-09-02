# RegLens AI


AI-powered regulatory compliance assistant for Indian FinTechs and MSMEs.

RegLens AI uses Groq Llama 3.3 to produce an auditable compliance checklist, risk summary, source documents, and downloadable reports.

## Stack
- Backend: FastAPI
- Frontend: Streamlit
- LLM: Groq API
- Vector retrieval: Qdrant Cloud semantic retrieval over regulatory chunks
- Audit log: SQLite
- Reports: ReportLab PDF and Markdown
- Deployment: Docker Compose or Kubernetes

## Required Environment

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Set at least:

```env
GROQ_API_KEY=your_groq_api_key
ALLOWED_ORIGINS=http://localhost:8501
DATABASE_URL=sqlite:///./data/reglens.db
BACKEND_API_URL=http://localhost:8000
```

For production containers, use:

```env
ENVIRONMENT=production
DATABASE_URL=sqlite:////app/data/reglens.db
```

## Local Development

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend in another terminal:

```bash
streamlit run src/app.py
```

Open:

- Frontend: `http://localhost:8501`
- Backend docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Docker Compose Deployment

Run a deployment preflight:

```bash
python scripts/deployment_check.py
```

Build and start both services:

```bash
docker compose up --build
```

Services:

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:8501`

Useful commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose down
```

## Build Images Manually

```bash
docker build -f Dockerfile.backend -t reglens-backend:latest .
docker build -f Dockerfile.frontend -t reglens-frontend:latest .
```

Run backend:

```bash
docker run --rm -p 8000:8000 --env-file .env \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=sqlite:////app/data/reglens.db \
  -v reglens-data:/app/data \
  reglens-backend:latest
```

Run frontend:

```bash
docker run --rm -p 8501:8501 \
  -e BACKEND_API_URL=http://host.docker.internal:8000 \
  reglens-frontend:latest
```

## Kubernetes Deployment

Build and push images to your registry, then update `image:` in the Kubernetes manifests if needed.

Create the secret:

```bash
kubectl create secret generic reglens-secrets \
  --from-literal=GROQ_API_KEY="<your_groq_api_key>"
```

Apply storage and config:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
```

Deploy backend and frontend:

```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
```

Check rollout:

```bash
kubectl rollout status deployment/reglens-backend
kubectl rollout status deployment/reglens-frontend
kubectl get svc reglens-frontend
```

## Testing And CI

Run tests:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The GitHub Actions workflow runs tests and builds both Docker images. Test failures now fail the CI job.

## Production Checklist

- `.env` or Kubernetes Secret contains a real `GROQ_API_KEY`.
- `ALLOWED_ORIGINS` contains the deployed frontend origin.
- `/health` returns HTTP 200 and reports Qdrant semantic retrieval as healthy.
- SQLite audit data is backed by persistent storage when required.
- Images are tagged with immutable release tags before production deployment.
- Frontend `BACKEND_API_URL` points to the reachable backend URL for that environment.
