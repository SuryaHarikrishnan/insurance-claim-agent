"""
utils.py - Helper functions for text cleaning, regex, date parsing, and logging.
"""

import re
import logging
from datetime import datetime
from typing import Optional


# ─── Logging Setup ────────────────────────────────────────────────────────────

def get_logger(name: str = "insurance_agent") -> logging.Logger:
    """Return a configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger()


# ─── Text Cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    if not text:
        return ""
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    # Collapse multiple spaces/tabs into one
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse more than 2 consecutive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_field_value(value: str) -> str:
    """Strip surrounding whitespace, punctuation artifacts from extracted values."""
    if not value:
        return ""
    value = value.strip(" \t\n:;,-")
    return value


# ─── Regex Helpers ─────────────────────────────────────────────────────────────

# Matches common date formats: MM/DD/YYYY, YYYY-MM-DD, Month DD YYYY, DD-Mon-YYYY, etc.
DATE_PATTERNS = [
    r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b",                    # MM/DD/YYYY or MM-DD-YYYY
    r"\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b",                       # YYYY-MM-DD
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",            # Month DD, YYYY
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{4})\b",                 # DD Month YYYY
    r"\b(\d{1,2})-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2,4})\b",  # DD-Mon-YY
]

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(raw: str) -> Optional[datetime]:
    """
    Try to parse a raw date string into a datetime object.
    Returns None if parsing fails.
    """
    raw = raw.strip()

    # Try standard formats first
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    # Try Month DD, YYYY
    m = re.match(
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})",
        raw, re.IGNORECASE
    )
    if m:
        month = MONTH_MAP.get(m.group(1).lower())
        if month:
            try:
                return datetime(int(m.group(3)), month, int(m.group(2)))
            except ValueError:
                pass

    # Try DD Month YYYY
    m = re.match(
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{4})",
        raw, re.IGNORECASE
    )
    if m:
        month = MONTH_MAP.get(m.group(2).lower())
        if month:
            try:
                return datetime(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                pass

    # Try DD-Mon-YY
    m = re.match(
        r"(\d{1,2})-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2,4})",
        raw, re.IGNORECASE
    )
    if m:
        month = MONTH_MAP.get(m.group(2).lower())
        year = int(m.group(3))
        if year < 100:
            year += 2000
        if month:
            try:
                return datetime(year, month, int(m.group(1)))
            except ValueError:
                pass

    return None


def extract_all_dates(text: str) -> list[str]:
    """Find all date-like strings in text."""
    found = []
    for pat in DATE_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            found.append(m.group(0))
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for d in found:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


def extract_dollar_amounts(text: str) -> list[float]:
    """Extract all dollar amounts from text, return as floats."""
    pattern = r"\$\s?([\d,]+(?:\.\d{1,2})?)"
    matches = re.findall(pattern, text)
    amounts = []
    for m in matches:
        try:
            amounts.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return amounts


def extract_policy_numbers(text: str) -> list[str]:
    """
    Extract potential policy numbers.
    Common formats: POL-XXXXXXX, INS-XXXXXXX, alphanumeric 6-15 chars near keywords.
    """
    # Common English words that start with policy-number prefixes — exclude these
    FALSE_POSITIVES = {
        "URANCE", "ICY", "OLICY", "SURANCE", "CLAIM", "CLAIMANT",
        "NUMBER", "NUMBERS", "TYPE", "SUBMISSION", "INSURED",
    }

    # Explicit prefixed patterns: must have a separator (dash/space) and digits
    prefixed = re.findall(
        r"\b(?:POL|INS|CLM)[-]([A-Z0-9]{4,15})\b",
        text, re.IGNORECASE
    )
    # Near keyword context: "Policy Number: <value>"
    contextual = re.findall(
        r"(?:policy\s*(?:number|no|#|id)\s*[:\s#]+)\s*([A-Z0-9][-A-Z0-9]{4,14})",
        text, re.IGNORECASE
    )
    combined = [p.upper() for p in prefixed + contextual]
    # Filter out false positives and pure-alpha codes without digits
    filtered = []
    for p in combined:
        if p in FALSE_POSITIVES:
            continue
        if not any(c.isdigit() for c in p):
            continue  # policy numbers almost always contain digits
        filtered.append(p)

    # Deduplicate
    seen = set()
    result = []
    for p in filtered:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result