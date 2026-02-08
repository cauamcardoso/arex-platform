"""
Build Institutions Database for AI Readiness Atlas
Pulls real data from:
1. National Student Clearinghouse HSI list (Excel)
2. Urban Institute Education Data API (IPEDS data)
3. Known CAHSI member list (compiled from public sources)

Usage:
    python3 scripts/build_institutions.py
"""

import json
import time
import sys
import os
from pathlib import Path
import openpyxl
import requests

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent
HSI_EXCEL = PROJECT_ROOT / "data" / "hsi_list.xlsx"
OUTPUT_FILE = PROJECT_ROOT / "data" / "institutions" / "institutions.json"

URBAN_API_BASE = "https://educationdata.urban.org/api/v1"

# Rate limiting for API calls
API_DELAY = 0.3  # seconds between requests

# ============================================================
# CAHSI MEMBER LIST (compiled from public sources)
# Sources: cahsi.utep.edu, NSF award pages, university websites
# ============================================================

CAHSI_MEMBERS = {
    # Founding Members (2006)
    "The University of Texas at El Paso": {"role": "founding_member"},
    "Florida International University": {"role": "founding_member"},
    "New Mexico State University": {"role": "founding_member"},
    "California State University-Dominguez Hills": {"role": "founding_member"},
    "Texas A & M University-Corpus Christi": {"role": "founding_member"},
    "University of Houston-Downtown": {"role": "founding_member"},
    "University of Puerto Rico-Mayaguez": {"role": "founding_member"},

    # 4-Year Members
    "Arizona State University": {"role": "member"},
    "University of New Mexico-Main Campus": {"role": "member"},
    "University of Puerto Rico-Rio Piedras": {"role": "member"},
    "California State University-Long Beach": {"role": "member"},
    "California State University-Los Angeles": {"role": "member"},
    "California State University-Northridge": {"role": "member"},
    "San Jose State University": {"role": "member"},
    "California State University-Fullerton": {"role": "member"},
    "San Diego State University": {"role": "member"},
    "San Francisco State University": {"role": "member"},
    "University of Houston": {"role": "member"},
    "City College of New York": {"role": "member"},
    "University of Illinois Chicago": {"role": "member"},
    "Rutgers University-Newark": {"role": "member"},
    "Florida Atlantic University": {"role": "member"},
    "University of Central Florida": {"role": "member"},
    "Georgia State University": {"role": "member"},
    "University of Colorado Denver/Anschutz Medical Campus": {"role": "member"},
    "New Mexico Highlands University": {"role": "member"},
    "The University of Texas at San Antonio": {"role": "member"},
    "The University of Texas Rio Grande Valley": {"role": "member"},
    "Northeastern Illinois University": {"role": "member"},
    "Prairie View A & M University": {"role": "member"},
    "Texas Tech University": {"role": "member"},
    "University of Puerto Rico-Bayamon": {"role": "member"},
    "Inter American University of Puerto Rico-Metro": {"role": "member"},
    "Texas State University": {"role": "member"},
    "Texas A & M University-Central Texas": {"role": "member"},
    "Texas A & M University-Kingsville": {"role": "member"},
    "Kean University": {"role": "member"},
    "University of California-Merced": {"role": "member"},
    "University of California-San Diego": {"role": "member"},
    "University of California-Santa Cruz": {"role": "member"},
    "California State Polytechnic University-Pomona": {"role": "member"},
    "California State University-San Bernardino": {"role": "member"},
    "University of North Texas": {"role": "member"},
    "University of Arizona": {"role": "member"},
    "University of Puerto Rico-Humacao": {"role": "member"},
    "Polytechnic University of Puerto Rico": {"role": "member"},
    "Nova Southeastern University": {"role": "member"},
    "St Mary's University": {"role": "member"},
    "University of the Incarnate Word": {"role": "member"},
    "Colorado State University-Pueblo": {"role": "member"},

    # 2-Year Members
    "El Paso Community College": {"role": "member"},
    "Miami Dade College": {"role": "member"},
    "Pima Community College": {"role": "member"},
    "Austin Community College District": {"role": "member"},
    "Houston Community College": {"role": "member"},
    "Alamo Colleges District": {"role": "member"},
    "San Antonio College": {"role": "member"},
    "South Texas College": {"role": "member"},
    "Maricopa County Community College District": {"role": "member"},
    "Dona Ana Community College": {"role": "member"},
    "Central New Mexico Community College": {"role": "member"},
    "Collin County Community College District": {"role": "member"},
    "Del Mar College": {"role": "member"},
    "Laredo College": {"role": "member"},
    "Lone Star College System": {"role": "member"},
    "Northeast Lakeview College": {"role": "member"},
    "Northwest Vista College": {"role": "member"},
    "Palo Alto College": {"role": "member"},
    "San Jacinto Community College": {"role": "member"},
    "Southwest Texas Junior College": {"role": "member"},
    "Tarrant County College District": {"role": "member"},
    "Victoria College": {"role": "member"},
    "Broward College": {"role": "member"},
    "Hillsborough Community College": {"role": "member"},
    "Valencia College": {"role": "member"},
    "College of Southern Nevada": {"role": "member"},
    "Community College of Denver": {"role": "member"},
}

# Normalized name lookup for matching IPEDS names to CAHSI names
def normalize_name(name):
    """Normalize institution name for matching."""
    name = name.upper().strip()
    # Remove common suffixes/prefixes
    replacements = {
        "THE ": "",
        " - ": "-",
        "SAINT ": "ST ",
        "MOUNT ": "MT ",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name


def get_cahsi_info(ipeds_name):
    """Check if institution is a CAHSI member. Uses fuzzy matching."""
    ipeds_norm = normalize_name(ipeds_name)

    for cahsi_name, info in CAHSI_MEMBERS.items():
        cahsi_norm = normalize_name(cahsi_name)
        # Exact match
        if ipeds_norm == cahsi_norm:
            return info
        # Partial match (one contains the other)
        if cahsi_norm in ipeds_norm or ipeds_norm in cahsi_norm:
            return info
        # Word-level matching for tricky cases
        cahsi_words = set(cahsi_norm.split())
        ipeds_words = set(ipeds_norm.split())
        # If 80%+ of CAHSI name words appear in IPEDS name
        if len(cahsi_words) > 2:
            overlap = cahsi_words & ipeds_words
            if len(overlap) / len(cahsi_words) >= 0.7:
                return info
    return None


# ============================================================
# STATE CODE MAPPING
# ============================================================

STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
    "Puerto Rico": "PR", "Guam": "GU", "Virgin Islands": "VI",
    "American Samoa": "AS", "Northern Mariana Islands": "MP",
}

REGION_MAP = {
    "AL": "Southeast", "AK": "West", "AZ": "Southwest", "AR": "Southeast",
    "CA": "West", "CO": "Mountain", "CT": "Northeast", "DE": "Northeast",
    "FL": "Southeast", "GA": "Southeast", "HI": "West", "ID": "West",
    "IL": "Midwest", "IN": "Midwest", "IA": "Midwest", "KS": "Midwest",
    "KY": "Southeast", "LA": "Southeast", "ME": "Northeast", "MD": "Northeast",
    "MA": "Northeast", "MI": "Midwest", "MN": "Midwest", "MS": "Southeast",
    "MO": "Midwest", "MT": "Mountain", "NE": "Midwest", "NV": "West",
    "NH": "Northeast", "NJ": "Northeast", "NM": "Southwest", "NY": "Northeast",
    "NC": "Southeast", "ND": "Midwest", "OH": "Midwest", "OK": "Southwest",
    "OR": "West", "PA": "Northeast", "RI": "Northeast", "SC": "Southeast",
    "SD": "Midwest", "TN": "Southeast", "TX": "Southwest", "UT": "Mountain",
    "VT": "Northeast", "VA": "Southeast", "WA": "West", "WV": "Southeast",
    "WI": "Midwest", "WY": "Mountain", "DC": "Northeast",
    "PR": "Caribbean", "GU": "Pacific", "VI": "Caribbean",
    "AS": "Pacific", "MP": "Pacific",
}

SECTOR_MAP = {
    "Public 4-year": "4year_public",
    "Public 2-year": "2year_public",
    "Private nonprofit 4-year": "4year_private",
    "Private nonprofit 2-year": "2year_private",
    "Public PAB": "public_pab",
    "Private nonprofit PAB": "private_pab",
}


# ============================================================
# STEP 1: Read HSI list from Excel
# ============================================================

def load_hsi_list():
    """Load HSI institutions from the NSC Excel file."""
    print("=" * 60)
    print("STEP 1: Loading HSI list from Excel...")
    print("=" * 60)

    wb = openpyxl.load_workbook(HSI_EXCEL)
    ws = wb["HSIs"]

    institutions = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        ipeds_id, name, state, sector, year = row
        if year == "2023-2024" and ipeds_id:
            ipeds_id = str(ipeds_id)
            state_code = STATE_CODES.get(state, state)
            institutions[ipeds_id] = {
                "ipeds_id": ipeds_id,
                "name": name.title() if name == name.upper() else name,
                "state_full": state,
                "state": state_code,
                "sector": sector,
                "type": SECTOR_MAP.get(sector, "other"),
                "region": REGION_MAP.get(state_code, "Other"),
            }

    print(f"  Loaded {len(institutions)} HSIs for 2023-2024")
    return institutions


# ============================================================
# STEP 2: Enrich with IPEDS data from Urban Institute API
# ============================================================

def fetch_ipeds_data(unitid):
    """Fetch institution data from Urban Institute API."""
    url = f"{URBAN_API_BASE}/college-university/ipeds/directory/2022/?unitid={unitid}&f=json"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                return results[0]
    except Exception as e:
        pass
    return None


def fetch_enrollment_fte(unitid):
    """Fetch FTE enrollment data from Urban Institute API."""
    url = f"{URBAN_API_BASE}/college-university/ipeds/enrollment-full-time-equivalent/2021/?unitid={unitid}&f=json"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            # Sum all levels of study for total FTE
            total_fte = 0
            for r in results:
                fte = r.get("rep_fte") or r.get("est_fte") or 0
                if fte > 0:
                    total_fte += fte
            return total_fte
    except Exception:
        pass
    return 0


def enrich_institutions(institutions):
    """Enrich institutions with IPEDS data."""
    print("\n" + "=" * 60)
    print("STEP 2: Enriching with IPEDS data (this takes a while)...")
    print("=" * 60)

    total = len(institutions)
    enriched = 0
    failed = 0

    for i, (ipeds_id, inst) in enumerate(institutions.items()):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Processing {i+1}/{total}...")

        # Fetch directory data
        ipeds = fetch_ipeds_data(ipeds_id)
        if ipeds:
            inst["city"] = (ipeds.get("city") or "").title()
            inst["lat"] = ipeds.get("latitude")
            inst["lng"] = ipeds.get("longitude")
            inst["website"] = ipeds.get("url_school")

            # Use proper name from IPEDS if available
            ipeds_name = ipeds.get("inst_name")
            if ipeds_name:
                inst["name"] = ipeds_name

            # State from IPEDS
            state_abbr = ipeds.get("state_abbr")
            if state_abbr:
                inst["state"] = state_abbr
                inst["region"] = REGION_MAP.get(state_abbr, inst.get("region", "Other"))

            # Carnegie classification
            carnegie = ipeds.get("cc_basic_2021")
            if carnegie and carnegie > 0:
                carnegie_labels = {
                    1: "R1: Doctoral Universities – Very High Research Activity",
                    2: "R2: Doctoral Universities – High Research Activity",
                    3: "Doctoral/Professional Universities",
                    4: "Master's Colleges & Universities: Larger Programs",
                    5: "Master's Colleges & Universities: Medium Programs",
                    6: "Master's Colleges & Universities: Small Programs",
                    7: "Baccalaureate Colleges: Arts & Sciences Focus",
                    8: "Baccalaureate Colleges: Diverse Fields",
                    9: "Baccalaureate/Associate's Colleges",
                    10: "Baccalaureate/Associate's Mixed",
                    14: "Associate's Colleges: High Transfer-High Traditional",
                    15: "Associate's Colleges: High Transfer-Mixed Traditional/Nontraditional",
                    16: "Associate's Colleges: High Transfer-High Nontraditional",
                    17: "Associate's Colleges: Mixed Transfer/Career-High Traditional",
                    18: "Associate's Colleges: Mixed Transfer/Career-Mixed Traditional/Nontraditional",
                    19: "Associate's Colleges: Mixed Transfer/Career-High Nontraditional",
                    20: "Associate's Colleges: High Career-High Traditional",
                    21: "Associate's Colleges: High Career-Mixed Traditional/Nontraditional",
                    22: "Associate's Colleges: High Career-High Nontraditional",
                    23: "Special Focus Two-Year Institutions",
                    24: "Special Focus Four-Year: Faith-Related Institutions",
                    25: "Special Focus Four-Year: Medical Schools & Centers",
                    26: "Special Focus Four-Year: Other Health Professions Schools",
                    27: "Special Focus Four-Year: Engineering Schools",
                    28: "Special Focus Four-Year: Other Technology-Related Schools",
                    29: "Special Focus Four-Year: Business & Management Schools",
                    30: "Special Focus Four-Year: Arts, Music & Design Schools",
                    31: "Special Focus Four-Year: Law Schools",
                    32: "Special Focus Four-Year: Other Special Focus Institutions",
                    33: "Tribal Colleges",
                }
                inst["carnegie_classification"] = carnegie_labels.get(carnegie, f"Carnegie Class {carnegie}")

                # Determine if it's a research institution
                if carnegie in [1, 2]:
                    if "public" in inst.get("type", ""):
                        inst["type"] = "4year_public_research"
                    elif "private" in inst.get("type", ""):
                        inst["type"] = "4year_private_research"

            # Fix website URL
            if inst.get("website") and not inst["website"].startswith("http"):
                inst["website"] = "https://" + inst["website"]

            # Fetch enrollment
            fte = fetch_enrollment_fte(ipeds_id)
            if fte > 0:
                inst["total_enrollment"] = fte

            enriched += 1
        else:
            failed += 1

        time.sleep(API_DELAY)

    print(f"\n  Enriched: {enriched}, Failed: {failed}")
    return institutions


# ============================================================
# STEP 3: Add CAHSI membership info
# ============================================================

def add_cahsi_info(institutions):
    """Add CAHSI membership information."""
    print("\n" + "=" * 60)
    print("STEP 3: Adding CAHSI membership data...")
    print("=" * 60)

    matched = 0
    for ipeds_id, inst in institutions.items():
        cahsi_info = get_cahsi_info(inst["name"])
        if cahsi_info:
            inst["is_cahsi_member"] = True
            inst["cahsi_role"] = cahsi_info["role"]
            matched += 1
        else:
            inst["is_cahsi_member"] = False
            inst["cahsi_role"] = None

    print(f"  Matched {matched} CAHSI members")

    # Also add non-HSI CAHSI members (like UC San Diego, Georgia State)
    # These won't be in the HSI list but are CAHSI members
    non_hsi_cahsi = {
        "University of California-San Diego": "110680",
        "Georgia State University": "139940",
        "University of California-Merced": "445188",
        "University of California-Santa Cruz": "110714",
    }

    added = 0
    for name, ipeds_id in non_hsi_cahsi.items():
        if ipeds_id not in institutions:
            institutions[ipeds_id] = {
                "ipeds_id": ipeds_id,
                "name": name,
                "is_hsi": False,
                "is_cahsi_member": True,
                "cahsi_role": "member",
                "type": "4year_public_research",
            }
            # Fetch their data too
            ipeds = fetch_ipeds_data(ipeds_id)
            if ipeds:
                inst = institutions[ipeds_id]
                inst["city"] = (ipeds.get("city") or "").title()
                inst["state"] = ipeds.get("state_abbr") or ""
                inst["region"] = REGION_MAP.get(inst["state"], "Other")
                inst["lat"] = ipeds.get("latitude")
                inst["lng"] = ipeds.get("longitude")
                inst["website"] = ipeds.get("url_school")
                inst["name"] = ipeds.get("inst_name") or name
                if inst.get("website") and not inst["website"].startswith("http"):
                    inst["website"] = "https://" + inst["website"]
                fte = fetch_enrollment_fte(ipeds_id)
                if fte > 0:
                    inst["total_enrollment"] = fte
                carnegie = ipeds.get("cc_basic_2021")
                if carnegie == 1:
                    inst["carnegie_classification"] = "R1: Doctoral Universities – Very High Research Activity"
                elif carnegie == 2:
                    inst["carnegie_classification"] = "R2: Doctoral Universities – High Research Activity"
                added += 1
            time.sleep(API_DELAY)

    print(f"  Added {added} non-HSI CAHSI members")
    return institutions


# ============================================================
# STEP 4: Generate IDs and clean up
# ============================================================

def generate_id(name):
    """Generate a URL-friendly ID from institution name."""
    # Common abbreviations
    abbreviations = {
        "university": "u",
        "college": "c",
        "community": "cc",
        "state": "st",
        "california": "ca",
        "texas": "tx",
    }

    name_clean = name.lower()
    # Remove common words
    for word in ["the ", "of ", "at ", "and ", "- ", "district"]:
        name_clean = name_clean.replace(word, "")

    # Create slug
    slug = ""
    for char in name_clean:
        if char.isalnum():
            slug += char
        elif char in " -":
            slug += "_"

    # Clean up multiple underscores
    while "__" in slug:
        slug = slug.replace("__", "_")
    slug = slug.strip("_")

    # Truncate if too long
    if len(slug) > 40:
        slug = slug[:40].rstrip("_")

    return slug


def create_short_name(name):
    """Create a short display name."""
    # Common mappings
    if "University of Texas at El Paso" in name:
        return "UTEP"
    if "University of Texas at San Antonio" in name:
        return "UTSA"
    if "University of Texas Rio Grande Valley" in name:
        return "UTRGV"

    # Try to create abbreviation from capitals
    words = name.replace("-", " ").replace("  ", " ").split()
    # Filter out common words
    skip = {"the", "of", "at", "and", "in", "for", "a", "an"}
    significant = [w for w in words if w.lower() not in skip]

    if len(significant) <= 3:
        return name

    # For "California State University-Fullerton" -> "CSU Fullerton"
    if "State University" in name and "California" in name:
        campus = name.split("-")[-1] if "-" in name else ""
        return f"CSU {campus}" if campus else name

    # Generic: use first letters
    abbr = "".join(w[0].upper() for w in significant if len(w) > 2)
    if len(abbr) >= 2 and len(abbr) <= 6:
        return abbr

    return name


def finalize_institutions(institutions):
    """Clean up and finalize institution data."""
    print("\n" + "=" * 60)
    print("STEP 4: Finalizing data...")
    print("=" * 60)

    final_list = []
    skipped = 0

    for ipeds_id, inst in institutions.items():
        # Skip if no coordinates (can't show on map)
        if not inst.get("lat") or not inst.get("lng"):
            skipped += 1
            continue

        inst_id = generate_id(inst["name"])
        short_name = create_short_name(inst["name"])

        # Build final record
        record = {
            "id": inst_id,
            "ipeds_id": ipeds_id,
            "name": inst["name"],
            "short_name": short_name if short_name != inst["name"] else None,
            "city": inst.get("city", ""),
            "state": inst.get("state", ""),
            "region": inst.get("region", "Other"),
            "type": inst.get("type", "other"),
            "carnegie_classification": inst.get("carnegie_classification"),
            "total_enrollment": inst.get("total_enrollment", 0),
            "is_hsi": inst.get("is_hsi", True),
            "is_cahsi_member": inst.get("is_cahsi_member", False),
            "cahsi_role": inst.get("cahsi_role"),
            "website": inst.get("website"),
            "ai_policy_url": None,
            "ai_highlights": [],
            "key_programs": [],
            "ai_readiness": {
                "overall_score": 1,
                "teaching_score": 1,
                "policy_score": 1,
                "ethics_score": 1,
                "research_score": 1,
                "infrastructure_score": 1,
                "notes": ""
            },
            "initiatives": [],
            "lat": inst["lat"],
            "lng": inst["lng"],
        }

        final_list.append(record)

    # Sort by name
    final_list.sort(key=lambda x: x["name"])

    print(f"  Final count: {len(final_list)} institutions ({skipped} skipped due to missing coordinates)")
    return final_list


# ============================================================
# STEP 5: Merge with existing curated data
# ============================================================

def merge_with_existing(new_institutions):
    """Merge new data with existing curated institution data."""
    print("\n" + "=" * 60)
    print("STEP 5: Merging with existing curated data...")
    print("=" * 60)

    # Load existing data from the backup
    backup_file = PROJECT_ROOT / "data" / "institutions" / "institutions_original.json"
    existing = {}
    source_file = backup_file if backup_file.exists() else OUTPUT_FILE
    if source_file.exists():
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for inst in data.get("institutions", []):
                # Match by name (case-insensitive, normalized)
                key = normalize_name(inst["name"])
                existing[key] = inst

    merged = 0
    for inst in new_institutions:
        key = normalize_name(inst["name"])
        if key in existing:
            old = existing[key]
            # Keep curated fields from existing data
            if old.get("ai_policy_url"):
                inst["ai_policy_url"] = old["ai_policy_url"]
            if old.get("ai_highlights"):
                inst["ai_highlights"] = old["ai_highlights"]
            if old.get("key_programs"):
                inst["key_programs"] = old["key_programs"]
            if old.get("initiatives"):
                inst["initiatives"] = old["initiatives"]
            if old.get("ai_readiness", {}).get("overall_score", 1) > 1:
                inst["ai_readiness"] = old["ai_readiness"]
            if old.get("short_name"):
                inst["short_name"] = old["short_name"]
            if old.get("id"):
                inst["id"] = old["id"]
            merged += 1

    print(f"  Merged curated data for {merged} institutions")
    return new_institutions


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("  AI Readiness Atlas - Institution Data Builder")
    print("  Institute for Applied AI Innovation - UTEP")
    print("=" * 60 + "\n")

    # Step 1: Load HSI list
    institutions = load_hsi_list()

    # Mark all as HSI
    for inst in institutions.values():
        inst["is_hsi"] = True

    # Step 2: Enrich with IPEDS data
    institutions = enrich_institutions(institutions)

    # Step 3: Add CAHSI info
    institutions = add_cahsi_info(institutions)

    # Step 4: Finalize
    final_list = finalize_institutions(institutions)

    # Step 5: Merge with existing curated data
    final_list = merge_with_existing(final_list)

    # Save
    output_data = {
        "metadata": {
            "version": "2.0",
            "last_updated": "2025-02-07",
            "description": "Hispanic-Serving Institutions database for AI Readiness Atlas",
            "total_institutions": len(final_list),
            "sources": [
                "National Student Clearinghouse HSI Lookup Table (July 2025)",
                "IPEDS via Urban Institute Education Data API",
                "CAHSI Member Institutions Directory",
                "HACU Hispanic-Serving Institutions List 2023-24",
                "Public university websites"
            ]
        },
        "institutions": final_list
    }

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("  COMPLETE!")
    print("=" * 60)
    print(f"\n  Output: {OUTPUT_FILE}")
    print(f"  Total institutions: {len(final_list)}")

    # Stats
    hsi_count = sum(1 for i in final_list if i.get("is_hsi"))
    cahsi_count = sum(1 for i in final_list if i.get("is_cahsi_member"))
    with_policy = sum(1 for i in final_list if i.get("ai_policy_url"))
    with_programs = sum(1 for i in final_list if i.get("key_programs"))
    states = set(i["state"] for i in final_list)

    print(f"  HSIs: {hsi_count}")
    print(f"  CAHSI members: {cahsi_count}")
    print(f"  With AI policy: {with_policy}")
    print(f"  With programs: {with_programs}")
    print(f"  States: {len(states)}")
    print()


if __name__ == "__main__":
    main()
