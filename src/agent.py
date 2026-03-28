"""
agent.py - Orchestrator for the insurance claim processing pipeline.

Coordinates: PDF load → text extraction → field extraction →
             fraud validation → decision making → result assembly.
"""

from pathlib import Path
from src.parsers import parse_pdf
from src.fraud_detector import validate_claim
from src.utils import get_logger

logger = get_logger()


# ─── Decision Engine ───────────────────────────────────────────────────────────

# Fields that, if missing, trigger an automatic REJECT
CRITICAL_FIELDS = {"claimant_name", "policy_number", "claim_amount"}


def make_decision(validation: dict) -> dict:
    """
    Determine claim status based on validation results.

    Rules:
      REJECT  - any critical required field missing OR major inconsistency
      FLAG    - fraud flags present OR non-critical missing fields OR minor inconsistencies
      ACCEPT  - no missing fields, no inconsistencies, no flags
    """
    missing = validation.get("missing_fields", [])
    inconsistencies = validation.get("inconsistencies", [])
    flags = validation.get("flags", [])

    # Critical missing fields → hard reject
    critical_missing = [f for f in missing if f in CRITICAL_FIELDS]
    if critical_missing:
        return {
            "status": "REJECT",
            "reason": (
                f"Missing critical field(s): {', '.join(critical_missing)}. "
                "Claim cannot be processed without this information."
            ),
        }

    # Major inconsistencies (amount ≤ 0, future date, extreme amount) → reject
    critical_inconsistencies = [
        i for i in inconsistencies
        if any(phrase in i.lower() for phrase in
               ["non-positive", "future", "abnormally high"])
    ]
    if critical_inconsistencies:
        return {
            "status": "REJECT",
            "reason": "Major data inconsistency: " + "; ".join(critical_inconsistencies),
        }

    # Fraud flags or non-critical issues → flag for review
    if flags or inconsistencies or missing:
        reasons = []
        if flags:
            reasons.append("Fraud indicators: " + "; ".join(flags))
        if inconsistencies:
            reasons.append("Data issues: " + "; ".join(inconsistencies))
        if missing:
            reasons.append(f"Non-critical missing field(s): {', '.join(missing)}")
        return {
            "status": "FLAG",
            "reason": " | ".join(reasons),
        }

    # All clear
    return {
        "status": "ACCEPT",
        "reason": "All required fields present, no inconsistencies detected, claim appears valid.",
    }


# ─── Main Agent Entry Point ────────────────────────────────────────────────────

def process_claim(pdf_path: str) -> dict:
    """
    Full processing pipeline for a single insurance claim PDF.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        Result dict with keys: file_name, extracted_data, validation, decision.
        On hard failure, returns a minimal error result.
    """
    path = Path(pdf_path)
    file_name = path.name
    logger.info(f"{'='*60}")
    logger.info(f"Processing: {file_name}")

    # ── Step 1 & 2: Load PDF + Extract Text ──────────────────────────────────
    try:
        raw_text, extracted_data = parse_pdf(str(path))
    except Exception as e:
        logger.error(f"Fatal error parsing {file_name}: {e}")
        return _error_result(file_name, f"PDF parsing failed: {e}")

    if raw_text is None:
        return _error_result(file_name, "Could not extract text from PDF (corrupted or empty)")

    # ── Step 3: Fraud Detection & Validation ─────────────────────────────────
    try:
        validation = validate_claim(extracted_data, raw_text)
    except Exception as e:
        logger.error(f"Validation error for {file_name}: {e}")
        validation = {"missing_fields": [], "inconsistencies": [str(e)], "flags": []}

    # ── Step 4: Decision ──────────────────────────────────────────────────────
    decision = make_decision(validation)

    logger.info(f"Decision for {file_name}: {decision['status']} — {decision['reason'][:80]}")

    return {
        "file_name": file_name,
        "extracted_data": extracted_data,
        "validation": validation,
        "decision": decision,
    }


def _error_result(file_name: str, reason: str) -> dict:
    """Build a standardised error result when processing cannot proceed."""
    return {
        "file_name": file_name,
        "extracted_data": {},
        "validation": {
            "missing_fields": ["all"],
            "inconsistencies": [],
            "flags": [],
        },
        "decision": {
            "status": "REJECT",
            "reason": reason,
        },
    }