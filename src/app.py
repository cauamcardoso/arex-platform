"""
AI Readiness Atlas
A platform helping Hispanic-Serving Institutions navigate AI integration in higher education.

Built by the Institute for Applied AI Innovation at UTEP
For HACU and CAHSI member institutions
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from institutions import InstitutionsDatabase

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

app = Flask(__name__,
            template_folder=str(project_root / "templates"),
            static_folder=str(project_root / "static"))

# Initialize institutions database
institutions_db = InstitutionsDatabase()


# ============================================================
# ROUTES - PAGES
# ============================================================

@app.route("/")
def home():
    """Homepage - redirects to Atlas for now."""
    return atlas()


@app.route("/atlas")
def atlas():
    """AI Readiness Atlas - Interactive map of HSI institutions."""
    stats = institutions_db.get_stats()

    return render_template(
        "atlas.html",
        total_institutions=stats["total_institutions"],
        hsi_count=stats["hsi_count"],
        cahsi_count=stats["cahsi_member_count"],
        states_count=stats["states_represented"],
        avg_readiness=stats["average_readiness_score"],
        total_enrollment=stats["total_enrollment"]
    )


@app.route("/institution/<institution_id>")
def institution_profile(institution_id):
    """Individual institution profile page."""
    institution = institutions_db.get_by_id(institution_id)

    if not institution:
        return render_template("404.html"), 404

    peers = institutions_db.get_peer_institutions(institution_id, limit=5)

    return render_template(
        "institution.html",
        institution=institution,
        peers=peers
    )


# ============================================================
# ROUTES - API
# ============================================================

@app.route("/api/institutions", methods=["GET"])
def get_institutions():
    """
    Get all institutions or filter by criteria.

    Query params:
        state: Filter by state code (e.g., 'TX', 'CA')
        region: Filter by region (e.g., 'Southwest', 'West')
        type: Filter by institution type
        is_hsi: Filter by HSI status (true/false)
        is_cahsi: Filter by CAHSI membership (true/false)
        min_readiness: Minimum readiness score (1-5)
        max_readiness: Maximum readiness score (1-5)
        search: Search by name/city
    """
    state = request.args.get('state')
    region = request.args.get('region')
    inst_type = request.args.get('type')
    is_hsi = request.args.get('is_hsi')
    is_cahsi = request.args.get('is_cahsi')
    min_readiness = request.args.get('min_readiness', type=int)
    max_readiness = request.args.get('max_readiness', type=int)
    search_query = request.args.get('search')

    # Convert string booleans
    if is_hsi is not None:
        is_hsi = is_hsi.lower() == 'true'
    if is_cahsi is not None:
        is_cahsi = is_cahsi.lower() == 'true'

    if search_query:
        results = institutions_db.search(search_query)
    else:
        results = institutions_db.filter(
            state=state,
            region=region,
            inst_type=inst_type,
            is_hsi=is_hsi,
            is_cahsi_member=is_cahsi,
            min_readiness=min_readiness,
            max_readiness=max_readiness
        )

    return jsonify({
        "institutions": results,
        "count": len(results)
    })


@app.route("/api/institutions/<institution_id>", methods=["GET"])
def get_institution(institution_id):
    """Get a single institution by ID."""
    institution = institutions_db.get_by_id(institution_id)

    if not institution:
        return jsonify({"error": "Institution not found"}), 404

    peers = institutions_db.get_peer_institutions(institution_id, limit=5)

    return jsonify({
        "institution": institution,
        "peers": peers
    })


@app.route("/api/institutions/<institution_id>/peers", methods=["GET"])
def get_institution_peers(institution_id):
    """Get peer institutions for a given institution."""
    limit = request.args.get('limit', default=5, type=int)
    peers = institutions_db.get_peer_institutions(institution_id, limit=limit)

    return jsonify({
        "institution_id": institution_id,
        "peers": peers,
        "count": len(peers)
    })


@app.route("/api/institutions/map", methods=["GET"])
def get_institutions_map():
    """Get institution data optimized for map visualization."""
    map_data = institutions_db.get_map_data()

    return jsonify({
        "institutions": map_data,
        "count": len(map_data)
    })


@app.route("/api/institutions/stats", methods=["GET"])
def get_institutions_stats():
    """Get aggregate statistics about institutions."""
    stats = institutions_db.get_stats()
    return jsonify(stats)


@app.route("/api/institutions/leaders", methods=["GET"])
def get_institutions_leaders():
    """
    Get top institutions by readiness category.

    Query params:
        category: One of 'overall', 'teaching', 'policy', 'ethics', 'research', 'infrastructure'
        limit: Number of results (default 5)
    """
    category = request.args.get('category', default='overall')
    limit = request.args.get('limit', default=5, type=int)

    valid_categories = ['overall', 'teaching', 'policy', 'ethics', 'research', 'infrastructure']
    if category not in valid_categories:
        return jsonify({"error": f"Invalid category. Must be one of: {valid_categories}"}), 400

    leaders = institutions_db.get_leaders_by_category(category, limit=limit)

    return jsonify({
        "category": category,
        "leaders": leaders,
        "count": len(leaders)
    })


@app.route("/api/institutions/states", methods=["GET"])
def get_institution_states():
    """Get list of states with institution counts."""
    stats = institutions_db.get_stats()
    states = stats.get('by_state', {})

    state_names = {
        'TX': 'Texas', 'CA': 'California', 'FL': 'Florida', 'NY': 'New York',
        'IL': 'Illinois', 'AZ': 'Arizona', 'NM': 'New Mexico', 'PR': 'Puerto Rico',
        'NJ': 'New Jersey', 'GA': 'Georgia', 'CO': 'Colorado'
    }

    state_list = []
    for code, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
        state_list.append({
            "code": code,
            "name": state_names.get(code, code),
            "count": count
        })

    return jsonify({
        "states": state_list,
        "total_states": len(state_list)
    })


@app.route("/api/institutions/regions", methods=["GET"])
def get_institution_regions():
    """Get list of regions with institution counts."""
    stats = institutions_db.get_stats()
    regions = stats.get('by_region', {})

    region_list = []
    for name, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
        region_list.append({
            "name": name,
            "count": count
        })

    return jsonify({
        "regions": region_list,
        "total_regions": len(region_list)
    })


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AI Readiness Atlas")
    print("  Institute for Applied AI Innovation - UTEP")
    print("=" * 60)

    stats = institutions_db.get_stats()
    print(f"\nInstitutions: {stats['total_institutions']}")
    print(f"HSIs: {stats['hsi_count']}")
    print(f"CAHSI Members: {stats['cahsi_member_count']}")
    print(f"States: {stats['states_represented']}")

    print("\nStarting server: http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop")
    print("-" * 60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000)
