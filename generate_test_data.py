"""
generate_test_data.py
─────────────────────
Generates 200 synthetic insurance claim PDFs modelled on the real Cigna Medical
Claim Form and HCFA-1500 form layouts.

Distribution (200 total):
  80  CLEAN        – all fields present, valid data, no red flags
  50  FRAUDULENT   – suspicious patterns, inflated amounts, red-flag phrases
  40  INCOMPLETE   – one or more critical fields missing
  30  EDGE_CASE    – technically valid but unusual (future-adjacent dates,
                     very high amounts, conflicting data, round numbers)

Output: sample_claims/  (one PDF per claim)
        data/claim_manifest.json  (ground-truth labels for every file)
"""

import os
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── Output paths ──────────────────────────────────────────────────────────────
OUT_DIR  = Path("sample_claims")
DATA_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

random.seed(42)

# ── Static data pools ─────────────────────────────────────────────────────────
FIRST_NAMES = [
    "James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
    "David","Barbara","William","Elizabeth","Richard","Susan","Joseph","Jessica",
    "Thomas","Sarah","Charles","Karen","Christopher","Lisa","Daniel","Nancy",
    "Matthew","Betty","Anthony","Margaret","Mark","Sandra","Donald","Ashley",
    "Steven","Dorothy","Paul","Kimberly","Andrew","Emily","Kenneth","Donna",
    "Joshua","Michelle","George","Carol","Kevin","Amanda","Brian","Melissa",
    "Edward","Deborah","Ronald","Stephanie","Timothy","Rebecca","Jason","Sharon",
    "Jeffrey","Laura","Ryan","Cynthia","Jacob","Kathleen","Gary","Amy",
    "Nicholas","Angela","Eric","Shirley","Jonathan","Anna","Stephen","Brenda",
    "Larry","Pamela","Justin","Emma","Scott","Nicole","Brandon","Helen",
    "Benjamin","Samantha","Samuel","Katherine","Raymond","Christine","Gregory",
    "Debra","Frank","Rachel","Alexander","Carolyn","Patrick","Janet",
]
LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
    "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
    "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker",
    "Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
    "Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell",
    "Carter","Roberts","Gomez","Phillips","Evans","Turner","Diaz","Parker",
    "Cruz","Edwards","Collins","Reyes","Stewart","Morris","Morales","Murphy",
    "Cook","Rogers","Gutierrez","Ortiz","Morgan","Cooper","Peterson","Bailey",
    "Reed","Kelly","Howard","Ramos","Kim","Cox","Ward","Richardson","Watson",
    "Brooks","Chavez","Wood","James","Bennett","Gray","Mendoza","Ruiz",
    "Hughes","Price","Alvarez","Castillo","Sanders","Patel","Myers","Long",
]
EMPLOYERS = [
    "Acme Manufacturing Co.","Sunrise Healthcare Group","Blue Ridge Tech Inc.",
    "Evergreen Logistics LLC","Summit Financial Services","Pacific Rim Exports",
    "Lakewood School District","Metro Transit Authority","Pinnacle Consulting",
    "Golden Gate Hospitality","Redwood Software Solutions","Valley Medical Center",
    "Horizon Energy Partners","Coastal Retail Group","NorthStar Engineering",
    "Midwest Agricultural Co.","Urban Development Corp","Skyline Construction",
    "Riverside Community College","Clearwater Pharmaceuticals",
]
STATES = [
    ("AL","Alabama"),("AK","Alaska"),("AZ","Arizona"),("AR","Arkansas"),
    ("CA","California"),("CO","Colorado"),("CT","Connecticut"),("FL","Florida"),
    ("GA","Georgia"),("IL","Illinois"),("IN","Indiana"),("IA","Iowa"),
    ("KS","Kansas"),("KY","Kentucky"),("LA","Louisiana"),("ME","Maine"),
    ("MD","Maryland"),("MA","Massachusetts"),("MI","Michigan"),("MN","Minnesota"),
    ("MO","Missouri"),("NE","Nebraska"),("NV","Nevada"),("NJ","New Jersey"),
    ("NM","New Mexico"),("NY","New York"),("NC","North Carolina"),("OH","Ohio"),
    ("OK","Oklahoma"),("OR","Oregon"),("PA","Pennsylvania"),("RI","Rhode Island"),
    ("SC","South Carolina"),("TN","Tennessee"),("TX","Texas"),("UT","Utah"),
    ("VA","Virginia"),("WA","Washington"),("WI","Wisconsin"),
]
CITIES = [
    "Springfield","Riverside","Fairview","Georgetown","Franklin","Greenville",
    "Bristol","Clinton","Madison","Salem","Auburn","Manchester","Oakland",
    "Dayton","Lexington","Raleigh","Columbus","Phoenix","Denver","Portland",
    "Seattle","Nashville","Memphis","Louisville","Baltimore","Boston",
    "Atlanta","Dallas","Houston","San Antonio","San Diego","Philadelphia",
]
DIAGNOSES = [
    ("Z00.00", "Routine general medical examination"),
    ("J06.9",  "Acute upper respiratory infection, unspecified"),
    ("M54.5",  "Low back pain"),
    ("I10",    "Essential (primary) hypertension"),
    ("E11.9",  "Type 2 diabetes mellitus without complications"),
    ("J18.9",  "Pneumonia, unspecified organism"),
    ("K21.0",  "Gastro-esophageal reflux disease with esophagitis"),
    ("F32.1",  "Major depressive disorder, single episode, moderate"),
    ("M79.3",  "Panniculitis, unspecified"),
    ("S93.401","Sprain of unspecified ligament of right ankle"),
    ("R51",    "Headache"),
    ("N39.0",  "Urinary tract infection, site not specified"),
    ("L30.9",  "Dermatitis, unspecified"),
    ("J45.20", "Mild intermittent asthma, uncomplicated"),
    ("G43.909","Migraine, unspecified, not intractable, without status migrainosus"),
    ("R10.9",  "Unspecified abdominal pain"),
    ("H66.90", "Otitis media, unspecified, unspecified ear"),
    ("M25.511","Pain in right shoulder"),
    ("Z23",    "Encounter for immunization"),
    ("K57.30", "Diverticulosis of large intestine without perforation"),
]
PROCEDURES = [
    ("99213","Office or other outpatient visit, established patient"),
    ("99214","Office or other outpatient visit, detailed"),
    ("99203","Office or other outpatient visit, new patient"),
    ("99232","Subsequent hospital care, per day"),
    ("93000","Electrocardiogram, routine ECG with interpretation"),
    ("71046","Radiologic examination, chest; 2 views"),
    ("80053","Comprehensive metabolic panel"),
    ("85025","Complete (CBC), automated"),
    ("36415","Collection of venous blood by venipuncture"),
    ("90471","Immunization administration"),
    ("97110","Therapeutic exercises"),
    ("97035","Application of a modality; ultrasound"),
    ("43239","Upper gastrointestinal endoscopy"),
    ("45378","Colonoscopy, flexible; diagnostic"),
    ("27447","Total knee arthroplasty"),
]
PHYSICIANS = [
    ("Dr. Sarah Pemberton, MD",  "1234567890", "Cardiology"),
    ("Dr. James Whitmore, DO",   "2345678901", "Family Medicine"),
    ("Dr. Elena Vasquez, MD",    "3456789012", "Internal Medicine"),
    ("Dr. Robert Tanaka, MD",    "4567890123", "Orthopedics"),
    ("Dr. Angela Foster, NP",    "5678901234", "Primary Care"),
    ("Dr. Michael Okonkwo, MD",  "6789012345", "Emergency Medicine"),
    ("Dr. Linda Krishnamurthy, MD","7890123456","Neurology"),
    ("Dr. David Callahan, MD",   "8901234567", "Gastroenterology"),
    ("Dr. Patricia Huang, MD",   "9012345678", "Pulmonology"),
    ("Dr. Thomas Eriksson, DO",  "0123456789", "Sports Medicine"),
]
FACILITIES = [
    ("General Hospital",        "100 Medical Center Dr"),
    ("Community Health Clinic", "250 Wellness Ave"),
    ("St. Mary's Medical Center","500 Hospital Blvd"),
    ("University Hospital",     "1 University Health Way"),
    ("Regional Urgent Care",    "333 Quick Care Ln"),
    ("Sunrise Outpatient Center","77 Sunrise Pkwy"),
    ("Mountain View Clinic",    "490 Ridge Rd"),
    ("Bayside Medical Group",   "12 Harbor View Dr"),
]
FRAUD_PHRASES = [
    "Please process urgently and issue payment via wire transfer.",
    "Cash payment preferred. No receipts are available for these services.",
    "Do not contact my employer regarding this claim.",
    "Payment should be directed to a third-party account.",
    "Services were rendered off-site; no facility records exist.",
    "Diagnosis was verbal only; no written documentation available.",
    "Please expedite — Western Union transfer requested.",
]

# ── Helper generators ─────────────────────────────────────────────────────────

def rnd_name():
    return f"{random.choice(LAST_NAMES)}, {random.choice(FIRST_NAMES)}"

def rnd_name_natural():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def rnd_policy():
    prefix = random.choice(["POL", "INS", "CGN", "HMO", "PPO"])
    year   = random.randint(2018, 2024)
    num    = random.randint(10000, 99999)
    return f"{prefix}-{year}-{num}"

def rnd_cigna_id():
    return "U" + "".join(random.choices(string.digits, k=9))

def rnd_date(start_days_ago=730, end_days_ago=1):
    delta = random.randint(end_days_ago, start_days_ago)
    return datetime.today() - timedelta(days=delta)

def rnd_future_date():
    delta = random.randint(10, 180)
    return datetime.today() + timedelta(days=delta)

def rnd_amount(lo, hi, round_to=None):
    amt = random.uniform(lo, hi)
    if round_to:
        amt = round(amt / round_to) * round_to
    return round(amt, 2)

def rnd_address():
    num   = random.randint(10, 9999)
    streets = ["Main St","Oak Ave","Maple Dr","Cedar Ln","Elm St","Park Blvd",
               "Lake Rd","River Way","Hill Ct","Forest Dr","Sunset Blvd","Valley Rd"]
    city  = random.choice(CITIES)
    state = random.choice(STATES)[0]
    zip_  = "".join(random.choices(string.digits, k=5))
    return f"{num} {random.choice(streets)}", city, state, zip_

def rnd_phone():
    area = random.randint(200, 999)
    mid  = random.randint(200, 999)
    end  = random.randint(1000, 9999)
    return f"({area}) {mid}-{end}"

def rnd_ssn():
    return f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"

def rnd_diagnosis():
    return random.choice(DIAGNOSES)

def rnd_procedure():
    return random.choice(PROCEDURES)

def rnd_physician():
    return random.choice(PHYSICIANS)

def rnd_facility():
    return random.choice(FACILITIES)

# ── PDF builders ──────────────────────────────────────────────────────────────

styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("title", fontSize=14, fontName="Helvetica-Bold",
                              alignment=TA_CENTER, spaceAfter=4)
HEAD_STYLE  = ParagraphStyle("head",  fontSize=10, fontName="Helvetica-Bold",
                              alignment=TA_CENTER, spaceAfter=2,
                              backColor=colors.HexColor("#d0d8e8"))
LABEL_STYLE = ParagraphStyle("label", fontSize=7,  fontName="Helvetica-Bold")
VALUE_STYLE = ParagraphStyle("value", fontSize=8,  fontName="Helvetica")
NOTE_STYLE  = ParagraphStyle("note",  fontSize=7,  fontName="Helvetica",
                              textColor=colors.gray)
WARN_STYLE  = ParagraphStyle("warn",  fontSize=7,  fontName="Helvetica-Bold",
                              textColor=colors.red)

def _tbl(data, col_widths, style_cmds=None):
    base = [
        ("FONTSIZE",    (0,0),(-1,-1), 8),
        ("FONTNAME",    (0,0),(-1,-1), "Helvetica"),
        ("GRID",        (0,0),(-1,-1), 0.4, colors.HexColor("#aaaaaa")),
        ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
    ]
    if style_cmds:
        base += style_cmds
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(base))
    return t

def _lv(label, value):
    """Label + value pair as two stacked paragraphs."""
    return [Paragraph(label, LABEL_STYLE), Paragraph(str(value) if value else "", VALUE_STYLE)]


def build_cigna_pdf(path: Path, fields: dict):
    """Render a Cigna-style Medical Claim Form."""
    doc = SimpleDocTemplate(str(path), pagesize=letter,
                            leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    W = 7.5 * inch
    story = []

    # Header
    story.append(Paragraph("Medical Claim Form", TITLE_STYLE))
    story.append(Paragraph(
        "<i>Insured and/or Administered by Connecticut General Life Insurance Company · "
        "Cigna Health and Life Insurance Company · Cigna HealthCare</i>", NOTE_STYLE))
    story.append(Paragraph(
        "This form can be used with all medical plans. "
        "It is not intended for Dental or Pharmacy claims.", NOTE_STYLE))
    story.append(Spacer(1, 6))

    # ── Section 1: Primary Customer ──────────────────────────────────────────
    story.append(Paragraph("PRIMARY CUSTOMER INFORMATION", HEAD_STYLE))
    row1 = _tbl([
        [*_lv("A1. PRIMARY CUSTOMER'S NAME (Last, First, M.I.)", fields.get("name","")),
         *_lv("A2. GENDER", fields.get("gender","M")),
         *_lv("B. DATE OF BIRTH", fields.get("dob",""))],
    ], [W*0.5, W*0.5, W*0.12, W*0.12, W*0.13, W*0.13])
    story.append(row1)

    addr, city, state, zip_ = fields.get("address", ("", "", "", ""))
    row2 = _tbl([
        [*_lv("C. PRIMARY CUSTOMER'S MAILING ADDRESS", addr),
         *_lv("CITY", city), *_lv("STATE", state), *_lv("ZIP", zip_),
         *_lv("DAYTIME TELEPHONE", fields.get("phone",""))],
    ], [W*0.28, W*0.28, W*0.14, W*0.14, W*0.08, W*0.08, W*0.14, W*0.14])
    story.append(row2)

    row3 = _tbl([
        [*_lv("D. CIGNA ID NUMBER", fields.get("cigna_id","")),
         *_lv("E. ACCOUNT NO.", fields.get("policy_number","")),
         *_lv("F. EMPLOYER NAME", fields.get("employer","")),
         *_lv("G. STATUS", fields.get("status","Employed"))],
    ], [W*0.22, W*0.22, W*0.22, W*0.22, W*0.17, W*0.17, W*0.1, W*0.1])  # fixed to 8 cols
    story.append(row3)
    story.append(Spacer(1, 5))

    # ── Section 2: Accident/Occupational ────────────────────────────────────
    story.append(Paragraph("ACCIDENT / OCCUPATIONAL CLAIM INFORMATION", HEAD_STYLE))
    inc_date = fields.get("incident_date", "")
    inc_date_str = inc_date.strftime("%m/%d/%Y") if isinstance(inc_date, datetime) else str(inc_date)
    row4 = _tbl([
        [*_lv("A. ACCIDENT DUE TO EMPLOYMENT?", fields.get("employment_accident","No")),
         *_lv("B. AUTO ACCIDENT?", fields.get("auto_accident","No")),
         *_lv("C. DESCRIPTION OF INCIDENT", fields.get("description","")),
         *_lv("D. DATE OF ACCIDENT / BEGINNING OF ILLNESS", inc_date_str)],
    ], [W*0.14, W*0.14, W*0.12, W*0.12, W*0.34, W*0.34, W*0.15, W*0.15])
    story.append(row4)
    story.append(Spacer(1, 5))

    # ── Section 3: Services ──────────────────────────────────────────────────
    story.append(Paragraph("SERVICES / PROCEDURES", HEAD_STYLE))
    svc_header = ["DATE OF SERVICE", "PLACE", "TYPE", "CPT/HCPCS CODE",
                  "DESCRIPTION", "DIAGNOSIS CODE", "CHARGES"]
    svc_rows   = [svc_header]
    for svc in fields.get("services", []):
        svc_rows.append([
            svc.get("date",""), svc.get("place","11"), svc.get("type","1"),
            svc.get("cpt",""), svc.get("description",""), svc.get("dx",""),
            f"${svc.get('charge',0):,.2f}",
        ])
    svc_tbl = _tbl(svc_rows,
                   [W*0.13, W*0.07, W*0.06, W*0.1, W*0.35, W*0.1, W*0.09],
                   style_cmds=[
                       ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#d0d8e8")),
                       ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                   ])
    story.append(svc_tbl)
    story.append(Spacer(1, 5))

    # ── Totals ────────────────────────────────────────────────────────────────
    total    = fields.get("claim_amount") or 0
    paid     = fields.get("amount_paid") or 0
    balance  = round(total - paid, 2)
    tot_disp = f"${total:,.2f}" if fields.get("claim_amount") is not None else "NOT PROVIDED"
    tot_tbl = _tbl([
        ["28. TOTAL CHARGE", "29. AMOUNT PAID", "30. BALANCE DUE"],
        [tot_disp, f"${paid:,.2f}", f"${balance:,.2f}"],
    ], [W/3, W/3, W/3],
    style_cmds=[
        ("BACKGROUND",  (0,0),(-1,0), colors.HexColor("#d0d8e8")),
        ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTNAME",    (0,1),(-1,1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,1),(-1,1), 10),
        ("ALIGN",       (0,0),(-1,-1), "CENTER"),
    ])
    story.append(tot_tbl)
    story.append(Spacer(1, 5))

    # ── Physician / Facility ──────────────────────────────────────────────────
    story.append(Paragraph("PHYSICIAN / SUPPLIER INFORMATION", HEAD_STYLE))
    phys_name, phys_npi, phys_spec = fields.get("physician", ("", "", ""))
    fac_name,  fac_addr            = fields.get("facility",  ("", ""))
    phys_tbl = _tbl([
        [*_lv("31. SIGNATURE / NAME OF PHYSICIAN", phys_name),
         *_lv("SPECIALTY", phys_spec),
         *_lv("NPI", phys_npi),
         *_lv("32. FACILITY NAME", fac_name),
         *_lv("FACILITY ADDRESS", fac_addr)],
    ], [W*0.22, W*0.22, W*0.1, W*0.1, W*0.1, W*0.1, W*0.13, W*0.13])
    story.append(phys_tbl)
    story.append(Spacer(1, 5))

    # ── Certification & Fraud warnings ───────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.gray))
    story.append(Paragraph(
        "<b>CERTIFICATION:</b> Any person who knowingly and with intent to defraud any insurance "
        "company or other person files a statement of claim containing any materially false "
        "information commits a fraudulent insurance act, which is a crime.", NOTE_STYLE))

    # Inject fraud notes if present
    if fields.get("fraud_note"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>ADDITIONAL NOTES:</b> {fields['fraud_note']}", WARN_STYLE))

    story.append(Spacer(1, 6))
    sig_tbl = _tbl([
        [*_lv("PRIMARY CUSTOMER'S SIGNATURE", fields.get("signature","")),
         *_lv("DATE", fields.get("signature_date",""))],
    ], [W*0.7, W*0.7, W*0.15, W*0.15])
    story.append(sig_tbl)
    story.append(Spacer(1, 4))
    story.append(Paragraph("591692c Rev. 11/2023", NOTE_STYLE))

    doc.build(story)


def build_hcfa_pdf(path: Path, fields: dict):
    """Render an HCFA-1500 style claim form."""
    doc = SimpleDocTemplate(str(path), pagesize=letter,
                            leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    W = 7.5 * inch
    story = []

    story.append(Paragraph("HEALTH INSURANCE CLAIM FORM", TITLE_STYLE))
    story.append(Paragraph("HCFA-1500 · APPROVED OMB-0938-0008", NOTE_STYLE))
    story.append(Spacer(1, 5))

    # Item 1 — program type
    prog = fields.get("program_type", "OTHER")
    prog_tbl = _tbl([[
        f"☐ MEDICARE", f"☐ MEDICAID", f"☐ CHAMPUS", f"☐ CHAMPVA",
        f"☐ GROUP HEALTH", f"☐ FECA BLK LUNG",
        f"{'☑' if prog=='OTHER' else '☐'} OTHER",
    ]], [W/7]*7)
    story.append(prog_tbl)
    story.append(Spacer(1, 4))

    # Patient & Insured block
    story.append(Paragraph("PATIENT AND INSURED INFORMATION", HEAD_STYLE))
    inc_date = fields.get("incident_date","")
    inc_str  = inc_date.strftime("%m/%d/%Y") if isinstance(inc_date, datetime) else str(inc_date)
    dob_str  = fields.get("dob_str","")
    pi_tbl = _tbl([
        [*_lv("1a. INSURED'S I.D. NUMBER", fields.get("cigna_id","")),
         *_lv("2. PATIENT'S NAME (Last, First, MI)", fields.get("name","")),
         *_lv("3. PATIENT'S BIRTH DATE", dob_str),
         *_lv("4. INSURED'S NAME", fields.get("insured_name", fields.get("name","")))],
        [*_lv("5. PATIENT'S ADDRESS", fields.get("address_str","")),
         *_lv("6. PATIENT RELATIONSHIP TO INSURED", fields.get("relationship","Self")),
         *_lv("7. INSURED'S ADDRESS", fields.get("address_str","")),
         *_lv("8. PATIENT STATUS", fields.get("status","Single · Employed"))],
        [*_lv("9. OTHER INSURED'S NAME", fields.get("other_insured","")),
         *_lv("10. IS PATIENT'S CONDITION RELATED TO EMPLOYMENT?",
               fields.get("employment_accident","No")),
         *_lv("11. INSURED'S POLICY GROUP / FECA NUMBER", fields.get("policy_number","")),
         *_lv("11c. INSURANCE PLAN NAME", fields.get("plan_name","Cigna PPO"))],
    ], [W*0.22, W*0.22, W*0.22, W*0.22, W*0.07, W*0.07, W*0.07, W*0.07])
    story.append(pi_tbl)
    story.append(Spacer(1, 4))

    # Condition / Diagnosis
    story.append(Paragraph("PHYSICIAN OR SUPPLIER INFORMATION", HEAD_STYLE))
    dx_code, dx_desc = fields.get("diagnosis", ("", ""))
    dx_tbl = _tbl([
        [*_lv("14. DATE OF CURRENT ILLNESS / INJURY / PREGNANCY", inc_str),
         *_lv("17. REFERRING PHYSICIAN", fields.get("referring_physician","")),
         *_lv("21. DIAGNOSIS / NATURE OF ILLNESS OR INJURY", f"{dx_code} – {dx_desc}")],
    ], [W*0.24, W*0.24, W*0.24, W*0.24, W*0.28, W*0.28])  # 6 cols
    story.append(dx_tbl)
    story.append(Spacer(1, 4))

    # Service lines
    story.append(Paragraph("24. DATES OF SERVICE / PROCEDURES", HEAD_STYLE))
    svc_header = ["FROM", "TO", "PLACE", "TYPE", "CPT", "MODIFIER",
                  "DIAGNOSIS CODE", "$ CHARGES", "DAYS/UNITS"]
    svc_rows   = [svc_header]
    for svc in fields.get("services", []):
        svc_rows.append([
            svc.get("date",""), svc.get("date",""),
            svc.get("place","11"), svc.get("type","1"),
            svc.get("cpt",""), "",
            svc.get("dx",""), f"${svc.get('charge',0):,.2f}",
            str(svc.get("units",1)),
        ])
    svc_tbl = _tbl(svc_rows,
                   [W*0.1, W*0.1, W*0.06, W*0.06, W*0.08, W*0.07, W*0.1, W*0.1, W*0.08],  # 9 = 0.75
                   style_cmds=[
                       ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#d0d8e8")),
                       ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
                   ])
    story.append(svc_tbl)
    story.append(Spacer(1, 4))

    # Totals
    total   = fields.get("claim_amount") or 0
    paid    = fields.get("amount_paid") or 0
    balance = round(total - paid, 2)
    tot_disp = f"${total:,.2f}" if fields.get("claim_amount") is not None else "NOT PROVIDED"
    tot_tbl = _tbl([
        ["28. TOTAL CHARGE", "29. AMOUNT PAID", "30. BALANCE DUE"],
        [tot_disp, f"${paid:,.2f}", f"${balance:,.2f}"],
    ], [W/3, W/3, W/3],
    style_cmds=[
        ("BACKGROUND", (0,0),(-1,0), colors.HexColor("#d0d8e8")),
        ("FONTNAME",   (0,0),(-1,1), "Helvetica-Bold"),
        ("ALIGN",      (0,0),(-1,-1),"CENTER"),
        ("FONTSIZE",   (0,1),(-1,1), 10),
    ])
    story.append(tot_tbl)
    story.append(Spacer(1, 4))

    # Physician sign-off
    phys_name, phys_npi, phys_spec = fields.get("physician",("","",""))
    fac_name,  fac_addr            = fields.get("facility", ("",""))
    sig_str = fields.get("signature_date","")
    sign_tbl = _tbl([
        [*_lv("25. FEDERAL TAX I.D. (EIN)", fields.get("tax_id","")),
         *_lv("26. PATIENT ACCOUNT NO.", fields.get("account_no","")),
         *_lv("27. ACCEPT ASSIGNMENT?", "YES"),
         *_lv("31. PHYSICIAN SIGNATURE / DATE", f"{phys_name} / {sig_str}"),
         *_lv("32. FACILITY", f"{fac_name}, {fac_addr}"),
         *_lv("33. BILLING PROVIDER / NPI", f"{phys_name}\nNPI: {phys_npi}")],
    ], [W*0.14, W*0.14, W*0.12, W*0.12, W*0.08, W*0.08, W*0.17, W*0.17, W*0.17, W*0.17, W*0.17, W*0.17])
    story.append(sign_tbl)

    if fields.get("fraud_note"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>NOTES:</b> {fields['fraud_note']}", WARN_STYLE))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "NOTICE: Any person who knowingly files a statement of claim containing any "
        "misrepresentation or false information may be guilty of a criminal act.", NOTE_STYLE))
    story.append(Paragraph("FORM HCFA-1500 (12-90) · APPROVED OMB-0938-0008", NOTE_STYLE))

    doc.build(story)


# ── Claim field factories ─────────────────────────────────────────────────────

def _base_fields(override_date=None, override_amount=None, missing=None):
    """Build a realistic complete set of fields."""
    missing = missing or []
    dob    = rnd_date(start_days_ago=365*65, end_days_ago=365*18)
    inc_dt = override_date if override_date else rnd_date(730, 30)
    amount = override_amount if override_amount else rnd_amount(150, 8000)
    addr   = rnd_address()
    phys   = rnd_physician()
    fac    = rnd_facility()
    dx     = rnd_diagnosis()
    procs  = random.sample(PROCEDURES, k=random.randint(1, 3))
    sig_dt = (inc_dt + timedelta(days=random.randint(1, 30))).strftime("%m/%d/%Y") \
             if isinstance(inc_dt, datetime) else ""

    # Build service lines (use 0 if amount missing — incomplete claim scenario)
    remaining = amount if amount is not None else 0.0
    services  = []
    for i, proc in enumerate(procs):
        charge = round(remaining / (len(procs) - i), 2)
        remaining -= charge
        svc_date = inc_dt if isinstance(inc_dt, datetime) else datetime.today()
        services.append({
            "date":        svc_date.strftime("%m/%d/%Y"),
            "place":       "11",
            "type":        "1",
            "cpt":         proc[0],
            "description": proc[1],
            "dx":          dx[0],
            "charge":      charge,
            "units":       1,
        })

    fields = {
        "name":               None if "name" in missing else rnd_name(),
        "gender":             random.choice(["M","F"]),
        "dob":                dob.strftime("%m/%d/%Y"),
        "dob_str":            dob.strftime("%m/%d/%Y"),
        "address":            addr,
        "address_str":        f"{addr[0]}, {addr[1]}, {addr[2]} {addr[3]}",
        "phone":              rnd_phone(),
        "cigna_id":           None if "cigna_id" in missing else rnd_cigna_id(),
        "policy_number":      None if "policy_number" in missing else rnd_policy(),
        "employer":           random.choice(EMPLOYERS),
        "status":             random.choice(["Employed","Single · Employed","Married · Employed"]),
        "plan_name":          random.choice(["Cigna PPO","Cigna HMO","Cigna HDHP","Open Access Plus"]),
        "incident_date":      None if "incident_date" in missing else inc_dt,
        "description":        None if "description" in missing else _incident_description(dx),
        "services":           services,
        "claim_amount":       None if "claim_amount" in missing else amount,
        "amount_paid":        0,
        "physician":          phys,
        "facility":           fac,
        "diagnosis":          dx,
        "tax_id":             "".join(random.choices(string.digits, k=9)),
        "account_no":         "".join(random.choices(string.digits, k=8)),
        "referring_physician":random.choice(PHYSICIANS)[0],
        "employment_accident":"No",
        "auto_accident":      "No",
        "other_insured":      "",
        "relationship":       "Self",
        "program_type":       "OTHER",
        "insured_name":       None,
        "signature":          rnd_name_natural(),
        "signature_date":     sig_dt,
        "fraud_note":         None,
    }
    return fields


def _incident_description(dx):
    """Generate a realistic description tied to the diagnosis."""
    templates = [
        f"Patient presented with {dx[1].lower()}. Evaluation and treatment provided as documented.",
        f"Routine visit for ongoing management of {dx[1].lower()}.",
        f"Emergency presentation. Chief complaint: {dx[1].lower()}. Treated per clinical protocol.",
        f"Follow-up consultation for {dx[1].lower()}. Labs ordered and reviewed.",
        f"Patient referred by PCP for specialist evaluation of {dx[1].lower()}.",
        f"Outpatient procedure performed for {dx[1].lower()}. No complications noted.",
    ]
    return random.choice(templates)


# ── Scenario generators ───────────────────────────────────────────────────────

def make_clean(idx):
    """Fully valid claim — should ACCEPT."""
    f = _base_fields()
    return f, "ACCEPT", "clean"


def make_fraudulent(idx):
    """Fraud indicators — should FLAG or REJECT."""
    subtype = idx % 7
    f = _base_fields()

    if subtype == 0:
        # Massively inflated amount
        f["claim_amount"] = rnd_amount(50000, 250000, round_to=1000)
        for s in f["services"]: s["charge"] = f["claim_amount"] / len(f["services"])
        f["fraud_note"] = random.choice(FRAUD_PHRASES)
        label = "fraud_inflated_amount"

    elif subtype == 1:
        # Round-number amount + wire transfer note
        f["claim_amount"] = float(random.choice([10000,15000,20000,25000,50000,75000,100000]))
        f["fraud_note"] = "Please issue payment via wire transfer immediately."
        label = "fraud_wire_transfer"

    elif subtype == 2:
        # Duplicate services (same CPT billed 4 times)
        base_svc = f["services"][0].copy()
        charge_each = round(f["claim_amount"] / 4, 2)
        f["services"] = [{**base_svc, "charge": charge_each} for _ in range(4)]
        f["fraud_note"] = "Multiple sessions — no appointment records available."
        label = "fraud_duplicate_services"

    elif subtype == 3:
        # Future incident date
        f["incident_date"] = rnd_future_date()
        f["services"][0]["date"] = f["incident_date"].strftime("%m/%d/%Y")
        label = "fraud_future_date"

    elif subtype == 4:
        # No receipt / cash only
        f["fraud_note"] = "Cash only. No receipts. Do not contact employer."
        f["claim_amount"] = rnd_amount(8000, 45000, round_to=500)
        label = "fraud_no_receipts"

    elif subtype == 5:
        # Policy number is a placeholder
        f["policy_number"] = random.choice(["N/A","NONE","UNKNOWN","TBD","000000"])
        f["fraud_note"] = random.choice(FRAUD_PHRASES)
        label = "fraud_invalid_policy"

    else:
        # Conflicting amounts in description
        high = rnd_amount(20000, 80000)
        low  = rnd_amount(500, 2000)
        f["description"] = (
            f"Patient treated for {f['diagnosis'][1].lower()}. "
            f"Estimate provided was ${low:,.2f}. Final invoice submitted for ${high:,.2f}. "
            f"Difference attributed to additional undocumented procedures."
        )
        f["claim_amount"] = high
        label = "fraud_conflicting_amounts"

    return f, "FLAG", label


def make_incomplete(idx):
    """Missing critical fields — should REJECT."""
    combos = [
        ["name"],
        ["policy_number"],
        ["claim_amount"],
        ["name", "policy_number"],
        ["incident_date"],
        ["name", "claim_amount"],
        ["policy_number", "incident_date"],
    ]
    missing = combos[idx % len(combos)]
    f = _base_fields(missing=missing)
    return f, "REJECT", f"incomplete_missing_{'_'.join(missing)}"


def make_edge_case(idx):
    """Unusual but potentially valid — should FLAG."""
    subtype = idx % 6
    f = _base_fields()

    if subtype == 0:
        # Very high but not fraudulent (e.g. surgery)
        f["claim_amount"] = rnd_amount(12000, 49999)
        f["description"] = "Major surgical procedure performed under general anaesthesia. All documentation on file."
        label = "edge_high_value"

    elif subtype == 1:
        # Claim filed very recently after incident (same day)
        today = datetime.today() - timedelta(days=1)
        f["incident_date"] = today
        f["services"][0]["date"] = today.strftime("%m/%d/%Y")
        label = "edge_same_day_filing"

    elif subtype == 2:
        # Very old incident date (>1 year ago)
        f["incident_date"] = datetime.today() - timedelta(days=random.randint(400, 700))
        label = "edge_old_incident"

    elif subtype == 3:
        # Multiple diagnoses in description, single procedure
        dx2 = rnd_diagnosis()
        f["description"] += f" Secondary diagnosis noted: {dx2[1]}."
        f["diagnosis"] = (f["diagnosis"][0] + ", " + dx2[0],
                          f["diagnosis"][1] + " / " + dx2[1])
        label = "edge_multiple_diagnoses"

    elif subtype == 4:
        # Zero prior payment recorded on expensive claim
        f["claim_amount"] = rnd_amount(5000, 20000)
        f["amount_paid"] = 0
        f["description"] += " Patient states previous insurer denied claim without explanation."
        label = "edge_denied_prior"

    else:
        # Suspiciously round claim amount
        f["claim_amount"] = float(random.choice([1000, 2000, 3000, 5000, 7500]))
        label = "edge_round_amount"

    return f, "FLAG", label


# ── Main generation loop ───────────────────────────────────────────────────────

def generate_all():
    manifest = []
    counter  = 1

    # Alternate form type to mix both templates
    def form_type(n): return "cigna" if n % 2 == 0 else "hcfa"

    batches = [
        (80, "CLEAN",      make_clean,      "clean"),
        (50, "FRAUDULENT", make_fraudulent, "fraud"),
        (40, "INCOMPLETE", make_incomplete, "incomplete"),
        (30, "EDGE_CASE",  make_edge_case,  "edge"),
    ]

    for count, category, factory, prefix in batches:
        print(f"\nGenerating {count} {category} claims...")
        for i in range(count):
            fields, expected_decision, subtype = factory(i)
            ft       = form_type(counter)
            filename = f"{prefix}_{counter:03d}_{ft}.pdf"
            fpath    = OUT_DIR / filename

            try:
                if ft == "cigna":
                    build_cigna_pdf(fpath, fields)
                else:
                    build_hcfa_pdf(fpath, fields)

                inc = fields.get("incident_date")
                manifest.append({
                    "file_name":         filename,
                    "form_type":         ft,
                    "category":          category,
                    "subtype":           subtype,
                    "expected_decision": expected_decision,
                    "ground_truth": {
                        "claimant_name":  fields.get("name"),
                        "policy_number":  fields.get("policy_number"),
                        "claim_amount":   fields.get("claim_amount"),
                        "incident_date":  inc.strftime("%Y-%m-%d") if isinstance(inc, datetime) else inc,
                        "claim_type":     "Health",
                        "has_fraud_note": bool(fields.get("fraud_note")),
                    },
                })
                if counter % 20 == 0:
                    print(f"  [{counter}] {filename}")
                counter += 1

            except Exception as e:
                print(f"  ERROR generating {filename}: {e}")
                counter += 1

    # Save manifest
    manifest_path = DATA_DIR / "claim_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(f"\n{'='*55}")
    print(f"  Generated {len(manifest)} PDFs → {OUT_DIR}/")
    print(f"  Manifest  → {manifest_path}")
    print(f"  Distribution:")
    for cat in ["CLEAN","FRAUDULENT","INCOMPLETE","EDGE_CASE"]:
        n = sum(1 for m in manifest if m["category"] == cat)
        print(f"    {cat:<12} {n:>3} claims")
    print(f"{'='*55}")


if __name__ == "__main__":
    generate_all()