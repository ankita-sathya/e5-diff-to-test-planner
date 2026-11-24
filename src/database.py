"""
E5 Diff-to-Test Planner - Database Module

Manages SQLite databases for:
- Test cases and test runs
- Defects and defect tracking
- Software releases and versions
- Regression test recommendations
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

DB_DIR = Path("data/db")
TESTS_DB = DB_DIR / "tests.db"
DEFECTS_DB = DB_DIR / "defects.db"
RELEASES_DB = DB_DIR / "releases.db"


def init_databases():
    """Initialize all databases with schema."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    _init_tests_db()
    _init_defects_db()
    _init_releases_db()
    
    print(f"✓ Databases initialized in {DB_DIR}")


def _init_tests_db():
    """Initialize tests database."""
    conn = sqlite3.connect(TESTS_DB)
    c = conn.cursor()
    
    # Test cases table
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            domain TEXT NOT NULL,
            description TEXT,
            preconditions TEXT,
            steps JSON,
            expected_result TEXT,
            estimated_duration_seconds INTEGER,
            hil_bench_tags JSON,
            languages_tested JSON,
            relevant_software_ids JSON,
            relevant_app_versions JSON,
            regression_areas JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Test runs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_runs (
            id TEXT PRIMARY KEY,
            test_case_id TEXT NOT NULL,
            pr_diff_id TEXT,
            defect_id TEXT,
            status TEXT,
            risk_level TEXT,
            similarity_score REAL,
            duration_seconds INTEGER,
            result TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(test_case_id) REFERENCES test_cases(id)
        )
    ''')
    
    # Test domains table
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_domains (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            software_ids JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def _init_defects_db():
    """Initialize defects database."""
    conn = sqlite3.connect(DEFECTS_DB)
    c = conn.cursor()
    
    # Defects table
    c.execute('''
        CREATE TABLE IF NOT EXISTS defects (
            id TEXT PRIMARY KEY,
            jira_id TEXT UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT,
            status TEXT,
            affected_software_ids JSON,
            affected_app_versions JSON,
            affected_functionality JSON,
            root_cause TEXT,
            proposed_fix TEXT,
            test_cases_needed JSON,
            regression_areas JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            reporter TEXT,
            assignee TEXT
        )
    ''')
    
    # Defect impacts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS defect_impacts (
            id TEXT PRIMARY KEY,
            defect_id TEXT NOT NULL,
            software_id TEXT NOT NULL,
            app_version TEXT NOT NULL,
            severity TEXT,
            impact_description TEXT,
            regression_risk_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(defect_id) REFERENCES defects(id)
        )
    ''')
    
    # Defect analysis results table
    c.execute('''
        CREATE TABLE IF NOT EXISTS defect_analyses (
            id TEXT PRIMARY KEY,
            defect_id TEXT NOT NULL,
            diff_summary TEXT,
            affected_domains JSON,
            affected_modules JSON,
            confidence_score REAL,
            recommended_tests JSON,
            regression_test_areas JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(defect_id) REFERENCES defects(id)
        )
    ''')
    
    conn.commit()
    conn.close()


def _init_releases_db():
    """Initialize releases database."""
    conn = sqlite3.connect(RELEASES_DB)
    c = conn.cursor()
    
    # Software table
    c.execute('''
        CREATE TABLE IF NOT EXISTS software (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            type TEXT,
            repository_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Software versions/releases table
    c.execute('''
        CREATE TABLE IF NOT EXISTS releases (
            id TEXT PRIMARY KEY,
            software_id TEXT NOT NULL,
            version TEXT NOT NULL,
            app_version TEXT,
            release_date TIMESTAMP,
            status TEXT,
            description TEXT,
            features JSON,
            known_issues JSON,
            dependencies JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(software_id) REFERENCES software(id),
            UNIQUE(software_id, version)
        )
    ''')
    
    # Functionality mapping table
    c.execute('''
        CREATE TABLE IF NOT EXISTS functionality (
            id TEXT PRIMARY KEY,
            software_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            modules JSON,
            affected_releases JSON,
            test_category TEXT,
            regression_priority TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(software_id) REFERENCES software(id)
        )
    ''')
    
    # Release compatibility table
    c.execute('''
        CREATE TABLE IF NOT EXISTS compatibility (
            id TEXT PRIMARY KEY,
            software_id TEXT NOT NULL,
            release_version TEXT NOT NULL,
            compatible_with JSON,
            breaking_changes JSON,
            migration_guide TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(software_id) REFERENCES software(id)
        )
    ''')
    
    conn.commit()
    conn.close()


def add_test_case(test_id: str, test_data: Dict) -> bool:
    """Add a test case to database."""
    try:
        conn = sqlite3.connect(TESTS_DB)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO test_cases (
                id, title, domain, description, preconditions,
                steps, expected_result, estimated_duration_seconds,
                hil_bench_tags, languages_tested,
                relevant_software_ids, relevant_app_versions,
                regression_areas, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_id,
            test_data.get('title'),
            test_data.get('domain'),
            test_data.get('description', ''),
            test_data.get('preconditions', ''),
            json.dumps(test_data.get('steps', [])),
            test_data.get('expected_result', ''),
            test_data.get('estimated_duration_seconds', 0),
            json.dumps(test_data.get('hil_bench_tags', [])),
            json.dumps(test_data.get('languages_tested', [])),
            json.dumps(test_data.get('relevant_software_ids', [])),
            json.dumps(test_data.get('relevant_app_versions', [])),
            json.dumps(test_data.get('regression_areas', [])),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding test case: {e}")
        return False


def add_defect(defect_id: str, defect_data: Dict) -> bool:
    """Add a defect to database."""
    try:
        conn = sqlite3.connect(DEFECTS_DB)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO defects (
                id, jira_id, title, description, severity, status,
                affected_software_ids, affected_app_versions,
                affected_functionality, root_cause, proposed_fix,
                test_cases_needed, regression_areas,
                created_at, updated_at, reporter, assignee
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            defect_id,
            defect_data.get('jira_id'),
            defect_data.get('title'),
            defect_data.get('description', ''),
            defect_data.get('severity', 'MEDIUM'),
            defect_data.get('status', 'OPEN'),
            json.dumps(defect_data.get('affected_software_ids', [])),
            json.dumps(defect_data.get('affected_app_versions', [])),
            json.dumps(defect_data.get('affected_functionality', [])),
            defect_data.get('root_cause', ''),
            defect_data.get('proposed_fix', ''),
            json.dumps(defect_data.get('test_cases_needed', [])),
            json.dumps(defect_data.get('regression_areas', [])),
            defect_data.get('created_at', datetime.now().isoformat()),
            datetime.now().isoformat(),
            defect_data.get('reporter'),
            defect_data.get('assignee')
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding defect: {e}")
        return False


def add_software_release(software_id: str, release_data: Dict) -> bool:
    """Add a software release to database."""
    conn = None
    try:
        conn = sqlite3.connect(RELEASES_DB)
        c = conn.cursor()
        
        # Ensure software exists
        c.execute('SELECT id FROM software WHERE id = ?', (software_id,))
        if not c.fetchone():
            c.execute('INSERT INTO software (id, name) VALUES (?, ?)',
                     (software_id, release_data.get('software_name', software_id)))
        
        # Add release
        c.execute('''
            INSERT OR REPLACE INTO releases (
                id, software_id, version, app_version, release_date,
                status, description, features, known_issues, dependencies
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"{software_id}_{release_data.get('version')}",
            software_id,
            release_data.get('version'),
            release_data.get('app_version'),
            release_data.get('release_date'),
            release_data.get('status', 'ACTIVE'),
            release_data.get('description', ''),
            json.dumps(release_data.get('features', [])),
            json.dumps(release_data.get('known_issues', [])),
            json.dumps(release_data.get('dependencies', []))
        ))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error adding software release: {e}")
        return False
    finally:
        if conn is not None:
            conn.close()


def get_test_case(test_id: str) -> Optional[Dict]:
    """Get a test case from database."""
    try:
        conn = sqlite3.connect(TESTS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM test_cases WHERE id = ?', (test_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Error getting test case: {e}")
        return None


def get_defect(defect_id: str) -> Optional[Dict]:
    """Get a defect from database."""
    try:
        conn = sqlite3.connect(DEFECTS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM defects WHERE id = ?', (defect_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Error getting defect: {e}")
        return None


def search_defects_by_software(software_id: str) -> List[Dict]:
    """Search defects by affected software."""
    try:
        conn = sqlite3.connect(DEFECTS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM defects
            WHERE affected_software_ids LIKE ?
            ORDER BY created_at DESC
        ''', (f'%{software_id}%',))
        
        rows = c.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error searching defects: {e}")
        return []


def get_release_info(software_id: str, version: str) -> Optional[Dict]:
    """Get release information."""
    try:
        conn = sqlite3.connect(RELEASES_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM releases
            WHERE software_id = ? AND version = ?
        ''', (software_id, version))
        
        row = c.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Error getting release info: {e}")
        return None


def verify_databases() -> Dict[str, int]:
    """Verify databases and return statistics."""
    stats = {}
    
    try:
        # Tests DB
        conn = sqlite3.connect(TESTS_DB)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM test_cases')
        stats['test_cases'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM test_runs')
        stats['test_runs'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM test_domains')
        stats['test_domains'] = c.fetchone()[0]
        
        conn.close()
        
        # Defects DB
        conn = sqlite3.connect(DEFECTS_DB)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM defects')
        stats['defects'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM defect_impacts')
        stats['defect_impacts'] = c.fetchone()[0]
        
        conn.close()
        
        # Releases DB
        conn = sqlite3.connect(RELEASES_DB)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM software')
        stats['software'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM releases')
        stats['releases'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM functionality')
        stats['functionality'] = c.fetchone()[0]
        
        conn.close()
        
    except Exception as e:
        print(f"Error verifying databases: {e}")
    
    return stats


if __name__ == '__main__':
    init_databases()
    stats = verify_databases()
    print("\nDatabase Statistics:")
    for table, count in stats.items():
        print(f"  {table}: {count}")
