"""
parsers.py - PDF text extraction and intelligent field parsing.

Uses pdfplumber for text extraction, then applies regex + heuristic
keyword-proximity matching to extract structured fields from messy text.
"""

import re
from typing import Optional
from pathlib import Path

try:
    import pdfplumber
    PDF_BACKEND = "pdfplumber"
except ImportError:
    pdfplumber = None
    PDF_BACKEND = None

try:
    import fitz  # PyMuPDF
    if PDF_BACKEND is None:
        PDF_BACKEND = "pymupdf"
except ImportError:
    fitz = None

from src.utils import (
    clean_text, normalize_field_value, parse_date,
    extract_all_dates, extract_dollar_amounts, extract_policy_numbers,
    get_logger,
)

logger = get_logger()


# ─── PDF Text Extraction ───────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extract all text from a PDF file (handles multi-page).
    Tries pdfplumber first, falls back to PyMuPDF.
    Returns None if extraction fails.
    """
    path = Path(pdf_path)
    if not path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return None

    # Try pdfplumber
    if pdfplumber:
        try:
            pages_text = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
            if pages_text:
                logger.info(f"[pdfplumber] Extracted {len(pages_text)} page(s) from {path.name}")
                return clean_text("\n".join(pages_text))
        except Exception as e:
            logger.warning(f"pdfplumber failed for {path.name}: {e}")

    # Fallback to PyMuPDF
    if fitz:
        try:
            pages_text = []
            doc = fitz.open(str(path))
            for page in doc:
                text = page.get_text()
                if text:
                    pages_text.append(text)
            doc.close()
            if pages_text:
                logger.info(f"[PyMuPDF] Extracted {len(pages_text)} page(s) from {path.name}")
                return clean_text("\n".join(pages_text))
        except Exception as e:
            logger.warning(f"PyMuPDF failed for {path.name}: {e}")

    logger.error(f"Could not extract text from {path.name} — no working PDF backend or empty PDF.")
    return None


# ─── Field Extraction Helpers ──────────────────────────────────────────────────

def _find_value_near_keyword(text: str, keywords: list[str], pattern: str,
                              window: int = 120) -> Optional[str]:
    """
    Search for `pattern` in a window of characters following any of the keywords.
    Returns the first match found, or None.
    """
    for kw in keywords:
        # Find all occurrences of the keyword (case-insensitive)
        for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
            start = m.end()
            snippet = text[start: start + window]
            hit = re.search(pattern, snippet, re.IGNORECASE)
            if hit:
                return normalize_field_value(hit.group(0))
    return None


def _find_text_near_keyword(text: str, keywords: list[str],
                             window: int = 80) -> Optional[str]:
    """
    Extract a short text value (name-like) following a keyword.
    Stops at the next newline or punctuation boundary.
    """
    for kw in keywords:
        for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
            start = m.end()
            snippet = text[start: start + window]
            # Grab everything up to newline, colon, or delimiter
            hit = re.match(r"[\s:]*([A-Za-z][^\n\r:;,\d]{2,50})", snippet)
            if hit:
                val = normalize_field_value(hit.group(1))
                if len(val) >= 3:
                    return val
    return None


# ─── Individual Field Extractors ───────────────────────────────────────────────

def extract_claimant_name(text: str) -> Optional[str]:
    """
    Extract the claimant / insured / policyholder name.
    Strategy: look near known label keywords, then fall back to header patterns.
    """
    keywords = [
        "claimant name", "claimant:", "insured name", "insured:",
        "policyholder name", "policyholder:", "name of claimant",
        "name of insured", "submitted by", "filed by", "applicant:",
    ]
    name = _find_text_near_keyword(text, keywords)
    if name:
        return name

    # Try "Name: John Doe" pattern anywhere
    m = re.search(r"\bname\s*[:\-]\s*([A-Z][a-z]+(?: [A-Z][a-z]+)+)", text)
    if m:
        return normalize_field_value(m.group(1))

    return None


def extract_policy_number(text: str) -> Optional[str]:
    """Extract the best candidate policy number."""
    candidates = extract_policy_numbers(text)
    if candidates:
        return candidates[0]  # Take first (highest-priority) match

    # Broader fallback: alphanumeric code near "policy" keyword, must contain digits
    m = re.search(
        r"policy\s*(?:number|no|#|id)?[:\s#]*([A-Z0-9][-A-Z0-9]{4,14})",
        text, re.IGNORECASE
    )
    if m:
        val = normalize_field_value(m.group(1)).upper()
        if any(c.isdigit() for c in val):
            return val

    return None


def extract_claim_amount(text: str) -> Optional[float]:
    """
    Extract the primary claimed dollar amount.
    Prefers values near claim-amount keywords; falls back to largest amount in doc.
    """
    # Keywords that typically label the claim amount
    amount_keywords = [
        "claim amount", "amount claimed", "total claim", "damage cost",
        "loss amount", "requested amount", "compensation requested",
        "total loss", "amount of claim", "claimed amount",
    ]

    # Search near keywords first
    dollar_pattern = r"\$\s?([\d,]+(?:\.\d{1,2})?)"
    for kw in amount_keywords:
        for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
            snippet = text[m.end(): m.end() + 100]
            hit = re.search(dollar_pattern, snippet)
            if hit:
                try:
                    return float(hit.group(1).replace(",", ""))
                except ValueError:
                    pass

    # Fallback: return the largest dollar amount found anywhere in the document
    all_amounts = extract_dollar_amounts(text)
    if all_amounts:
        return max(all_amounts)

    return None


def extract_incident_date(text: str) -> Optional[str]:
    """
    Extract the incident / accident / loss date.
    Returns ISO-format string (YYYY-MM-DD) or the raw string if parse fails.
    """
    date_keywords = [
        "incident date", "date of incident", "date of accident",
        "accident date", "date of loss", "loss date", "event date",
        "occurred on", "happened on", "date of event", "date of occurrence",
    ]

    # Search in a window after each keyword
    date_pattern = r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}|" \
                   r"(?:January|February|March|April|May|June|July|August|September|" \
                   r"October|November|December)\s+\d{1,2},?\s+\d{4}|" \
                   r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|" \
                   r"September|October|November|December)\s+\d{4}|" \
                   r"\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2,4}"

    raw_date = _find_value_near_keyword(text, date_keywords, date_pattern)

    if raw_date:
        dt = parse_date(raw_date)
        if dt:
            return dt.strftime("%Y-%m-%d")
        return raw_date  # Return raw if parse fails

    # Fallback: find all dates, return the first plausible one (not today/future)
    from datetime import datetime
    all_dates = extract_all_dates(text)
    today = datetime.today()
    for d in all_dates:
        dt = parse_date(d)
        if dt and dt <= today:
            return dt.strftime("%Y-%m-%d")

    return None


def extract_claim_type(text: str) -> Optional[str]:
    """
    Identify the type of insurance claim from known categories.
    """
    categories = {
        "auto": ["auto", "vehicle", "car", "truck", "motorcycle", "collision",
                 "automobile", "motor vehicle"],
        "health": ["medical", "health", "hospital", "surgery", "treatment",
                   "healthcare", "injury", "illness", "doctor"],
        "property": ["property", "home", "house", "building", "fire", "flood",
                     "theft", "burglary", "damage to property", "dwelling"],
        "life": ["life insurance", "death benefit", "beneficiary", "deceased",
                 "death claim"],
        "liability": ["liability", "third party", "legal", "lawsuit", "negligence"],
        "travel": ["travel", "trip cancellation", "lost luggage", "flight"],
        "disability": ["disability", "unable to work", "long-term disability"],
    }

    text_lower = text.lower()
    for claim_type, keywords in categories.items():
        for kw in keywords:
            if kw in text_lower:
                return claim_type.capitalize()

    # Check for explicit "Type of Claim:" label
    m = re.search(r"(?:type of claim|claim type)[:\s]+([A-Za-z /]+)", text, re.IGNORECASE)
    if m:
        return normalize_field_value(m.group(1)).capitalize()

    return None


def extract_description(text: str) -> Optional[str]:
    """
    Extract a description of the incident.
    Looks for labeled sections; falls back to the first substantive paragraph.
    """
    desc_keywords = [
        "description of incident", "incident description", "description of loss",
        "description of claim", "details of incident", "accident description",
        "nature of claim", "what happened", "describe the incident",
        "claim description", "description:",
    ]

    for kw in desc_keywords:
        m = re.search(re.escape(kw), text, re.IGNORECASE)
        if m:
            start = m.end()
            # Grab up to 400 chars, stop at next labeled section
            snippet = text[start: start + 400]
            snippet = re.split(r"\n[A-Z][A-Za-z ]+:", snippet)[0]
            snippet = normalize_field_value(snippet)
            if len(snippet) > 20:
                return snippet[:400]

    # Fallback: return the longest paragraph
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 60]
    if paragraphs:
        return sorted(paragraphs, key=len, reverse=True)[0][:400]

    return None


# ─── Main Extraction Entry Point ───────────────────────────────────────────────

def extract_structured_data(text: str) -> dict:
    """
    Run all field extractors on the cleaned text.
    Returns a dict with all extracted fields (value may be None if not found).
    """
    return {
        "claimant_name": extract_claimant_name(text),
        "policy_number": extract_policy_number(text),
        "claim_amount": extract_claim_amount(text),
        "incident_date": extract_incident_date(text),
        "claim_type": extract_claim_type(text),
        "description": extract_description(text),
    }


def parse_pdf(pdf_path: str) -> tuple[Optional[str], dict]:
    """
    Full parse pipeline for a single PDF.

    Returns:
        (raw_text, extracted_data_dict)
        raw_text is None if extraction failed entirely.
    """
    raw_text = extract_text_from_pdf(pdf_path)
    if raw_text is None:
        logger.error(f"Skipping extraction — could not read {pdf_path}")
        return None, {}

    data = extract_structured_data(raw_text)
    logger.info(f"Extracted fields: { {k: v for k, v in data.items() if v is not None} }")
    return raw_text, data