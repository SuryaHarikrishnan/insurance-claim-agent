"""
main.py - Entry point for the insurance claim processing pipeline.

Scans the sample_claims/ directory for PDF files, processes each one
through the agent, and saves all results to output/results.json.
"""

import sys
from pathlib import Path

# Ensure src/ is importable when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.agent import process_claim
from src.database import save_all_results, clear_results
from src.utils import get_logger

logger = get_logger()

CLAIMS_DIR = Path(__file__).resolve().parent / "sample_claims"
OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "results.json"


def find_pdfs(directory: Path) -> list[Path]:
    """Return sorted list of PDF files in the given directory."""
    if not directory.exists():
        logger.warning(f"Claims directory not found: {directory}")
        return []
    pdfs = sorted(directory.glob("*.pdf"))
    logger.info(f"Found {len(pdfs)} PDF(s) in {directory}")
    return pdfs


def main():
    logger.info("=" * 60)
    logger.info("  Insurance Claim Processing Agent — Starting")
    logger.info("=" * 60)

    pdfs = find_pdfs(CLAIMS_DIR)

    if not pdfs:
        logger.warning("No PDF files found. Place claims in the sample_claims/ directory.")
        # Still write an empty results file so callers don't fail
        save_all_results([], OUTPUT_PATH)
        return

    # Reset output file at the start of each batch run
    clear_results(OUTPUT_PATH)

    all_results = []
    stats = {"ACCEPT": 0, "FLAG": 0, "REJECT": 0, "ERROR": 0}

    for pdf_path in pdfs:
        try:
            result = process_claim(str(pdf_path))
        except Exception as e:
            logger.error(f"Unexpected error for {pdf_path.name}: {e}")
            result = {
                "file_name": pdf_path.name,
                "extracted_data": {},
                "validation": {"missing_fields": [], "inconsistencies": [], "flags": []},
                "decision": {"status": "REJECT", "reason": f"Unexpected processing error: {e}"},
            }

        all_results.append(result)
        status = result.get("decision", {}).get("status", "ERROR")
        stats[status] = stats.get(status, 0) + 1

    # Write final batch output
    save_all_results(all_results, OUTPUT_PATH)

    # Summary report
    logger.info("=" * 60)
    logger.info(f"  Processing complete. {len(all_results)} claim(s) processed.")
    logger.info(f"  ACCEPT: {stats['ACCEPT']}  |  FLAG: {stats['FLAG']}  |  REJECT: {stats['REJECT']}")
    logger.info(f"  Results saved to: {OUTPUT_PATH}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()