"""Unit tests for src/fraud_detector.py validation rules and fraud heuristics."""

from datetime import datetime, timedelta

from src.fraud_detector import (
    check_missing_fields,
    check_claim_amount,
    check_incident_date,
    check_policy_number_format,
    check_multiple_amounts,
    check_multiple_dates,
    check_old_incident,
    run_fraud_heuristics,
    validate_claim,
)


def make_claim(**overrides):
    """A clean baseline claim that should pass every check."""
    claim = {
        "claimant_name": "Jane Doe",
        "policy_number": "POL-483920",
        "claim_amount": 1240.55,
        "incident_date": (datetime.today() - timedelta(days=45)).strftime("%Y-%m-%d"),
        "claim_type": "auto",
        "description": (
            "Rear bumper damage from a low-speed collision in a parking lot. "
            "Photos and repair estimate from certified shop attached."
        ),
    }
    claim.update(overrides)
    return claim


# ── check_missing_fields ──────────────────────────────────────────────────

def test_no_missing_fields_on_clean_claim():
    assert check_missing_fields(make_claim()) == []

def test_none_value_is_missing():
    assert "claim_amount" in check_missing_fields(make_claim(claim_amount=None))

def test_whitespace_string_is_missing():
    assert "claimant_name" in check_missing_fields(make_claim(claimant_name="   "))


# ── check_claim_amount ────────────────────────────────────────────────────

def test_normal_amount_passes():
    assert check_claim_amount(1240.55) == []

def test_negative_amount_is_inconsistent():
    assert len(check_claim_amount(-50.0)) == 1

def test_zero_amount_is_inconsistent():
    assert len(check_claim_amount(0)) == 1

def test_extreme_amount_is_inconsistent():
    assert any("abnormally high" in msg for msg in check_claim_amount(750_000))

def test_none_amount_is_skipped():
    assert check_claim_amount(None) == []


# ── check_incident_date ───────────────────────────────────────────────────

def test_iso_date_parses():
    assert check_incident_date("2026-05-01") == []

def test_garbage_date_is_inconsistent():
    assert len(check_incident_date("not-a-date-at-all")) == 1

def test_empty_date_is_skipped():
    assert check_incident_date(None) == []


# ── check_policy_number_format ────────────────────────────────────────────

def test_valid_policy_number_passes():
    assert check_policy_number_format("POL-483920") == []

def test_short_policy_number_flagged():
    assert len(check_policy_number_format("A1")) == 1

def test_placeholder_policy_number_flagged():
    assert any("placeholder" in msg for msg in check_policy_number_format("N/A"))


# ── cross-document checks ─────────────────────────────────────────────────

def test_conflicting_amounts_flagged():
    raw = "Total due: $150.00 ... adjusted total: $9,800.00"
    assert len(check_multiple_amounts(raw, 9800.0)) == 1

def test_consistent_amounts_pass():
    raw = "Estimate: $1,200.00, final invoice $1,240.55"
    assert check_multiple_amounts(raw, 1240.55) == []

def test_many_distinct_dates_flagged():
    raw = " ".join(f"2026-0{m}-1{m}" for m in range(1, 8))
    assert len(check_multiple_dates(raw)) == 1


# ── date-age heuristics ───────────────────────────────────────────────────

def test_old_incident_flagged():
    old = (datetime.today() - timedelta(days=900)).strftime("%Y-%m-%d")
    assert any("late filing" in msg for msg in check_old_incident(old))

def test_recent_incident_not_flagged():
    assert check_old_incident(make_claim()["incident_date"]) == []


# ── run_fraud_heuristics ──────────────────────────────────────────────────

def test_clean_claim_has_no_flags():
    assert run_fraud_heuristics(make_claim(), raw_text="") == []

def test_high_value_claim_flagged():
    flags = run_fraud_heuristics(make_claim(claim_amount=25_500.75), raw_text="")
    assert any("High-value claim" in f for f in flags)

def test_round_number_flagged():
    flags = run_fraud_heuristics(make_claim(claim_amount=8_000.0), raw_text="")
    assert any("round number" in f for f in flags)

def test_future_incident_date_flagged():
    future = (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    flags = run_fraud_heuristics(make_claim(incident_date=future), raw_text="")
    assert any("future" in f for f in flags)

def test_suspicious_phrase_flagged():
    desc = (
        "Item was purchased cash only from a private seller, no receipt was "
        "provided at the time of the transaction."
    )
    flags = run_fraud_heuristics(make_claim(description=desc), raw_text="")
    assert any("Suspicious phrase" in f for f in flags)

def test_short_description_flagged():
    flags = run_fraud_heuristics(make_claim(description="Broken."), raw_text="")
    assert any("very short" in f for f in flags)


# ── validate_claim (integration) ──────────────────────────────────────────

def test_validate_claim_returns_expected_shape():
    report = validate_claim(make_claim(), raw_text="")
    assert set(report.keys()) == {"missing_fields", "inconsistencies", "flags"}
    assert report["missing_fields"] == []
    assert report["inconsistencies"] == []
    assert report["flags"] == []

def test_validate_claim_catches_multiple_problems():
    bad = make_claim(claimant_name=None, claim_amount=-10.0, policy_number="N/A")
    report = validate_claim(bad, raw_text="")
    assert "claimant_name" in report["missing_fields"]
    assert len(report["inconsistencies"]) >= 2
    assert len(report["flags"]) >= 1
