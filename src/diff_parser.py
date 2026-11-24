"""Git diff parser for extracting semantic changes."""

from dataclasses import dataclass, field
from typing import Optional, List
import re


@dataclass
class FileDiff:
    """Represents changes to a single file."""
    file_path: str
    old_path: Optional[str] = None
    is_addition: bool = False
    is_deletion: bool = False
    is_rename: bool = False
    additions: int = 0
    deletions: int = 0
    changes: List[str] = field(default_factory=list)


@dataclass
class DiffSummary:
    """Summary of all changes in a diff."""
    files: List[FileDiff]
    total_additions: int = 0
    total_deletions: int = 0
    semantic_summary: str = ""
    affected_domains: List[str] = field(default_factory=list)
    
    @property
    def total_changed_lines(self) -> int:
        return self.total_additions + self.total_deletions


class DiffParser:
    """Parses unified Git diffs."""
    
    def __init__(self):
        self.files: List[FileDiff] = []
    
    def parse(self, diff_text: str) -> DiffSummary:
        """
        Parse unified Git diff format.
        
        Args:
            diff_text: Raw unified diff text
            
        Returns:
            DiffSummary with parsed changes
        """
        self.files = []
        lines = diff_text.split('\n')
        
        current_file = None
        additions_count = 0
        deletions_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Detect file header: diff --git a/path b/path
            if line.startswith('diff --git'):
                if current_file is not None:
                    current_file.additions = additions_count
                    current_file.deletions = deletions_count
                    self.files.append(current_file)
                
                # Parse new file
                current_file = self._parse_file_header(line, lines, i)
                additions_count = 0
                deletions_count = 0
                
                if current_file is None:
                    i += 1
                    continue
            
            # Count additions and deletions
            elif current_file is not None:
                if line.startswith('+') and not line.startswith('+++'):
                    additions_count += 1
                    current_file.changes.append(line)
                elif line.startswith('-') and not line.startswith('---'):
                    deletions_count += 1
                    current_file.changes.append(line)
            
            i += 1
        
        # Add last file
        if current_file is not None:
            current_file.additions = additions_count
            current_file.deletions = deletions_count
            self.files.append(current_file)
        
        return self._create_summary()
    
    def _parse_file_header(self, diff_line: str, lines: List[str], line_index: int) -> Optional[FileDiff]:
        """Extract file path and metadata from diff header."""
        # Format: diff --git a/path b/path
        match = re.match(r'diff --git a/(.*) b/(.*)', diff_line)
        if not match:
            return None
        
        old_path = match.group(1)
        new_path = match.group(2)
        
        file_diff = FileDiff(file_path=new_path, old_path=old_path)
        
        # Check next lines for file status
        for j in range(line_index + 1, min(line_index + 5, len(lines))):
            next_line = lines[j]
            if next_line.startswith('new file mode'):
                file_diff.is_addition = True
            elif next_line.startswith('deleted file mode'):
                file_diff.is_deletion = True
            elif next_line.startswith('similarity') or next_line.startswith('rename'):
                file_diff.is_rename = True
            elif next_line.startswith('---') or next_line.startswith('+++'):
                break
        
        return file_diff
    
    def _create_summary(self) -> DiffSummary:
        """Create a summary of all changes."""
        total_adds = sum(f.additions for f in self.files)
        total_dels = sum(f.deletions for f in self.files)
        
        # Extract semantic information from file paths and changes
        affected_domains = self._extract_domains()
        semantic = self._generate_semantic_summary()
        
        return DiffSummary(
            files=self.files,
            total_additions=total_adds,
            total_deletions=total_dels,
            semantic_summary=semantic,
            affected_domains=affected_domains
        )
    
    def _extract_domains(self) -> List[str]:
        """Extract automotive domains from file paths."""
        domains = set()
        domain_patterns = {
            'speedometer': ['speedometer', 'cluster', '0x1a4', 'speed'],
            'someip': ['someip', 'sd', 'discovery', 'ttl_timer'],
            'canfd': ['can', 'gateway', 'frame', '0x1f4'],
            'aaos': ['aaos', 'media', 'navigation', 'bluetooth', 'call'],
            'uds': ['uds', 'diagnostic', 'session', 'routine'],
            'localization': ['localization', 'cluster_de', 'cluster_jp', 'xml', 'lang', 'kanji'],
        }
        
        all_text = ' '.join([f.file_path for f in self.files] + 
                            [' '.join(c for c in f.changes) for f in self.files])
        all_text = all_text.lower()
        
        for domain, keywords in domain_patterns.items():
            if any(kw in all_text for kw in keywords):
                domains.add(domain)
        
        return sorted(list(domains))
    
    def _generate_semantic_summary(self) -> str:
        """Generate semantic summary of changes."""
        summaries = []
        
        for file_diff in self.files:
            if file_diff.is_addition:
                summaries.append(f"New file: {file_diff.file_path}")
            elif file_diff.is_deletion:
                summaries.append(f"Deleted: {file_diff.file_path}")
            elif file_diff.is_rename:
                summaries.append(f"Renamed: {file_diff.old_path} → {file_diff.file_path}")
            else:
                summaries.append(f"Modified: {file_diff.file_path} (+{file_diff.additions} -{file_diff.deletions})")
            if file_diff.changes:
                # Bound long diffs to avoid overwhelming the embedding model.
                changes = "; ".join(change[:200] for change in file_diff.changes[:8])
                summaries.append(f"Changes in {file_diff.file_path}: {changes}")
        
        return "; ".join(summaries[:20])


def parse_diff(diff_text: str) -> DiffSummary:
    """Convenience function to parse a diff."""
    parser = DiffParser()
    return parser.parse(diff_text)
