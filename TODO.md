# TODO - Deployment Readiness (Docker/Kubernetes)

## Plan
- [x] 1) Update backend Docker runtime to use gunicorn (uvicorn worker) with production settings
- [x] 2) Update frontend Docker command to run Streamlit with explicit server address/port
- [x] 3) Ensure persistent volumes cover `/app/data` and `/app/chroma_db` expectations
- [x] 4) Add Kubernetes manifests for backend/frontend Deployments + Services
- [x] 5) Add Kubernetes PVCs for SQLite audit log and Chroma vector store
- [x] 6) Add ConfigMap/Secret examples for required environment variables
- [x] 7) Update README with Docker production + Kubernetes usage instructions
- [ ] 8) Dry-run YAML validation and quick container build checks


