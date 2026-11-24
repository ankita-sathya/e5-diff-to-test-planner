"""
Load sample test cases, defects, and software release metadata into the databases.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

from src import database

logger = logging.getLogger(__name__)


class DataLoader:
    """Load sample data into project databases."""

    def __init__(self):
        self.base_path = Path(__file__).parent.parent / 'data'

    def load_test_catalog(self, catalog_file: str = 'sample_test_catalog.json') -> int:
        """Load test cases from catalog JSON into tests database.
        
        Args:
            catalog_file: Path to test catalog JSON file
            
        Returns:
            Number of test cases loaded
        """
        catalog_path = self.base_path / catalog_file
        if not catalog_path.exists():
            raise FileNotFoundError(f"Test catalog not found: {catalog_path}")
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        loaded_count = 0
        for test_case in test_cases:
            if database.get_test_case(test_case['id']) is not None:
                continue
            try:
                # Add or update test case in database
                success = database.add_test_case(
                    test_id=test_case['id'],
                    test_data={
                        'title': test_case['title'],
                        'domain': test_case['domain'],
                        'preconditions': test_case.get('preconditions', ''),
                        'steps': test_case.get('steps', []),
                        'expected_result': test_case.get('expected_result', ''),
                        'hil_bench_tags': test_case.get('hil_bench_tags', []),
                        'estimated_duration_seconds': test_case.get('estimated_duration_seconds', 60),
                        'languages_tested': test_case.get('languages_tested', [])
                    }
                )
                if not success:
                    raise RuntimeError(f"Failed to load test case {test_case['id']}")
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load test case {test_case.get('id')}: {e}")
                raise
        
        logger.info(f"Loaded {loaded_count} test cases from {catalog_file}")
        return loaded_count

    def load_sample_defects(self) -> int:
        """Load sample defects into defects database."""
        defects_data = [
            {
                "id": "BUG-4001",
                "title": "Speedometer scaling incorrect at 100 km/h",
                "description": "Cluster speedometer displays 102 km/h when receiving CAN frame 0x1A4 with payload [0x00, 0x64, 0x00, 0x00]. Affects CAN-FD signal processing.",
                "severity": "HIGH",
                "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
                "affected_versions": ["v2.3", "v2.4"]
            },
            {
                "id": "BUG-4092",
                "title": "Japanese kanji truncation on curved cockpit navigation banner during incoming call",
                "description": "When displaying 'コンビニエンスストア' (convenience store) on the curved cluster panel during an incoming call, the kanji characters are clipped at the edges. Cluster firmware v2.3+. Rendering artifacts visible on character boundaries.",
                "severity": "CRITICAL",
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "affected_versions": ["v2.3"]
            },
            {
                "id": "BUG-4093",
                "title": "German Umlauts render as boxes in Fahrenheit mode",
                "description": "When switching HMI to Deutsch language and displaying 'Temperaturanzeige', the umlauts (ä, ö, ü) render as placeholder boxes in the digital cluster.",
                "severity": "HIGH",
                "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "affected_versions": ["v2.2", "v2.3"]
            },
            {
                "id": "BUG-4094",
                "title": "SOME/IP service discovery timeout in crowded WiFi environments",
                "description": "SOME/IP-SD protocol fails to discover media services when WiFi signal strength is low (<-70 dBm). TTL timer expires before service response received. Affects infotainment media app connectivity.",
                "severity": "MEDIUM",
                "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
                "affected_versions": ["v3.1", "v3.2"]
            },
            {
                "id": "BUG-4095",
                "title": "CAN-FD frame flooding in gateway causes diagnostic read timeout",
                "description": "When CAN-FD gateway receives >500 frames/sec, UDS (ISO 14229) diagnostic read requests timeout. Affects OBD scanner and diagnostics functionality.",
                "severity": "HIGH",
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "affected_versions": ["v2.3"]
            },
            {
                "id": "BUG-4096",
                "title": "Bluetooth pairing fails during active cellular call",
                "description": "When device is on an active cellular call, Bluetooth pairing attempts fail with connection timeout. Connectivity stack prioritization issue.",
                "severity": "MEDIUM",
                "created_at": (datetime.now() - timedelta(days=4)).isoformat(),
                "affected_versions": ["v3.0", "v3.1"]
            },
            {
                "id": "BUG-4097",
                "title": "ADAS lane detection fails on curved mountain roads",
                "description": "Lane departure warning and lane keep assist trigger false positives on roads with radius <200m. Camera calibration or algorithm issue affecting safety-critical ADAS functionality.",
                "severity": "CRITICAL",
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "affected_versions": ["v2.4"]
            },
            {
                "id": "BUG-4098",
                "title": "Radio tuning slider jitters at extremes (FM 87.5 / 108.0 MHz)",
                "description": "Media app radio tuning slider exhibits visual jitter when user drags to FM band extremes. UI rendering synchronization issue.",
                "severity": "LOW",
                "created_at": (datetime.now() - timedelta(days=6)).isoformat(),
                "affected_versions": ["v3.1"]
            },
            {
                "id": "BUG-4099",
                "title": "Navigation route preview crashes on >5000 waypoint routes",
                "description": "Infotainment navigation app crashes when rendering routes with more than 5000 waypoints. Memory allocation or rendering pipeline issue.",
                "severity": "HIGH",
                "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
                "affected_versions": ["v3.2"]
            },
            {
                "id": "BUG-4100",
                "title": "Adaptive cruise control oscillates at steady-state 80 km/h",
                "description": "Adaptive cruise control exhibits hunting behavior (±2 km/h oscillation) when maintaining steady-state speed. PID controller tuning issue in ADAS.",
                "severity": "MEDIUM",
                "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "affected_versions": ["v2.4"]
            },
        ]

        loaded_count = 0
        for defect in defects_data:
            if database.get_defect(defect['id']) is not None:
                continue
            try:
                success = database.add_defect(
                    defect_id=defect['id'],
                    defect_data={
                        'title': defect['title'],
                        'description': defect['description'],
                        'severity': defect['severity'],
                        'created_at': defect['created_at'],
                        'affected_app_versions': defect['affected_versions']
                    }
                )
                if not success:
                    raise RuntimeError(f"Failed to load defect {defect['id']}")
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load defect {defect.get('id')}: {e}")
                raise
        
        logger.info(f"Loaded {loaded_count} sample defects")
        return loaded_count

    def load_software_releases(self) -> int:
        """Load software release metadata."""
        software_data = [
            {
                "id": "cluster",
                "latest_version": "v2.4",
                "versions": ["v2.0", "v2.1", "v2.2", "v2.3", "v2.4"],
            },
            {
                "id": "infotainment",
                "latest_version": "v3.2",
                "versions": ["v2.8", "v2.9", "v3.0", "v3.1", "v3.2"],
            },
            {
                "id": "adas",
                "latest_version": "v2.4",
                "versions": ["v1.8", "v1.9", "v2.0", "v2.1", "v2.2", "v2.3", "v2.4"],
            },
            {
                "id": "diagnostics",
                "latest_version": "v1.5",
                "versions": ["v1.0", "v1.1", "v1.2", "v1.3", "v1.4", "v1.5"],
            },
            {
                "id": "connectivity",
                "latest_version": "v3.1",
                "versions": ["v2.8", "v2.9", "v3.0", "v3.1"],
            },
        ]

        loaded_count = 0
        for software in software_data:
            for version in software['versions']:
                if database.get_release_info(software['id'], version) is not None:
                    continue
                if not database.add_software_release(software['id'], {'version': version}):
                    raise RuntimeError(f"Failed to load release {software['id']} {version}")
                loaded_count += 1
        
        logger.info(f"Loaded {loaded_count} software releases")
        return loaded_count

    def load_all(self) -> Dict[str, int]:
        """Load all sample data.
        
        Returns:
            Dictionary with counts: {'test_cases': N, 'defects': N, 'software': N}
        """
        result = {
            'test_cases': self.load_test_catalog(),
            'defects': self.load_sample_defects(),
            'software': self.load_software_releases(),
        }
        
        logger.info(
            f"Data loading complete: {result['test_cases']} test cases, "
            f"{result['defects']} defects, {result['software']} software releases"
        )
        
        return result


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    database.init_databases()
    loader = DataLoader()
    results = loader.load_all()
    
    print(f"\n✓ Data loading complete:")
    print(f"  • {results['test_cases']} test cases loaded")
    print(f"  • {results['defects']} defects loaded")
    print(f"  • {results['software']} software releases loaded")
