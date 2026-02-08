"""
Institutions Database Module
Manages HSI/CAHSI institution data for the AI Readiness Atlas.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class InstitutionsDatabase:
    """
    Manages institution data for the AI Readiness Atlas.
    Provides search, filter, and aggregation capabilities.
    """

    def __init__(self, data_path: str = None):
        """
        Initialize the institutions database.

        Args:
            data_path: Path to institutions.json. Defaults to data/institutions/institutions.json
        """
        if data_path is None:
            project_root = Path(__file__).parent.parent
            data_path = project_root / "data" / "institutions" / "institutions.json"

        self.data_path = Path(data_path)
        self._load_data()

    def _load_data(self):
        """Load institution data from JSON file."""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.metadata = data.get('metadata', {})
                self.institutions = data.get('institutions', [])
        else:
            self.metadata = {}
            self.institutions = []

        # Build lookup index by ID
        self._index = {inst['id']: inst for inst in self.institutions}

        print(f"Institutions database loaded: {len(self.institutions)} institutions")

    def get_all(self) -> List[Dict]:
        """Get all institutions."""
        return self.institutions

    def get_by_id(self, institution_id: str) -> Optional[Dict]:
        """Get a single institution by ID."""
        return self._index.get(institution_id)

    def search(self, query: str) -> List[Dict]:
        """
        Search institutions by name, city, or state.

        Args:
            query: Search string

        Returns:
            List of matching institutions
        """
        query_lower = query.lower()
        results = []

        for inst in self.institutions:
            # Search in name, short_name, city, state
            searchable = f"{inst.get('name', '')} {inst.get('short_name', '')} {inst.get('city', '')} {inst.get('state', '')}".lower()
            if query_lower in searchable:
                results.append(inst)

        return results

    def filter(self,
               state: str = None,
               region: str = None,
               inst_type: str = None,
               is_hsi: bool = None,
               is_cahsi_member: bool = None,
               min_readiness: int = None,
               max_readiness: int = None) -> List[Dict]:
        """
        Filter institutions by various criteria.

        Args:
            state: Filter by state code (e.g., 'TX', 'CA')
            region: Filter by region (e.g., 'Southwest', 'West')
            inst_type: Filter by type (e.g., '4year_public_research', '2year_public')
            is_hsi: Filter by HSI status
            is_cahsi_member: Filter by CAHSI membership
            min_readiness: Minimum overall AI readiness score
            max_readiness: Maximum overall AI readiness score

        Returns:
            List of matching institutions
        """
        results = self.institutions.copy()

        if state:
            results = [i for i in results if i.get('state', '').upper() == state.upper()]

        if region:
            results = [i for i in results if i.get('region', '').lower() == region.lower()]

        if inst_type:
            results = [i for i in results if inst_type.lower() in i.get('type', '').lower()]

        if is_hsi is not None:
            results = [i for i in results if i.get('is_hsi') == is_hsi]

        if is_cahsi_member is not None:
            results = [i for i in results if i.get('is_cahsi_member') == is_cahsi_member]

        if min_readiness is not None:
            results = [i for i in results if i.get('ai_readiness', {}).get('overall_score', 0) >= min_readiness]

        if max_readiness is not None:
            results = [i for i in results if i.get('ai_readiness', {}).get('overall_score', 5) <= max_readiness]

        return results

    def get_by_state(self, state: str) -> List[Dict]:
        """Get all institutions in a state."""
        return self.filter(state=state)

    def get_cahsi_members(self) -> List[Dict]:
        """Get all CAHSI member institutions."""
        return self.filter(is_cahsi_member=True)

    def get_hsis(self) -> List[Dict]:
        """Get all Hispanic-Serving Institutions."""
        return self.filter(is_hsi=True)

    def get_stats(self) -> Dict:
        """
        Get aggregate statistics about the institutions database.

        Returns:
            Dictionary with various statistics
        """
        total = len(self.institutions)

        if total == 0:
            return {"total_institutions": 0}

        # Count by type
        type_counts = {}
        for inst in self.institutions:
            t = inst.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1

        # Count by state
        state_counts = {}
        for inst in self.institutions:
            s = inst.get('state', 'unknown')
            state_counts[s] = state_counts.get(s, 0) + 1

        # Count by region
        region_counts = {}
        for inst in self.institutions:
            r = inst.get('region', 'unknown')
            region_counts[r] = region_counts.get(r, 0) + 1

        # HSI and CAHSI counts
        hsi_count = len([i for i in self.institutions if i.get('is_hsi')])
        cahsi_count = len([i for i in self.institutions if i.get('is_cahsi_member')])

        # Readiness score distribution
        readiness_scores = [i.get('ai_readiness', {}).get('overall_score', 0) for i in self.institutions]
        avg_readiness = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0

        readiness_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for score in readiness_scores:
            if score in readiness_distribution:
                readiness_distribution[score] += 1

        # Total enrollment
        total_enrollment = sum(i.get('total_enrollment', 0) for i in self.institutions)

        return {
            "total_institutions": total,
            "hsi_count": hsi_count,
            "cahsi_member_count": cahsi_count,
            "by_type": type_counts,
            "by_state": state_counts,
            "by_region": region_counts,
            "average_readiness_score": round(avg_readiness, 2),
            "readiness_distribution": readiness_distribution,
            "total_enrollment": total_enrollment,
            "states_represented": len(state_counts),
            "regions_represented": len(region_counts)
        }

    def get_map_data(self) -> List[Dict]:
        """
        Get simplified data for map visualization.

        Returns:
            List of institutions with only the fields needed for map display
        """
        map_data = []
        for inst in self.institutions:
            map_data.append({
                "id": inst.get('id'),
                "name": inst.get('name'),
                "short_name": inst.get('short_name'),
                "city": inst.get('city'),
                "state": inst.get('state'),
                "lat": inst.get('lat'),
                "lng": inst.get('lng'),
                "type": inst.get('type'),
                "is_hsi": inst.get('is_hsi'),
                "is_cahsi_member": inst.get('is_cahsi_member'),
                "overall_score": inst.get('ai_readiness', {}).get('overall_score', 0),
                "hispanic_enrollment_pct": inst.get('hispanic_enrollment_pct', 0),
                "ai_policy_url": inst.get('ai_policy_url'),
                "ai_highlights": inst.get('ai_highlights', [])
            })
        return map_data

    def get_peer_institutions(self, institution_id: str, limit: int = 5) -> List[Dict]:
        """
        Find peer institutions similar to the given institution.
        Matches on: state/region, type, enrollment size, readiness level.

        Args:
            institution_id: The ID of the institution to find peers for
            limit: Maximum number of peers to return

        Returns:
            List of similar institutions
        """
        target = self.get_by_id(institution_id)
        if not target:
            return []

        target_type = target.get('type', '')
        target_state = target.get('state', '')
        target_region = target.get('region', '')
        target_enrollment = target.get('total_enrollment', 0)
        target_readiness = target.get('ai_readiness', {}).get('overall_score', 0)

        scored_peers = []

        for inst in self.institutions:
            if inst['id'] == institution_id:
                continue

            score = 0

            # Same type is important
            if inst.get('type') == target_type:
                score += 3
            elif target_type.split('_')[0] in inst.get('type', ''):
                score += 1

            # Same state
            if inst.get('state') == target_state:
                score += 2
            # Same region
            elif inst.get('region') == target_region:
                score += 1

            # Similar enrollment (within 50%)
            inst_enrollment = inst.get('total_enrollment', 0)
            if target_enrollment > 0 and inst_enrollment > 0:
                ratio = min(target_enrollment, inst_enrollment) / max(target_enrollment, inst_enrollment)
                if ratio > 0.5:
                    score += 1

            # Similar readiness
            inst_readiness = inst.get('ai_readiness', {}).get('overall_score', 0)
            if abs(inst_readiness - target_readiness) <= 1:
                score += 1

            if score > 0:
                scored_peers.append((score, inst))

        # Sort by score descending, take top N
        scored_peers.sort(key=lambda x: x[0], reverse=True)
        return [inst for score, inst in scored_peers[:limit]]

    def get_spotlight_by_category(self, category: str, limit: int = 5) -> List[Dict]:
        """
        Get spotlight institutions for a specific readiness category.
        Highlights institutions with strong practices others can learn from.

        Args:
            category: One of 'overall', 'teaching', 'policy', 'ethics', 'research', 'infrastructure'
            limit: Number of spotlight institutions to return

        Returns:
            List of spotlight institutions for that category
        """
        if category == 'overall':
            score_key = 'overall_score'
        else:
            score_key = f'{category}_score'

        scored = []
        for inst in self.institutions:
            score = inst.get('ai_readiness', {}).get(score_key, 0)
            scored.append((score, inst))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [inst for score, inst in scored[:limit]]


# Convenience function to get a singleton instance
_db_instance = None

def get_institutions_db() -> InstitutionsDatabase:
    """Get the singleton institutions database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = InstitutionsDatabase()
    return _db_instance


if __name__ == "__main__":
    # Test the module
    db = InstitutionsDatabase()

    print("\n" + "=" * 60)
    print("  AI Readiness Atlas - Institutions Database")
    print("=" * 60)

    stats = db.get_stats()
    print(f"\nTotal Institutions: {stats['total_institutions']}")
    print(f"HSIs: {stats['hsi_count']}")
    print(f"CAHSI Members: {stats['cahsi_member_count']}")
    print(f"States Represented: {stats['states_represented']}")
    print(f"Average AI Readiness: {stats['average_readiness_score']}/5")
    print(f"Total Student Enrollment: {stats['total_enrollment']:,}")

    print("\nBy Region:")
    for region, count in stats['by_region'].items():
        print(f"  {region}: {count}")

    print("\nReadiness Distribution:")
    for score, count in sorted(stats['readiness_distribution'].items()):
        print(f"  Level {score}: {count} institutions")

    print("\n" + "-" * 60)
    print("Sample Searches:")

    # Test search
    texas = db.get_by_state('TX')
    print(f"\nTexas institutions: {len(texas)}")

    # Test CAHSI filter
    cahsi = db.get_cahsi_members()
    print(f"CAHSI members: {len(cahsi)}")

    # Test readiness filter
    trailblazers = db.filter(min_readiness=5)
    print(f"Institutions with readiness score 5: {len(trailblazers)}")
    for inst in trailblazers[:3]:
        print(f"  - {inst['name']}")

    # Test peer finding
    print(f"\nPeers for UTEP:")
    peers = db.get_peer_institutions('utep', limit=3)
    for peer in peers:
        print(f"  - {peer['name']} ({peer['state']})")
