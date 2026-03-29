"""
api.py - FastAPI backend for the insurance claim processing pipeline.

Endpoints:
  POST   /claims          Upload a PDF → get ACCEPT/FLAG/REJECT decision
  GET    /claims          List all processed claims
  GET    /claims/{id}     Get a single claim by ID
  DELETE /claims/{id}     Remove a claim from results

Run with:
  uvicorn api:app --reload
"""

import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agent import process_claim
from src.database import load_results, save_all_results
from src.utils import get_logger

logger = get_logger()

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Insurance Claim Processing API",
    description="Upload insurance claim PDFs and receive automated ACCEPT / FLAG / REJECT decisions.",
    version="1.0.0",
)

# Allow all origins for now — lock this down when you have a real frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp folder for uploaded PDFs during processing
UPLOAD_DIR  = Path("uploads")
OUTPUT_PATH = Path("output/results.json")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_PATH.parent.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_all_claims() -> list[dict]:
    """Load current results, adding a stable `id` field to each."""
    results = load_results(OUTPUT_PATH)
    for i, r in enumerate(results):
        if "id" not in r:
            r["id"] = str(i + 1)
    return results


def _save_all_claims(claims: list[dict]) -> None:
    save_all_results(claims, OUTPUT_PATH)


def _find_claim(claim_id: str) -> tuple[int, dict]:
    """Return (index, claim) or raise 404."""
    claims = _get_all_claims()
    for i, c in enumerate(claims):
        if c.get("id") == claim_id:
            return i, c
    raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Health check — confirms the API is running."""
    return {"status": "ok", "message": "Insurance Claim Processing API is running."}


@app.post("/claims", status_code=201, tags=["Claims"])
async def submit_claim(file: UploadFile = File(...)):
    """
    Upload a PDF insurance claim.

    - Saves the file temporarily
    - Runs the full extraction + fraud detection pipeline
    - Returns the decision immediately
    - Persists the result to output/results.json
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Save upload to a temp path with a unique name to avoid collisions
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    temp_path   = UPLOAD_DIR / unique_name

    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        logger.info(f"Received upload: {file.filename} → {temp_path}")

        # Run the pipeline
        result = process_claim(str(temp_path))

        # Assign a unique ID and store the original filename
        result["id"]            = str(uuid.uuid4())
        result["file_name"]     = file.filename   # show user's filename, not temp name
        result["original_name"] = file.filename

        # Persist to results.json
        claims = _get_all_claims()
        claims.append(result)
        _save_all_claims(claims)

        logger.info(f"Claim processed: {file.filename} → {result['decision']['status']}")
        return result

    except Exception as e:
        logger.error(f"Error processing {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    finally:
        # Always clean up the temp file
        if temp_path.exists():
            temp_path.unlink()


@app.get("/claims", tags=["Claims"])
def list_claims(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List all processed claims.

    Optional filters:
    - `status` — filter by decision: ACCEPT, FLAG, or REJECT
    - `limit`  — max number of results to return (default 100)
    - `offset` — pagination offset (default 0)
    """
    claims = _get_all_claims()

    # Filter by status if provided
    if status:
        status_upper = status.upper()
        if status_upper not in {"ACCEPT", "FLAG", "REJECT"}:
            raise HTTPException(
                status_code=400,
                detail="status must be one of: ACCEPT, FLAG, REJECT"
            )
        claims = [c for c in claims if c.get("decision", {}).get("status") == status_upper]

    total    = len(claims)
    paginated = claims[offset: offset + limit]

    return {
        "total":  total,
        "offset": offset,
        "limit":  limit,
        "claims": paginated,
    }


@app.get("/claims/summary", tags=["Claims"])
def claims_summary():
    """
    Return a count breakdown by decision status.
    Useful for a dashboard overview card.
    """
    claims = _get_all_claims()
    summary = {"ACCEPT": 0, "FLAG": 0, "REJECT": 0, "total": len(claims)}
    for c in claims:
        status = c.get("decision", {}).get("status", "")
        if status in summary:
            summary[status] += 1
    return summary


@app.get("/claims/{claim_id}", tags=["Claims"])
def get_claim(claim_id: str):
    """
    Get full details for a single claim by its ID.

    Returns extracted data, validation results, and the final decision.
    """
    _, claim = _find_claim(claim_id)
    return claim


@app.delete("/claims/{claim_id}", status_code=200, tags=["Claims"])
def delete_claim(claim_id: str):
    """
    Remove a claim from the results store by its ID.

    Does not delete the original PDF (already removed after processing).
    """
    idx, claim = _find_claim(claim_id)
    claims = _get_all_claims()
    claims.pop(idx)
    _save_all_claims(claims)
    logger.info(f"Deleted claim: {claim_id} ({claim.get('file_name')})")
    return {
        "message": f"Claim '{claim_id}' deleted successfully.",
        "deleted": claim,
    }