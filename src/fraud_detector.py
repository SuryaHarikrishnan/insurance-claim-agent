"""
fraud_detector.py - Validation, consistency checks, and fraud heuristics.

Analyses extracted claim data and returns a structured report with:
  - missing_fields: required fields that were not extracted
  - inconsistencies: logical or data-level conflicts found
  - flags: fraud or suspicious-pattern warnings
"""

from datetime import datetime
from typing import Optional
from src.utils import get_logger, extract_all_dates, extract_dollar_amounts, parse_date

logger = get_logger()

# ─── Configuration ─────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ["claimant_name", "policy_number", "claim_amount", "incident_date"]
HIGH_AMOUNT_THRESHOLD = 10_000   # Flag claims above this value
EXTREME_AMOUNT_THRESHOLD = 500_000  # Likely fraudulent / data error


# ─── Individual Checks ─────────────────────────────────────────────────────────

def check_missing_fields(data: dict) -> list[str]:
    """Return list of required fields with None or empty values."""
    missing = []
    for field in REQUIRED_FIELDS:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    return missing


def check_claim_amount(amount: Optional[float]) -> list[str]:
    """Validate claim amount logic."""
    issues = []
    if amount is None:
        return issues  # Handled by missing_fields
    if amount <= 0:
        issues.append(f"Claim amount is non-positive: {amount}")
    if amount > EXTREME_AMOUNT_THRESHOLD:
        issues.append(f"Claim amount is abnormally high: ${amount:,.2f}")
    return issues


def check_incident_date(date_str: Optional[str]) -> list[str]:
    """Validate that incident date is not in the future."""
    issues = []
    if not date_str:
        return issues
    dt = parse_date(date_str)
    if dt is None:
        # Try ISO format (our standard output)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            issues.append(f"Could not parse incident date: '{date_str}'")
            return issues
    if dt > datetime.today():
        issues.append(f"Incident date is in the future: {date_str}")
    return issues


def check_policy_number_format(policy_number: Optional[str]) -> list[str]:
    """Sanity-check the policy number format."""
    issues = []
    if not policy_number:
        return issues
    if len(policy_number) < 4:
        issues.append(f"Policy number suspiciously short: '{policy_number}'")
    if policy_number.upper() in {"N/A", "NA", "NONE", "UNKNOWN", "TBD"}:
        issues.append(f"Policy number appears to be a placeholder: '{policy_number}'")
    return issues


def check_multiple_amounts(raw_text: str, extracted_amount: Optional[float]) -> list[str]:
    """
    Detect if the document contains wildly conflicting dollar amounts,
    which may indicate tampering or a confusing document.
    """
    issues = []
    if not raw_text or extracted_amount is None:
        return issues

    all_amounts = extract_dollar_amounts(raw_text)
    if len(all_amounts) < 2:
        return issues

    # Significant amounts (>= $100) excluding the extracted one
    significant = [a for a in all_amounts if a >= 100]
    if len(significant) < 2:
        return issues

    max_amt = max(significant)
    min_amt = min(significant)

    # If the range spans more than 10x and extracted is in the middle, flag it
    if max_amt > 0 and (max_amt / max(min_amt, 1)) > 10:
        issues.append(
            f"Multiple conflicting dollar amounts found in document "
            f"(range: ${min_amt:,.2f} – ${max_amt:,.2f}). "
            f"Extracted: ${extracted_amount:,.2f}."
        )
    return issues


def check_multiple_dates(raw_text: str) -> list[str]:
    """
    Flag documents that contain many different dates,
    which could indicate altered or composite documents.
    """
    issues = []
    if not raw_text:
        return issues
    all_dates = extract_all_dates(raw_text)
    unique_dates = set(all_dates)
    if len(unique_dates) > 5:
        issues.append(
            f"Unusually many dates found in document ({len(unique_dates)}). "
            "May indicate composite or altered document."
        )
    return issues


# ─── Fraud Heuristics ──────────────────────────────────────────────────────────

def run_fraud_heuristics(data: dict, raw_text: str) -> list[str]:
    """
    Apply fraud detection heuristics. Returns list of fraud flag strings.
    """
    flags = []

    amount = data.get("claim_amount")
    policy = data.get("policy_number")
    name = data.get("claimant_name")
    description = data.get("description") or ""

    # High-value claim flag
    if amount is not None and amount > HIGH_AMOUNT_THRESHOLD:
        flags.append(f"High-value claim: ${amount:,.2f} exceeds threshold of ${HIGH_AMOUNT_THRESHOLD:,}")

    # Missing critical identifiers
    if not policy:
        flags.append("Missing policy number — cannot verify coverage")
    if not name:
        flags.append("Missing claimant name — identity unverifiable")

    # Very short or vague description
    if len(description.strip()) < 30:
        flags.append("Claim description is very short or missing — insufficient detail")

    # Round-number amounts (often indicative of estimated/fabricated claims)
    if amount and amount > 1000 and amount % 1000 == 0:
        flags.append(f"Claim amount is a suspiciously round number: ${amount:,.0f}")

    # Keyword red flags in description
    suspicious_phrases = [
        "cash only", "no receipt", "do not contact", "urgent",
        "immediate payment", "wire transfer", "western union",
    ]
    desc_lower = description.lower()
    for phrase in suspicious_phrases:
        if phrase in desc_lower:
            flags.append(f"Suspicious phrase detected in description: '{phrase}'")

    return flags


# ─── Main Validation Entry Point ───────────────────────────────────────────────

def validate_claim(data: dict, raw_text: str = "") -> dict:
    """
    Run all validation and fraud checks on extracted claim data.

    Args:
        data: dict of extracted fields
        raw_text: original PDF text (used for cross-checks)

    Returns:
        {
            "missing_fields": [...],
            "inconsistencies": [...],
            "flags": [...]
        }
    """
    missing_fields = check_missing_fields(data)

    inconsistencies = []
    inconsistencies += check_claim_amount(data.get("claim_amount"))
    inconsistencies += check_incident_date(data.get("incident_date"))
    inconsistencies += check_policy_number_format(data.get("policy_number"))
    inconsistencies += check_multiple_amounts(raw_text, data.get("claim_amount"))
    inconsistencies += check_multiple_dates(raw_text)

    flags = run_fraud_heuristics(data, raw_text)

    logger.info(
        f"Validation — missing: {missing_fields}, "
        f"inconsistencies: {len(inconsistencies)}, flags: {len(flags)}"
    )

    return {
        "missing_fields": missing_fields,
        "inconsistencies": inconsistencies,
        "flags": flags,
    }