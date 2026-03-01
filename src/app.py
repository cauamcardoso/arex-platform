"""
AIREX - AI Readiness Explorer
A platform where academic institutions assess their AI readiness,
find peer institutions, and share what is working.

Built by the Institute for Applied AI Innovation at UTEP
"""

import os
import sys
import json
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

# Load resources database
resources_path = project_root / "data" / "resources" / "resources.json"
if resources_path.exists():
    with open(resources_path, 'r', encoding='utf-8') as f:
        resources_data = json.load(f)
        resources_db = resources_data.get('resources', [])
else:
    resources_db = []

# Load news database
news_path = project_root / "data" / "news" / "news.json"
if news_path.exists():
    with open(news_path, 'r', encoding='utf-8') as f:
        news_data = json.load(f)
        news_db = news_data.get('articles', [])
else:
    news_db = []


# ============================================================
# ROUTES - PAGES
# ============================================================

@app.route("/")
def home():
    """Homepage - Landing page with value proposition."""
    stats = institutions_db.get_stats()

    # Format total enrollment for display (e.g., "4M")
    total_enrollment = stats["total_enrollment"]
    if total_enrollment >= 1_000_000:
        millions = total_enrollment / 1_000_000
        enrollment_display = f"{millions:.0f}M" if millions == int(millions) else f"{millions:.1f}M"
    elif total_enrollment >= 1_000:
        enrollment_display = f"{total_enrollment / 1_000:.0f}K"
    else:
        enrollment_display = str(total_enrollment)

    return render_template(
        "home.html",
        total_institutions=stats["total_institutions"],
        states_count=stats["states_represented"],
        avg_readiness=stats["average_readiness_score"],
        total_enrollment=stats["total_enrollment"],
        total_enrollment_display=enrollment_display
    )


@app.route("/atlas")
def atlas():
    """AIREX Atlas - Interactive map of institutions."""
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


@app.route("/assessment")
def assessment():
    """AI Readiness Self-Assessment tool."""
    return render_template("assessment.html")


@app.route("/readiness")
def readiness():
    """AI Readiness concept page - What is AI readiness?"""
    return render_template("readiness.html")


@app.route("/repository")
def repository():
    """Conversational Repository - curated resources and search assistant."""
    return render_template("toolkit.html")


@app.route("/toolkit")
def toolkit():
    """Legacy route - redirect to repository."""
    return repository()


@app.route("/news")
def news():
    """AI News and Discovery page."""
    return render_template("news.html")


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


@app.route("/api/institutions/spotlight", methods=["GET"])
def get_institutions_spotlight():
    """
    Get spotlight institutions by readiness category.

    Query params:
        category: One of 'overall', 'teaching', 'policy', 'ethics', 'research', 'infrastructure'
        limit: Number of results (default 5)
    """
    category = request.args.get('category', default='overall')
    limit = request.args.get('limit', default=5, type=int)

    valid_categories = ['overall', 'teaching', 'policy', 'ethics', 'research', 'infrastructure']
    if category not in valid_categories:
        return jsonify({"error": f"Invalid category. Must be one of: {valid_categories}"}), 400

    spotlight = institutions_db.get_spotlight_by_category(category, limit=limit)

    return jsonify({
        "category": category,
        "spotlight": spotlight,
        "count": len(spotlight)
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


# ============================================================
# ROUTES - RESOURCES API
# ============================================================

@app.route("/api/resources", methods=["GET"])
def get_resources():
    """Get all resources or filter by pillar/type."""
    pillar = request.args.get('pillar')
    rtype = request.args.get('type')

    results = resources_db
    if pillar:
        results = [r for r in results if r.get('pillar') == pillar]
    if rtype:
        results = [r for r in results if r.get('type') == rtype]

    return jsonify({
        "resources": results,
        "count": len(results)
    })


@app.route("/api/resources/search", methods=["GET"])
def search_resources():
    """
    Search resources by query string.
    Searches across title, description, topics, readings, and content sections.
    Returns matching resources with relevant excerpts.
    """
    query = request.args.get('q', '').lower().strip()
    if not query:
        return jsonify({"results": [], "count": 0, "query": ""})

    query_terms = query.split()
    results = []

    for resource in resources_db:
        score = 0
        matches = []

        # Search in title
        title = resource.get('title', '').lower()
        if any(term in title for term in query_terms):
            score += 5

        # Search in description
        desc = resource.get('description', '').lower()
        if any(term in desc for term in query_terms):
            score += 3

        # Search in topics
        topics = ' '.join(resource.get('topics', [])).lower()
        for term in query_terms:
            if term in topics:
                score += 4

        # Search in readings (syllabi)
        readings = resource.get('readings', [])
        matched_readings = []
        for reading in readings:
            reading_text = f"{reading.get('title', '')} {reading.get('author', '')} {' '.join(reading.get('topics', []))}".lower()
            if any(term in reading_text for term in query_terms):
                score += 3
                matched_readings.append(reading)

        # Search in sessions (workshops)
        sessions = resource.get('sessions', [])
        matched_sessions = []
        for session in sessions:
            session_text = f"{session.get('title', '')} {session.get('description', '')}".lower()
            if any(term in session_text for term in query_terms):
                score += 2
                matched_sessions.append(session)

        # Search in content sections
        sections = resource.get('content_sections', [])
        matched_sections = []
        for section in sections:
            section_text = f"{section.get('section', '')} {section.get('summary', '')} {' '.join(section.get('items', []))}".lower()
            if any(term in section_text for term in query_terms):
                score += 2
                matched_sections.append(section)

        if score > 0:
            result = {
                "resource": resource,
                "relevance_score": score,
                "matched_readings": matched_readings,
                "matched_sessions": matched_sessions,
                "matched_sections": matched_sections
            }
            results.append(result)

    # Sort by relevance
    results.sort(key=lambda x: x['relevance_score'], reverse=True)

    return jsonify({
        "results": results[:10],
        "count": len(results),
        "query": query
    })


# ============================================================
# ROUTES - NEWS API
# ============================================================

@app.route("/api/news", methods=["GET"])
def get_news():
    """Get news articles, optionally filtered by pillar."""
    pillar = request.args.get('pillar')

    results = news_db
    if pillar:
        results = [a for a in results if a.get('pillar') == pillar]

    # Sort by date descending
    results.sort(key=lambda x: x.get('date', ''), reverse=True)

    return jsonify({
        "articles": results,
        "count": len(results)
    })


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AIREX - AI Readiness Explorer")
    print("  Institute for Applied AI Innovation - UTEP")
    print("=" * 60)

    stats = institutions_db.get_stats()
    print(f"\nInstitutions: {stats['total_institutions']}")
    print(f"HSIs: {stats['hsi_count']}")
    print(f"CAHSI Members: {stats['cahsi_member_count']}")
    print(f"States: {stats['states_represented']}")
    print(f"Resources: {len(resources_db)}")
    print(f"News Articles: {len(news_db)}")

    port = int(os.environ.get('PORT', os.environ.get('FLASK_RUN_PORT', 5000)))
    print(f"\nStarting server: http://127.0.0.1:{port}")
    print("\nPress Ctrl+C to stop")
    print("-" * 60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=port)
