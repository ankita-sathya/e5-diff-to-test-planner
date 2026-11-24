"""Risk-based test selection planner and Jira Xray gap synthesis engine."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
import json
import hashlib
import numpy as np
from datetime import datetime

from src.embedder import EmbedderBase
from src.diff_parser import DiffSummary
from src.visual_evidence import VisualMatch


@dataclass
class RankedTest:
    """A test case ranked by similarity score."""
    test_id: str
    title: str
    domain: str
    similarity_score: float
    hil_bench_tags: List[str] = field(default_factory=list)
    estimated_duration_seconds: int = 0
    language: str = "EN"
    visual_similarity_score: Optional[float] = None
    visual_query: Optional[str] = None
    visual_reference: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class XrayGapTicket:
    """Auto-generated Jira Xray gap test ticket."""
    suggested_id: str
    title: str
    domain: str
    preconditions: str
    test_steps: List[str]
    expected_result: str
    hil_bench_tags: List[str] = field(default_factory=list)
    gap_reason: str = ""
    similarity_max: float = 0.0
    affected_domains: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_jira_description(self) -> str:
        """Format as Jira issue description."""
        return f"""*Preconditions:*
{self.preconditions}

*Steps:*
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(self.test_steps))}

*Expected Result:*
{self.expected_result}

*HIL Bench Tags:*
{', '.join(self.hil_bench_tags) if self.hil_bench_tags else "N/A"}

*Gap Analysis:*
{self.gap_reason}

*Affected Domains:*
{', '.join(self.affected_domains) if self.affected_domains else "N/A"}
"""


@dataclass
class PlannerResult:
    """Complete test selection and gap analysis result."""
    ranked_tests: List[RankedTest]
    total_hil_time_seconds: int
    hil_time_saved_seconds: int
    full_suite_time_seconds: int
    test_count: int
    full_suite_count: int
    high_risk_tests: List[RankedTest]
    medium_risk_tests: List[RankedTest]
    gap_tickets: List[XrayGapTicket]
    execution_summary: str
    
    def to_dict(self) -> dict:
        return {
            "ranked_tests": [t.to_dict() for t in self.ranked_tests],
            "total_hil_time_seconds": self.total_hil_time_seconds,
            "hil_time_saved_seconds": self.hil_time_saved_seconds,
            "full_suite_time_seconds": self.full_suite_time_seconds,
            "test_count": self.test_count,
            "full_suite_count": self.full_suite_count,
            "high_risk_tests": [t.to_dict() for t in self.high_risk_tests],
            "medium_risk_tests": [t.to_dict() for t in self.medium_risk_tests],
            "gap_tickets": [g.to_dict() for g in self.gap_tickets],
            "execution_summary": self.execution_summary,
        }


class TestPlanner:
    """
    Risk-based test selection and Jira Xray gap detection engine.
    
    Thresholds:
    - HIGH >= 0.78
    - MEDIUM >= 0.65
    - GAP DETECTION < 0.62
    """
    
    HIGH_RISK_THRESHOLD = 0.78
    MEDIUM_RISK_THRESHOLD = 0.65
    GAP_DETECTION_THRESHOLD = 0.62
    
    def __init__(self, embedder: EmbedderBase):
        """
        Initialize planner.
        
        Args:
            embedder: EmbedderBase instance for computing embeddings
        """
        self.embedder = embedder
        self.test_catalog: List[dict] = []
        self.embeddings_cache: dict[str, np.ndarray] = {}
    
    def load_test_catalog(self, catalog_path: str) -> None:
        """Load test catalog from JSON file."""
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.test_catalog = json.load(f)
        
        # Pre-compute embeddings for all tests
        for test in self.test_catalog:
            test_description = f"{test['title']} {test['domain']} {' '.join(test.get('steps', []))} {test.get('expected_result', '')}"
            self.embeddings_cache[test['id']] = self.embedder.embed_passage(test_description)
    
    def plan(
        self,
        diff_summary: DiffSummary,
        defect_description: Optional[str] = None,
        full_suite_time_seconds: int = 28800,  # 8 hours for 4000 tests @ 7.2s avg
        visual_matches: Optional[dict[str, VisualMatch]] = None,
        visual_threshold: float = 0.8,
    ) -> PlannerResult:
        """
        Plan test selection based on PR diff and defect.
        
        Args:
            diff_summary: Parsed Git diff
            defect_description: Optional Jira defect text
            full_suite_time_seconds: Total runtime for full test suite
            
        Returns:
            PlannerResult with ranked tests, gaps, and time savings
        """
        # Combine diff and defect into query text
        query_text = diff_summary.semantic_summary
        if defect_description:
            query_text += f" {defect_description}"
        query_text = query_text.strip()
        
        query_embedding = self.embedder.embed_query(query_text) if query_text else None
        
        # Score all tests
        scored_tests = []
        for test in self.test_catalog:
            test_embedding = self.embeddings_cache.get(test['id'])
            if test_embedding is None:
                continue
            
            # Cosine similarity
            similarity = float(np.dot(query_embedding, test_embedding)) if query_embedding is not None else 0.0
            similarity = np.clip(similarity, 0.0, 1.0)
            
            scored_tests.append({
                'test': test,
                'similarity': similarity
            })
        
        # Sort by similarity descending
        scored_tests.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Classify by risk level
        high_risk = []
        medium_risk = []
        low_risk = []
        gaps = []
        
        for scored in scored_tests:
            test = scored['test']
            sim = scored['similarity']
            visual_match = (visual_matches or {}).get(test['id'])
            
            ranked_test = RankedTest(
                test_id=test['id'],
                title=test['title'],
                domain=test['domain'],
                similarity_score=sim,
                hil_bench_tags=test.get('hil_bench_tags', []),
                estimated_duration_seconds=test.get('estimated_duration_seconds', 60),
                language=test.get('languages_tested', ['EN'])[0],
                visual_similarity_score=visual_match.score if visual_match else None,
                visual_query=visual_match.query if visual_match else None,
                visual_reference=visual_match.reference if visual_match else None,
            )
            
            if sim >= self.HIGH_RISK_THRESHOLD:
                high_risk.append(ranked_test)
            elif sim >= self.MEDIUM_RISK_THRESHOLD or (
                visual_match is not None and visual_match.score >= visual_threshold
            ):
                medium_risk.append(ranked_test)
            else:
                low_risk.append(ranked_test)
            
        if query_text and scored_tests and scored_tests[0]['similarity'] < self.GAP_DETECTION_THRESHOLD:
            closest = scored_tests[0]
            gaps.append(self._synthesize_gap(closest['test'], scored_tests, closest['similarity']))
        
        # Compile results
        selected_tests = high_risk + medium_risk
        total_hil_time = sum(t.estimated_duration_seconds for t in selected_tests)
        hil_time_saved = full_suite_time_seconds - total_hil_time
        
        # Generate summary
        summary = self._generate_summary(
            high_risk, medium_risk, full_suite_time_seconds, total_hil_time, gaps,
            visual_matches is not None and bool(visual_matches),
        )
        
        return PlannerResult(
            ranked_tests=selected_tests,
            total_hil_time_seconds=total_hil_time,
            hil_time_saved_seconds=max(0, hil_time_saved),
            full_suite_time_seconds=full_suite_time_seconds,
            test_count=len(selected_tests),
            full_suite_count=len(self.test_catalog),
            high_risk_tests=high_risk,
            medium_risk_tests=medium_risk,
            gap_tickets=gaps,
            execution_summary=summary
        )
    
    def _synthesize_gap(self, closest_test: dict, all_scored: List[dict], max_sim: float) -> XrayGapTicket:
        """Synthesize a new Jira Xray test ticket for coverage gap."""
        domains = set()
        for scored in all_scored[:10]:
            domains.add(scored['test'].get('domain', 'Unknown'))
        
        # Infer gap characteristics from closest test
        gap_domain = closest_test.get('domain', 'Unknown')
        
        # Generate suggested test ID
        digest = hashlib.sha256(closest_test['id'].encode('utf-8')).hexdigest()
        suggested_id = f"XRAY-{9000 + int(digest[:8], 16) % 1000}"
        
        # Infer test characteristics based on gap
        preconditions = f"{gap_domain} environment active"
        expected_result = f"Feature performs correctly per {gap_domain} specification"
        
        gap_reason = (
            f"No existing test text matched the change (max text similarity: {max_sim:.2f}). "
            f"The closest test is in {gap_domain}; review the affected functionality."
        )
        
        gap_ticket = XrayGapTicket(
            suggested_id=suggested_id,
            title=f"[AUTO-GAP] {gap_domain}: Regression Coverage",
            domain=gap_domain,
            preconditions=preconditions,
            test_steps=[
                "Setup test environment for affected domain",
                "Execute core functionality paths",
                "Verify expected behavior",
                "Confirm no regressions from PR changes"
            ],
            expected_result=expected_result,
            hil_bench_tags=[d.replace('_', '') for d in sorted(domains)[:3]],
            gap_reason=gap_reason,
            similarity_max=max_sim,
            affected_domains=sorted(list(domains))
        )
        
        return gap_ticket
    
    def _generate_summary(
        self,
        high_risk: List[RankedTest],
        medium_risk: List[RankedTest],
        full_time: int,
        selected_time: int,
        gaps: List[XrayGapTicket],
        visual_used: bool = False,
    ) -> str:
        """Generate execution summary."""
        total_selected = len(high_risk) + len(medium_risk)
        time_saved_pct = int(100 * (full_time - selected_time) / full_time) if full_time > 0 else 0
        
        warning = (
            "\nWARNING: No tests selected; this is not evidence that regression testing can be skipped.\n"
            if total_selected == 0 else ""
        )
        medium_criterion = f"{self.MEDIUM_RISK_THRESHOLD:g}-{self.HIGH_RISK_THRESHOLD:g}"
        if visual_used:
            medium_criterion += " text or qualifying visual match"
        summary = f"""
RISK-BASED TEST SELECTION REPORT
{'='*60}

EXECUTION SUMMARY:
- Selected Tests: {total_selected} / {len(self.test_catalog)}
- HIGH RISK (≥{self.HIGH_RISK_THRESHOLD:g}): {len(high_risk)} tests
- MEDIUM RISK ({medium_criterion}): {len(medium_risk)} tests
{warning}

HIL BENCH TIME PROJECTION:
- Full Suite: {full_time}s ({full_time/3600:.1f}h)
- Selected: {selected_time}s ({selected_time/3600:.1f}h)
- Time Saved: {full_time - selected_time}s ({time_saved_pct}%)

COVERAGE GAPS DETECTED: {len(gaps)}
{f"- {chr(10).join(g.title for g in gaps[:5])}" if gaps else "- None"}
"""
        return summary
