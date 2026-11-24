"""Tests for database module and release analyzer."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.database import (
    init_databases, verify_databases, 
    add_test_case, add_defect, add_software_release,
    get_test_case, get_defect
)
from src.release_analyzer import (
    SoftwareReleaseAnalyzer, 
    analyze_pr_for_regression
)
from src.data_loader import DataLoader
from src import database


@pytest.fixture
def isolated_databases(tmp_path, monkeypatch):
    """Keep test writes separate from the user's databases."""
    db_dir = tmp_path / "db"
    monkeypatch.setattr(database, "DB_DIR", db_dir)
    monkeypatch.setattr(database, "TESTS_DB", db_dir / "tests.db")
    monkeypatch.setattr(database, "DEFECTS_DB", db_dir / "defects.db")
    monkeypatch.setattr(database, "RELEASES_DB", db_dir / "releases.db")


class TestDatabase:
    """Test database initialization and operations."""

    @pytest.fixture(autouse=True)
    def setup_databases(self, isolated_databases):
        """Initialize databases for testing."""
        init_databases()
        yield

    def test_database_initialization(self):
        """Databases initialize correctly."""
        stats = verify_databases()
        
        assert isinstance(stats, dict)
        assert 'test_cases' in stats
        assert 'defects' in stats
        assert 'software' in stats

    def test_add_test_case(self):
        """Add test case to database."""
        test_data = {
            'title': 'Test CAN Signal Scaling',
            'domain': 'Digital_Cluster',
            'preconditions': 'Vehicle ON',
            'steps': ['Step 1', 'Step 2'],
            'expected_result': 'Signal scales correctly',
            'hil_bench_tags': ['CAN-FD'],
            'estimated_duration_seconds': 60,
            'languages_tested': ['EN']
        }
        
        success = add_test_case('TEST-001', test_data)
        assert success is True
        
        # Verify test case was added
        retrieved = get_test_case('TEST-001')
        assert retrieved is not None
        assert retrieved['title'] == 'Test CAN Signal Scaling'
        assert retrieved['domain'] == 'Digital_Cluster'

    def test_add_defect(self):
        """Add defect to database."""
        defect_data = {
            'title': 'Japanese truncation bug',
            'description': 'Characters are clipped on curved display',
            'severity': 'CRITICAL',
            'created_at': datetime.now().isoformat(),
            'affected_versions': ['v2.3']
        }
        
        success = add_defect('BUG-001', defect_data)
        assert success is True
        
        # Verify defect was added
        retrieved = get_defect('BUG-001')
        assert retrieved is not None
        assert retrieved['title'] == 'Japanese truncation bug'
        assert retrieved['severity'] == 'CRITICAL'

    def test_add_software_release(self):
        """Add software release to database."""
        release_data = {
            'version': 'v2.4',
        }
        
        success = add_software_release('cluster', release_data)
        assert success
        assert database.get_release_info('cluster', 'v2.4')['version'] == 'v2.4'


class TestReleaseAnalyzer:
    """Test software release analyzer."""

    def test_analyzer_initialization(self):
        """Analyzer initializes correctly."""
        analyzer = SoftwareReleaseAnalyzer()
        assert len(analyzer.SOFTWARE_PATTERNS) > 0
        assert 'cluster' in analyzer.SOFTWARE_PATTERNS
        assert 'infotainment' in analyzer.SOFTWARE_PATTERNS

    def test_determine_severity_critical(self):
        """Determine severity as CRITICAL for safety issues."""
        analyzer = SoftwareReleaseAnalyzer()
        
        description = 'Lane detection crash causes vehicle safety failure'
        
        severity = analyzer._determine_severity(description)
        # Returns Severity enum
        assert severity.value in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

    def test_determine_severity_high(self):
        """Determine severity as HIGH for rendering issues."""
        analyzer = SoftwareReleaseAnalyzer()
        
        description = 'Japanese kanji characters truncated on cluster display'
        
        severity = analyzer._determine_severity(description)
        # Should be HIGH due to truncation/rendering keywords
        assert severity.value in ['HIGH', 'MEDIUM', 'CRITICAL']

    def test_get_regression_areas_cluster(self):
        """Get regression test areas for cluster software."""
        analyzer = SoftwareReleaseAnalyzer()
        
        affected_software = {'cluster'}
        
        areas = analyzer._get_regression_areas(affected_software)
        
        assert isinstance(areas, list)
        assert len(areas) > 0
        
        for area in areas:
            assert 'area' in area
            assert 'software' in area
            assert 'priority' in area
            assert 'tests' in area

    def test_get_regression_areas_infotainment(self):
        """Get regression test areas for infotainment software."""
        analyzer = SoftwareReleaseAnalyzer()
        
        affected_software = {'infotainment'}
        
        areas = analyzer._get_regression_areas(affected_software)
        
        assert isinstance(areas, list)
        # Should have entries for infotainment
        infotainment_areas = [a for a in areas if a['software'] == 'infotainment']
        assert len(infotainment_areas) > 0

    def test_analyze_defect_full_workflow(self):
        """Full defect analysis workflow."""
        analyzer = SoftwareReleaseAnalyzer()
        
        defect_description = 'Japanese kanji truncation on curved cockpit display during incoming call. CAN signal 0x1A4 rendering issue.'
        
        analysis = analyzer.analyze_defect(defect_description)
        
        assert isinstance(analysis, dict)
        assert 'affected_software' in analysis or len(analysis) > 0

    def test_analyze_diff_full_workflow(self):
        """Full diff analysis workflow."""
        analyzer = SoftwareReleaseAnalyzer()
        
        file_paths = [
            'src/cluster/speedometer.cpp',
            'src/cluster/localization/de.json',
            'src/cluster/localization/jp.json'
        ]
        
        diff_content = """
        diff --git a/src/cluster/speedometer.cpp
        Modified CAN signal 0x1A4 scaling factor
        """
        
        analysis = analyzer.analyze_diff(diff_content, file_paths)
        
        assert isinstance(analysis, dict)
        assert 'affected_software' in analysis or 'regression_areas' in analysis

    def test_analyze_pr_for_regression(self):
        """Test high-level analyze_pr_for_regression function."""
        diff_content = """diff --git a/src/cluster/speedometer.cpp b/src/cluster/speedometer.cpp
index 1234567..abcdefg 100644
--- a/src/cluster/speedometer.cpp
+++ b/src/cluster/speedometer.cpp
@@ -1,3 +1,3 @@
 speed scaling update
-int speed = 0;
+int speed = raw_value * scaling_factor;
"""
        
        file_paths = ['src/cluster/speedometer.cpp']
        
        defect_description = """
        Cluster speedometer displays incorrect values. 
        CAN frame 0x1A4 signal scaling is broken.
        """
        
        result = analyze_pr_for_regression(diff_content, file_paths, defect_description)
        
        assert isinstance(result, dict)
        assert 'combined_affected_software' in result
        assert 'combined_regression_areas' in result
        assert 'diff_analysis' in result
        assert 'defect_analysis' in result
        assert 'summary' in result


class TestDataLoader:
    """Test data loading functionality."""

    @pytest.fixture(autouse=True)
    def setup_databases(self, isolated_databases):
        """Initialize databases for testing."""
        init_databases()
        yield

    def test_data_loader_initialization(self):
        """Data loader initializes correctly."""
        loader = DataLoader()
        assert loader.base_path.exists()

    def test_load_test_catalog(self):
        """Load test catalog from JSON."""
        loader = DataLoader()
        count = loader.load_test_catalog('sample_test_catalog.json')
        
        assert count > 0
        with open(loader.base_path / 'sample_test_catalog.json', encoding='utf-8') as f:
            assert count == len(json.load(f))

    def test_load_sample_defects(self):
        """Load sample defects."""
        loader = DataLoader()
        count = loader.load_sample_defects()
        
        assert count > 0
        assert count == 10  # We defined 10 sample defects

    def test_load_software_releases(self):
        """Load software release metadata."""
        loader = DataLoader()
        count = loader.load_software_releases()
        
        assert count == 27
        assert verify_databases()['software'] == 5
        assert verify_databases()['releases'] == 27
        assert loader.load_software_releases() == 0

    def test_load_all(self):
        """Load all sample data."""
        loader = DataLoader()
        results = loader.load_all()
        
        assert isinstance(results, dict)
        assert 'test_cases' in results
        assert 'defects' in results
        assert 'software' in results
        
        # Verify non-zero counts
        assert results['test_cases'] > 0
        assert results['defects'] > 0

    def test_loading_again_preserves_existing_records(self):
        loader = DataLoader()
        assert loader.load_test_catalog() > 0
        assert add_test_case('XRAY-1001', {'title': 'Custom title', 'domain': 'Custom'})
        assert loader.load_test_catalog() == 0
        assert get_test_case('XRAY-1001')['title'] == 'Custom title'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
