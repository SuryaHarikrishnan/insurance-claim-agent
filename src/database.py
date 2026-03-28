"""
database.py - Storage layer for claim processing results.

Handles reading and writing results.json, with safe append semantics
and atomic writes to prevent file corruption.
"""

import json
import os
import tempfile
from pathlib import Path
from src.utils import get_logger

logger = get_logger()

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "output" / "results.json"


def _ensure_output_dir(output_path: Path) -> None:
    """Create output directory if it doesn't exist."""
    output_path.parent.mkdir(parents=True, exist_ok=True)


def load_results(output_path: Path = DEFAULT_OUTPUT_PATH) -> list[dict]:
    """
    Load existing results from JSON file.
    Returns empty list if file doesn't exist or is malformed.
    """
    if not output_path.exists():
        return []
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            logger.warning(f"results.json is not a list — resetting.")
            return []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load results from {output_path}: {e}")
        return []


def _atomic_write(output_path: Path, data: list) -> bool:
    """
    Write JSON data to a temp file then rename (atomic on most OS).
    Returns True on success, False on failure.
    """
    _ensure_output_dir(output_path)
    dir_ = output_path.parent
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp_path, output_path)
        return True
    except OSError as e:
        logger.error(f"Failed to write results to {output_path}: {e}")
        # Clean up temp file if it still exists
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return False


def save_result(result: dict, output_path: Path = DEFAULT_OUTPUT_PATH) -> bool:
    """
    Append a single claim result to the JSON file.
    Safe: loads existing data, appends, then writes atomically.
    """
    existing = load_results(output_path)
    existing.append(result)
    success = _atomic_write(output_path, existing)
    if success:
        logger.info(f"Saved result for '{result.get('file_name', '?')}' → {output_path}")
    return success


def save_all_results(results: list[dict], output_path: Path = DEFAULT_OUTPUT_PATH) -> bool:
    """
    Write (overwrite) the full list of results to JSON.
    Used at the end of a complete batch run.
    """
    success = _atomic_write(output_path, results)
    if success:
        logger.info(f"Saved {len(results)} result(s) → {output_path}")
    return success


def clear_results(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    """Reset the results file to an empty list."""
    _atomic_write(output_path, [])
    logger.info(f"Cleared results at {output_path}")