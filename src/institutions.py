"""
Institutions Database Module
Manages institution data for AIREX - AI Readiness Explorer.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class InstitutionsDatabase:
    """
    Manages institution data for AIREX - AI Readiness Explorer.
    Provides search, filter, and aggregation capabilities.
    """

    def __init__(self, data_path: str = None):
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
        return self.institutions

    def get_by_id(self, institution_id: str) -> Optional[Dict]:
        return self._index.get(institution_id)

    def search(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for inst in self.institutions:
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
        return self.filter(state=state)

    def get_cahsi_members(self) -> List[Dict]:
        return self.filter(is_cahsi_member=True)

    def get_hsis(self) -> List[Dict]:
        return self.filter(is_hsi=True)

    def get_stats(self) -> Dict:
        total = len(self.institutions)
        if total == 0:
            return {"total_institutions": 0}

        type_counts = {}
        for inst in self.institutions:
            t = inst.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1

        state_counts = {}
        for inst in self.institutions:
            s = inst.get('state', 'unknown')
            state_counts[s] = state_counts.get(s, 0) + 1

        region_counts = {}
        for inst in self.institutions:
            r = inst.get('region', 'unknown')
            region_counts[r] = region_counts.get(r, 0) + 1

        hsi_count = len([i for i in self.institutions if i.get('is_hsi')])
        cahsi_count = len([i for i in self.institutions if i.get('is_cahsi_member')])

        readiness_scores = [i.get('ai_readiness', {}).get('overall_score', 0) for i in self.institutions]
        avg_readiness = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0

        readiness_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for score in readiness_scores:
            if score in readiness_distribution:
                readiness_distribution[score] += 1

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
                "total_enrollment": inst.get('total_enrollment', 0),
                "ai_policy_url": inst.get('ai_policy_url'),
                "ai_highlights": inst.get('ai_highlights', []),
                "key_programs": inst.get('key_programs', []),
                "initiatives": inst.get('initiatives', [])
            })
        return map_data

    def get_peer_institutions(self, institution_id: str, limit: int = 5) -> List[Dict]:
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
            if inst.get('type') == target_type:
                score += 3
            elif target_type.split('_')[0] in inst.get('type', ''):
                score += 1
            if inst.get('state') == target_state:
                score += 2
            elif inst.get('region') == target_region:
                score += 1
            inst_enrollment = inst.get('total_enrollment', 0)
            if target_enrollment > 0 and inst_enrollment > 0:
                ratio = min(target_enrollment, inst_enrollment) / max(target_enrollment, inst_enrollment)
                if ratio > 0.5:
                    score += 1
            inst_readiness = inst.get('ai_readiness', {}).get('overall_score', 0)
            if abs(inst_readiness - target_readiness) <= 1:
                score += 1

            if score > 0:
                scored_peers.append((score, inst))

        scored_peers.sort(key=lambda x: x[0], reverse=True)
        return [inst for score, inst in scored_peers[:limit]]

    def get_spotlight_by_category(self, category: str, limit: int = 5) -> List[Dict]:
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


_db_instance = None

def get_institutions_db() -> InstitutionsDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = InstitutionsDatabase()
    return _db_instance
