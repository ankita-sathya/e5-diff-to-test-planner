"""
Software Release Analyzer

Analyzes defects and diffs to determine:
- Which software/apps are affected
- Which versions are relevant
- Which functionality is impacted
- Where regression testing is needed
"""

import re
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RegressionRisk(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class AffectedComponent:
    """Represents an affected software component."""
    software_id: str
    software_name: str
    app_versions: List[str]
    functionality: List[str]
    modules: List[str]
    regression_risk: RegressionRisk
    impact_description: str


@dataclass
class RegressionTestArea:
    """Represents an area requiring regression testing."""
    area_name: str
    functionality: str
    priority: str
    suggested_tests: List[str]
    risk_level: str


class SoftwareReleaseAnalyzer:
    """
    Analyzes defects and diffs to determine software/version relevance
    and regression testing requirements.
    """
    
    # Software identification patterns
    SOFTWARE_PATTERNS = {
        'cluster': {
            'names': ['cluster', 'gauge', 'instrument', 'dashboard'],
            'modules': ['cluster_display', 'gauge_control', 'rendering'],
            'versions': ['v2.1', 'v2.2', 'v2.3', 'v2.4', 'v3.0'],
        },
        'infotainment': {
            'names': ['media', 'radio', 'music', 'player', 'navigation', 'navi', 'map'],
            'modules': ['media_player', 'radio_tuner', 'navigation_engine'],
            'versions': ['v1.5', 'v1.6', 'v2.0', 'v2.1'],
        },
        'adas': {
            'names': ['cruise', 'lane', 'collision', 'adaptive', 'adas', 'autonomous'],
            'modules': ['cruise_control', 'lane_keeping', 'collision_detection'],
            'versions': ['v3.0', 'v3.1', 'v4.0'],
        },
        'diagnostics': {
            'names': ['obd', 'diagnostic', 'scanner', 'service', 'dtc', 'error_code'],
            'modules': ['obd2', 'scanner', 'service_reminder'],
            'versions': ['v1.0', 'v1.1', 'v1.2'],
        },
        'connectivity': {
            'names': ['bluetooth', 'wifi', 'cellular', 'gsm', 'network', 'connection'],
            'modules': ['bluetooth_stack', 'wifi_driver', 'modem'],
            'versions': ['v5.0', 'v5.1', 'v6.0'],
        },
    }
    
    # Functionality mapping
    FUNCTIONALITY_MAP = {
        'cluster': [
            'Speedometer Display',
            'Fuel Gauge',
            'RPM Meter',
            'Temperature Display',
            'Digital Cluster Rendering',
            'Localization (DE, JP, EN)',
        ],
        'infotainment': [
            'Media Playback',
            'Radio Tuning',
            'Navigation',
            'Voice Control',
            'Bluetooth Audio',
            'USB Media',
        ],
        'adas': [
            'Adaptive Cruise Control',
            'Lane Keeping Assist',
            'Collision Detection',
            'Emergency Braking',
            'Speed Governor',
        ],
        'diagnostics': [
            'OBD-II Scanning',
            'Error Code Handling',
            'Service Reminders',
            'Performance Monitoring',
        ],
        'connectivity': [
            'Bluetooth Pairing',
            'WiFi Connection',
            'Cellular Connectivity',
            'OTA Updates',
        ],
    }
    
    # Regression test recommendations
    REGRESSION_TEST_AREAS = {
        'cluster': [
            {
                'area': 'Digital Cluster Display',
                'tests': [
                    'Speedometer precision test',
                    'Fuel gauge accuracy test',
                    'RPM meter range test',
                    'Display rendering test (curved display)',
                    'Multilingual character rendering (DE, JP)',
                ],
                'priority': 'CRITICAL',
            },
            {
                'area': 'CAN Message Handling',
                'tests': [
                    'CAN-FD frame parsing',
                    'Signal scaling validation',
                    '0x1A4 frame processing',
                ],
                'priority': 'HIGH',
            },
            {
                'area': 'Localization',
                'tests': [
                    'German umlauts rendering',
                    'Japanese kanji rendering',
                    'Text truncation detection',
                ],
                'priority': 'HIGH',
            },
        ],
        'infotainment': [
            {
                'area': 'Media Player',
                'tests': [
                    'Play/Pause functionality',
                    'Shuffle/Repeat modes',
                    'Volume control',
                    'Seek functionality',
                ],
                'priority': 'HIGH',
            },
            {
                'area': 'Radio Tuning',
                'tests': [
                    'FM frequency tuning',
                    'AM frequency tuning',
                    'Station preset storage',
                    'Signal strength detection',
                ],
                'priority': 'MEDIUM',
            },
            {
                'area': 'Navigation',
                'tests': [
                    'Route calculation',
                    'GPS accuracy',
                    'Map rendering',
                    'Voice guidance',
                ],
                'priority': 'HIGH',
            },
        ],
        'adas': [
            {
                'area': 'Cruise Control',
                'tests': [
                    'Acceleration profile',
                    'Deceleration smoothness',
                    'Speed governor enforcement',
                ],
                'priority': 'CRITICAL',
            },
            {
                'area': 'Safety Systems',
                'tests': [
                    'Collision detection accuracy',
                    'Emergency braking response',
                    'Lane keeping assist activation',
                ],
                'priority': 'CRITICAL',
            },
        ],
    }
    
    def analyze_defect(self, defect_description: str, defect_title: str = "") -> Dict:
        """Analyze a defect to determine affected software/versions."""
        
        full_text = f"{defect_title} {defect_description}".lower()
        
        affected_components = []
        affected_software = set()
        affected_functionality = set()
        
        # Identify affected software
        for software_id, patterns in self.SOFTWARE_PATTERNS.items():
            for pattern in patterns['names']:
                if re.search(rf'\b{pattern}\b', full_text):
                    affected_software.add(software_id)
                    
                    # Identify specific functionality
                    for func in self.FUNCTIONALITY_MAP.get(software_id, []):
                        func_lower = func.lower()
                        if any(kw in full_text for kw in func_lower.split()):
                            affected_functionality.add(func)
                    break
        
        # Determine version relevance
        versions_affected = self._determine_versions(full_text, affected_software)
        
        # Determine regression test areas
        regression_areas = self._get_regression_areas(affected_software)
        
        # Determine severity and risk
        severity = self._determine_severity(defect_description)
        risk_level = self._determine_risk_level(severity, affected_software)
        
        return {
            'affected_software': list(affected_software),
            'affected_versions': versions_affected,
            'affected_functionality': list(affected_functionality),
            'regression_areas': regression_areas,
            'severity': severity.value,
            'regression_risk': risk_level.value,
            'modules_affected': self._get_affected_modules(affected_software),
            'regression_testing_needed': len(regression_areas) > 0,
        }
    
    def analyze_diff(self, diff_content: str, file_paths: List[str] = None) -> Dict:
        """Analyze a Git diff to determine software relevance."""
        
        affected_software = set()
        affected_modules = set()
        
        # Analyze file paths
        if file_paths:
            for filepath in file_paths:
                filepath_lower = filepath.lower()
                
                for software_id, patterns in self.SOFTWARE_PATTERNS.items():
                    for module in patterns['modules']:
                        if module in filepath_lower:
                            affected_software.add(software_id)
                            affected_modules.add(module)
        
        # Analyze diff content
        diff_lower = diff_content.lower()
        keywords_found = {}
        
        for software_id, patterns in self.SOFTWARE_PATTERNS.items():
            matches = 0
            for keyword in patterns['names'] + patterns['modules']:
                if keyword in diff_lower:
                    matches += 1
            
            if matches > 0:
                keywords_found[software_id] = matches
        
        # Sort by relevance
        sorted_software = sorted(
            keywords_found.items(),
            key=lambda x: x[1],
            reverse=True
        )
        affected_software.update([s[0] for s in sorted_software])
        
        # Determine recommended test areas
        regression_areas = self._get_regression_areas(affected_software)
        
        return {
            'affected_software': list(affected_software),
            'affected_modules': list(affected_modules),
            'regression_areas': regression_areas,
            'modules_affected': self._get_affected_modules(affected_software),
            'change_complexity': self._assess_complexity(diff_content),
        }
    
    def _determine_versions(self, text: str, software_ids: Set[str]) -> Dict[str, List[str]]:
        """Determine which versions are affected."""
        versions = {}
        
        for software_id in software_ids:
            software_versions = self.SOFTWARE_PATTERNS[software_id]['versions']
            affected_versions = []
            
            for version in software_versions:
                # Check if version is mentioned in text
                if version.lower() in text or version in text:
                    affected_versions.append(version)
            
            # If no specific versions mentioned, return all versions as potentially affected
            if not affected_versions:
                affected_versions = software_versions
            
            versions[software_id] = affected_versions
        
        return versions
    
    def _determine_severity(self, description: str) -> Severity:
        """Determine defect severity from description."""
        desc_lower = description.lower()
        
        # Critical keywords
        critical_keywords = ['crash', 'fatal', 'safety', 'emergency', 'collision', 'braking']
        if any(kw in desc_lower for kw in critical_keywords):
            return Severity.CRITICAL
        
        # High keywords
        high_keywords = ['truncation', 'rendering', 'display', 'missing', 'corrupted']
        if any(kw in desc_lower for kw in high_keywords):
            return Severity.HIGH
        
        # Medium keywords
        medium_keywords = ['ui', 'button', 'offset', 'incorrect', 'wrong']
        if any(kw in desc_lower for kw in medium_keywords):
            return Severity.MEDIUM
        
        return Severity.LOW
    
    def _determine_risk_level(self, severity: Severity, software_ids: Set[str]) -> RegressionRisk:
        """Determine regression testing risk level."""
        
        # Safety-critical software requires higher risk
        safety_critical = {'adas', 'diagnostics'}
        if any(s in safety_critical for s in software_ids):
            if severity == Severity.CRITICAL:
                return RegressionRisk.CRITICAL
            elif severity == Severity.HIGH:
                return RegressionRisk.HIGH
        
        # Map severity to risk
        severity_to_risk = {
            Severity.CRITICAL: RegressionRisk.CRITICAL,
            Severity.HIGH: RegressionRisk.HIGH,
            Severity.MEDIUM: RegressionRisk.MEDIUM,
            Severity.LOW: RegressionRisk.LOW,
        }
        
        return severity_to_risk.get(severity, RegressionRisk.MEDIUM)
    
    def _get_regression_areas(self, software_ids: Set[str]) -> List[Dict]:
        """Get regression testing areas for affected software."""
        areas = []
        
        for software_id in software_ids:
            software_areas = self.REGRESSION_TEST_AREAS.get(software_id, [])
            for area in software_areas:
                areas.append({
                    'software': software_id,
                    'area': area['area'],
                    'tests': area['tests'],
                    'priority': area['priority'],
                })
        
        # Sort by priority
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        areas.sort(key=lambda x: priority_order.get(x['priority'], 999))
        
        return areas
    
    def _get_affected_modules(self, software_ids: Set[str]) -> List[str]:
        """Get affected modules for software."""
        modules = []
        
        for software_id in software_ids:
            modules.extend(self.SOFTWARE_PATTERNS[software_id]['modules'])
        
        return list(set(modules))
    
    def _assess_complexity(self, diff_content: str) -> str:
        """Assess change complexity from diff."""
        lines = len(diff_content.split('\n'))
        
        if lines > 500:
            return 'HIGH'
        elif lines > 200:
            return 'MEDIUM'
        else:
            return 'LOW'


def analyze_pr_for_regression(diff_content: str, file_paths: List[str], 
                             defect_description: str = None) -> Dict:
    """
    Comprehensive analysis for PR to determine:
    - Affected software/versions
    - Regression testing requirements
    - Software release compatibility
    """
    analyzer = SoftwareReleaseAnalyzer()
    
    # Analyze diff
    diff_analysis = analyzer.analyze_diff(diff_content, file_paths)
    
    # Analyze defect if provided
    defect_analysis = None
    if defect_description:
        defect_analysis = analyzer.analyze_defect(defect_description)
    
    # Merge analyses
    all_software = set(diff_analysis.get('affected_software', []))
    if defect_analysis:
        all_software.update(defect_analysis.get('affected_software', []))
    
    return {
        'diff_analysis': diff_analysis,
        'defect_analysis': defect_analysis,
        'combined_affected_software': list(all_software),
        'combined_regression_areas': diff_analysis.get('regression_areas', []),
        'summary': {
            'software_count': len(all_software),
            'regression_areas_count': len(diff_analysis.get('regression_areas', [])),
            'requires_extensive_regression': len(diff_analysis.get('regression_areas', [])) > 3,
        }
    }


if __name__ == '__main__':
    # Test
    analyzer = SoftwareReleaseAnalyzer()
    
    test_defect = "Japanese kanji truncation on curved cockpit navigation banner during incoming call"
    result = analyzer.analyze_defect(test_defect)
    
    print("Defect Analysis Result:")
    print(f"  Affected Software: {result['affected_software']}")
    print(f"  Affected Functionality: {result['affected_functionality']}")
    print(f"  Regression Risk: {result['regression_risk']}")
    print(f"  Test Areas: {len(result['regression_areas'])}")
