# RegLens AI - Quick Wins & Priority Fixes

## 🚨 Do These FIRST (Critical - Can Break in Production)

### Fix #1: Update Regulations Script (5 mins)
**File:** `update_regulations.py`

**Current Problem:**
- Script prints "Update complete" even if all sources fail
- Knowledge base becomes empty without alerting anyone

**Quick Fix:**
```python
# update_regulations.py - Add validation
def update_regulations():
    print("🔄 Updating RegLens AI knowledge base...")
    summary = ingest_all_from_urls(GOVERNMENT_SOURCES)
    
    # ADD THIS CHECK:
    if summary.get("successful", 0) == 0:
        print("❌ CRITICAL ERROR: No regulations were successfully ingested!")
        print(f"Total attempted: {summary.get('total', 0)}")
        print(f"Failed/Rejected: {summary.get('rejected_or_failed', 0)}")
        sys.exit(1)  # Exit with error
    
    print(f"✅ Success: {summary['successful']}/{summary['total']} regulations ingested")
    if summary.get("rejected_or_failed", 0) > 0:
        print(f"⚠️  {summary['rejected_or_failed']} sources had issues")

if __name__ == "__main__":
    update_regulations()
```

---

### Fix #2: Database Thread Safety (15 mins)
**File:** `src/db.py`

**Current Problem:**
- `check_same_thread=False` disables thread safety
- Concurrent requests cause "database is locked" errors
- Audit logs silently fail to save

**Quick Fix - Add Thread Lock:**
```python
# src/db.py
import threading

db_lock = threading.Lock()

def log_request(profile: Dict[str, str], status: str, result_text: str, source_documents: str | None = None) -> int:
    with db_lock:  # ADD THIS LINE
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO compliance_requests (
                timestamp, business_type, industry, services,
                customer_type, transaction_type, revenue,
                status, result_text, source_documents
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                profile.get("business_type", ""),
                profile.get("industry", ""),
                profile.get("services", ""),
                profile.get("customer_type", ""),
                profile.get("transaction_type", ""),
                profile.get("revenue", ""),
                status,
                result_text,
                source_documents,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id  # ADD THIS LINE

def fetch_recent_requests(limit: int = 50) -> List[Dict]:
    with db_lock:  # ADD THIS LINE
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM compliance_requests ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
```

---

### Fix #3: Groq Timeout Not Working (10 mins)
**File:** `src/compliance_engine.py`

**Current Problem:**
- `timeout=30` parameter is ignored by Groq library
- System hangs indefinitely if API is unresponsive

**Quick Fix - Add Timing Check:**
```python
# src/compliance_engine.py - Replace the try-except block
import time

start_time = time.time()
timeout_seconds = 35  # 35-second hard timeout

try:
    logger.info("Starting Groq API call...")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2000,
        messages=[...],
        temperature=0.1,
        # Remove: timeout=30  (doesn't work anyway)
    )
    elapsed = time.time() - start_time
    logger.info(f"Groq API completed in {elapsed:.2f}s")
    return response.choices[0].message.content, source_documents

except Exception as exc:
    elapsed = time.time() - start_time
    logger.error(f"Groq API error after {elapsed:.2f}s: {str(exc)}")
    
    # If it's taking too long, it might be hung
    if elapsed > 30:
        return """
## ⚠️ Response Timeout

RegLens AI did not receive a response within a reasonable time (>{:.0f}s).

This may indicate:
- Groq API is overloaded
- Network connectivity issue
- Your API key is invalid

**What to do:** Try again in a moment or verify your GROQ_API_KEY.
        """.format(elapsed), source_documents
    
    return f"""
## ⚠️ API Error

Groq API error: {str(exc)}

**What to do:** Please try again or contact support if issue persists.
    """, source_documents
```

---

### Fix #4: Retriever Error Handling (10 mins)
**File:** `src/retriever.py`

**Current Problem:**
- No error handling; crashes if ChromaDB is empty or broken
- One corrupted entry breaks all compliance checks

**Quick Fix - Add Try-Except:**
```python
# src/retriever.py - Wrap the function with error handling
import logging

logger = logging.getLogger(__name__)

def retrieve(query, n_results=5):
    try:
        # Validate input
        if not query or not isinstance(query, str):
            logger.warning(f"Invalid query: {query}")
            return []
        
        embedding = model.encode(query).tolist()
        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        
        chunks = results.get("documents", [[]])[0]  # Safe access
        metadatas = results.get("metadatas", [[]])[0]  # Safe access
        
        if not chunks:
            logger.warning("No chunks returned from ChromaDB")
            return []
        
        # Filter results to only include trusted sources
        filtered_results = []
        for chunk, metadata in zip(chunks, metadatas):
            if not isinstance(chunk, str) or not metadata:
                continue
                
            source_url = metadata.get("source_url")
            if source_url and is_trusted_domain(source_url):
                filtered_results.append((chunk, source_url))
            elif not source_url:
                filtered_results.append((chunk, metadata.get("source", "local")))
        
        return filtered_results
    
    except Exception as e:
        logger.error(f"Error in retrieve(): {str(e)}")
        return []  # Return empty - will trigger guardrail
```

---

### Fix #5: Environment Variable Validation (10 mins)
**File:** `src/compliance_engine.py`

**Current Problem:**
- If GROQ_API_KEY is missing, app crashes at import time with confusing error
- No default for other settings

**Quick Fix - Better Error Messages:**
```python
# src/compliance_engine.py - Replace the validation section
import sys

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("\n" + "="*60)
    print("❌ CONFIGURATION ERROR")
    print("="*60)
    print("GROQ_API_KEY environment variable is not set.")
    print("\nHow to fix:")
    print("1. Create a .env file in the project root (or copy .env.example)")
    print("2. Add: GROQ_API_KEY=your_key_here")
    print("3. Get your key from: https://console.groq.com")
    print("\nAlternatively, set environment variable:")
    print("   export GROQ_API_KEY=your_key_here")
    print("="*60 + "\n")
    sys.exit(1)

try:
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"❌ Failed to initialize Groq client: {str(e)}")
    sys.exit(1)
```

---

### Fix #6: Add Basic Logging (15 mins)
**File:** `src/api.py`

**Current Problem:**
- Zero logging in production
- Cannot debug issues
- No request/response visibility

**Quick Fix - Add Request Logging:**
```python
# src/api.py - Add at the top
import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add middleware to log all requests
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        elapsed = time.time() - start_time
        
        logger.info(f"{request.method} {request.url.path} - {response.status_code} ({elapsed:.2f}s)")
        return response

app.add_middleware(LoggingMiddleware)

# Log important operations
@app.post("/api/compliance-check", response_model=ComplianceResponse)
@limiter.limit("10/minute")
def compliance_check(request: Request, profile: BusinessProfile) -> JSONResponse:
    logger.info(f"Compliance check requested for {profile.industry}")
    try:
        result, source_documents = run_compliance_check_with_sources(profile.dict())
        logger.info(f"Compliance check succeeded")
        log_request(profile.dict(), status="success", result_text=result, ...)
        return JSONResponse(status_code=200, content={...})
    except Exception as exc:
        logger.error(f"Compliance check failed: {str(exc)}", exc_info=True)
        log_request(profile.dict(), status="error", result_text=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
```

---

## 🔧 Do These NEXT (High Priority - 1-2 Days)

### Fix #7: Pin Dependency Versions (10 mins)
**File:** `requirements.txt`

**Current Problem:**
- Uses `>=` version specifiers
- `streamlit>=1.20` could install v1.40 in production
- Breaking changes in dependencies break deployment

**Quick Fix:**
```bash
# Generate locked dependencies
pip freeze > requirements.txt

# Or manually pin critical ones:
# requirements.txt
fastapi==0.108.0
uvicorn[standard]==0.25.0
pydantic==2.5.2
python-dotenv==1.0.0
requests==2.31.0
pdfplumber==0.10.3
chromadb==0.4.18
sentence-transformers==2.2.2
groq==0.4.1
slowapi==0.1.9
reportlab==4.0.9
streamlit==1.30.0
```

---

### Fix #8: Add Type Hints (30 mins)
**File:** `src/db.py` and `src/retriever.py`

**Current Problem:**
- No return type hints
- IDE can't catch type errors
- Hard to maintain

**Quick Fix - Add Type Hints:**
```python
# src/db.py
from typing import Dict, List, Optional

def get_connection() -> sqlite3.Connection:
    """Get SQLite database connection"""
    ...

def log_request(
    profile: Dict[str, str],
    status: str,
    result_text: str,
    source_documents: Optional[str] = None
) -> int:
    """Log compliance request. Returns record ID."""
    ...

def fetch_recent_requests(limit: int = 50) -> List[Dict]:
    """Fetch recent compliance requests"""
    ...

# src/retriever.py
from typing import List, Tuple

def retrieve(query: str, n_results: int = 5) -> List[Tuple[str, str]]:
    """
    Retrieve regulation chunks.
    
    Returns:
        List of (chunk_text, source_url) tuples
    """
    ...
```

---

### Fix #9: Improve Health Check (10 mins)
**File:** `src/api.py`

**Current Problem:**
- `/health` always returns 200 even if system is broken
- Load balancer can't detect failures

**Quick Fix:**
```python
# src/api.py
@app.get("/health")
def health_check() -> dict:
    """Check if all system components are healthy"""
    health = {
        "status": "healthy",
        "components": {}
    }
    
    # Check database
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        health["components"]["database"] = "ok"
    except Exception as e:
        health["components"]["database"] = f"error: {str(e)}"
        health["status"] = "unhealthy"
    
    # Check ChromaDB
    try:
        collection.count()
        health["components"]["chromadb"] = "ok"
    except Exception as e:
        health["components"]["chromadb"] = f"error: {str(e)}"
        health["status"] = "unhealthy"
    
    # Check if embeddings model loaded
    try:
        model.encode("test")
        health["components"]["embeddings"] = "ok"
    except Exception as e:
        health["components"]["embeddings"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health)
```

---

## 📋 Implementation Checklist

### Week 1 (Critical Fixes)
- [ ] Fix update_regulations.py validation
- [ ] Add thread lock to database
- [x] Fix timeout handling
- [x] Add error handling to retriever
- [ ] Add environment variable validation
- [x] Add basic logging

### Week 2 (High Priority)
- [ ] Pin dependency versions
- [ ] Add type hints
- [x] Improve health check
- [ ] Add retry logic to frontend
- [ ] Add CORS validation
- [ ] Create .env.example

### Week 3 (Medium Priority)
- [ ] Add database indexes
- [ ] Implement caching (optional)
- [ ] Improve error messages
- [x] Add request/response logging
- [ ] Add monitoring/metrics

### Week 4+ (Production Hardening)
- [ ] Authentication (JWT)
- [ ] Database migrations (Alembic)
- [x] Separate Docker images
- [ ] Load testing
- [ ] Security audit
- [ ] Disaster recovery

---

## 🧪 Testing Your Fixes

```bash
# Test 1: Update script validates success
python update_regulations.py
# Should succeed or exit with error (not "Update complete")

# Test 2: Database threading under load
python test_concurrent_requests.py
# Should handle 100+ concurrent requests without "database is locked"

# Test 3: API health check
curl http://localhost:8000/health
# Should return component statuses

# Test 4: Timeout handling
# (Temporarily break Groq API) - should timeout gracefully

# Test 5: Error handling in retriever
# Delete chroma_db and restart - should still work (return guardrail message)
```

---

## 📞 Need Help?

Check your project audit report: `PROJECT_AUDIT_REPORT.md`

Each issue has:
- Why it's broken
- Business impact
- Code fix example
- Testing instructions
