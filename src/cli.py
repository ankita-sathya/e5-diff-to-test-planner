"""CLI entrypoint for e5-diff-to-test-planner."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from src.embedder import create_embedder
from src.diff_parser import parse_diff
from src.planner import TestPlanner
from src.release_analyzer import analyze_pr_for_regression
from src.visual_evidence import Evidence, SiglipImageEmbedder, extract_git_evidence, resolve_attachments, score_visual_matches


@click.group()
def cli():
    """E5 Diff-to-Test Planner: AI-powered risk-based test selection."""
    pass


@cli.command()
@click.option(
    '--diff',
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help='Path to unified Git diff (.patch) file'
)
@click.option('--git-base', help='Base Git revision to compare with --git-head.')
@click.option('--git-head', default='HEAD', show_default=True, help='Head Git revision.')
@click.option('--git-repo', type=click.Path(exists=True, file_okay=False), default='.',
              show_default=True, help='Local Git repository to compare.')
@click.option(
    '--catalog',
    type=click.Path(exists=True),
    required=True,
    help='Path to test catalog JSON file'
)
@click.option(
    '--defect',
    type=click.Path(exists=True),
    default=None,
    help='Optional Jira defect JSON file'
)
@click.option('--media', type=click.Path(exists=True, dir_okay=False), multiple=True,
              help='Local image or video evidence; repeat for multiple files.')
@click.option('--visual-threshold', type=click.FloatRange(0, 1), default=0.8,
              show_default=True, help='Minimum image-to-image similarity for a visual match.')
@click.option(
    '--output',
    type=click.Path(),
    default='report.json',
    help='Output report JSON file'
)
@click.option(
    '--mock-embeddings',
    is_flag=True,
    default=False,
    help='Use fast mock embedder (no model download)'
)
@click.option('--high-threshold', type=click.FloatRange(0, 1), default=0.78, show_default=True)
@click.option('--medium-threshold', type=click.FloatRange(0, 1), default=0.65, show_default=True)
@click.option('--gap-threshold', type=click.FloatRange(0, 1), default=0.62, show_default=True)
@click.option(
    '--full-suite-time',
    type=int,
    default=28800,
    help='Full suite runtime in seconds (default: 28800 = 8h)'
)
def analyze(
    diff: Optional[str],
    git_base: Optional[str],
    git_head: str,
    git_repo: str,
    catalog: str,
    defect: Optional[str],
    media: tuple[str, ...],
    visual_threshold: float,
    output: str,
    mock_embeddings: bool,
    high_threshold: float,
    medium_threshold: float,
    gap_threshold: float,
    full_suite_time: int
):
    """Analyze PR diff and select high-risk tests."""
    
    click.echo("E5 Diff-to-Test Planner")
    click.echo("=" * 60)
    
    if diff and git_base:
        raise click.UsageError("Provide only one of --diff or --git-base.")
    if not diff and not git_base and not defect:
        raise click.UsageError("Provide a --diff, --git-base or --defect.")
    if git_base and (git_base.startswith('-') or git_head.startswith('-')):
        raise click.UsageError("Git revisions must not start with '-'.")
    if medium_threshold > high_threshold:
        raise click.UsageError("--medium-threshold cannot exceed --high-threshold.")
    if diff:
        click.echo(f"Loading diff: {diff}")
        with open(diff, 'r', encoding='utf-8') as f:
            diff_text = f.read()
    elif git_base:
        click.echo(f"Comparing Git revisions: {git_base}..{git_head}")
        try:
            completed = subprocess.run(
                ['git', '-C', git_repo, 'diff', '--no-ext-diff', '--no-textconv',
                 f'{git_base}..{git_head}', '--'],
                capture_output=True, text=True, encoding='utf-8', check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
            raise click.ClickException(f"Git diff failed: {detail}") from exc
        diff_text = completed.stdout
    else:
        diff_text = ""
    if (diff or git_base) and not diff_text.strip():
        raise click.ClickException("The selected diff is empty.")
    
    diff_summary = parse_diff(diff_text)
    click.echo(f"  Files changed: {len(diff_summary.files)}")
    click.echo(f"  Total lines: +{diff_summary.total_additions} -{diff_summary.total_deletions}")
    click.echo(f"  Domains: {', '.join(diff_summary.affected_domains)}")
    
    # Load defect if provided
    defect_text = ""
    defect_media: list[Evidence] = []
    if defect:
        click.echo(f"\nLoading defect: {defect}")
        with open(defect, 'r', encoding='utf-8') as f:
            defect_data = json.load(f)
            defect_text = f"{defect_data.get('summary', '')} {defect_data.get('description', '')}".strip()
            try:
                defect_media = resolve_attachments(defect_data.get('attachments'), Path(defect).resolve().parent, 'defect')
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc
            click.echo(f"  ID: {defect_data.get('id')}")
            click.echo(f"  Summary: {defect_data.get('summary')}")
    
    # Initialize embedder
    click.echo(f"\nInitializing embedder...")
    if mock_embeddings:
        click.echo("  Using MOCK embedder (deterministic, no model download)")
    else:
        click.echo("  Using E5 multilingual model (may download weights on first run)")
    
    embedder = create_embedder(mock=mock_embeddings)
    
    # Load test catalog
    click.echo(f"\nLoading test catalog: {catalog}")
    planner = TestPlanner(embedder)
    planner.HIGH_RISK_THRESHOLD = high_threshold
    planner.MEDIUM_RISK_THRESHOLD = medium_threshold
    planner.GAP_DETECTION_THRESHOLD = gap_threshold
    planner.load_test_catalog(catalog)
    click.echo(f"  Loaded {len(planner.test_catalog)} test cases")
    
    # Run planning
    click.echo(f"\nRunning test selection...")
    with tempfile.TemporaryDirectory(prefix="e5-git-media-") as temp_dir:
        try:
            query_media = defect_media + [Evidence(Path(path).resolve(), f"input: {path}") for path in media]
            if git_base:
                query_media.extend(extract_git_evidence(Path(git_repo), git_base, git_head, Path(temp_dir)))
            if not diff_summary.semantic_summary and not defect_text and not query_media:
                raise ValueError("No change text or visual evidence was provided.")
            visual_matches = {}
            if query_media:
                if not any(test.get('attachments') for test in planner.test_catalog):
                    raise ValueError("No test-case media attachments are available for comparison.")
                click.echo(f"\nComparing {len(query_media)} media file(s) using local SigLIP...")
                visual_matches = score_visual_matches(
                    query_media, planner.test_catalog, Path(catalog).resolve().parent, SiglipImageEmbedder()
                )
            result = planner.plan(
                diff_summary,
                defect_description=defect_text,
                full_suite_time_seconds=full_suite_time,
                visual_matches=visual_matches,
                visual_threshold=visual_threshold,
            )
        except (ValueError, OSError, RuntimeError) as exc:
            raise click.ClickException(f"Visual evidence processing failed: {exc}") from exc
    
    # Print summary
    click.echo(result.execution_summary)
    
    # Analyze for software releases and regression
    click.echo(f"\n" + "=" * 60)
    click.echo("SOFTWARE RELEASE & REGRESSION ANALYSIS")
    click.echo("=" * 60)
    
    release_analysis = analyze_pr_for_regression(
        diff_content=diff_text,
        file_paths=[f.file_path for f in diff_summary.files],
        defect_description=defect_text
    )
    
    # Display affected software
    affected_software = release_analysis['combined_affected_software']
    if affected_software:
        click.echo(f"\n✓ Affected Software/Apps: {len(affected_software)}")
        for software in affected_software:
            click.echo(f"  • {software.upper()}")
            if defect_text and release_analysis['defect_analysis']:
                versions = release_analysis['defect_analysis'].get('affected_versions', {}).get(software, [])
                if versions:
                    click.echo(f"    Versions: {', '.join(versions)}")
                funcs = release_analysis['defect_analysis'].get('affected_functionality', [])
                if funcs:
                    click.echo(f"    Functionality: {', '.join(funcs[:3])}")
    else:
        click.echo("\n✓ No specific software identified (generic/multi-software change)")
    
    # Display regression test areas
    regression_areas = release_analysis['combined_regression_areas']
    if regression_areas:
        click.echo(f"\n✓ Regression Testing Areas: {len(regression_areas)}")
        for area in regression_areas[:5]:
            priority = area.get('priority', 'MEDIUM')
            click.echo(f"  • [{priority:8s}] {area['area']} ({area['software']})")
            for test in area.get('tests', [])[:2]:
                click.echo(f"      - {test}")
    
    # Save enhanced report
    enhanced_report = {
        'test_selection': result.to_dict(),
        'software_release_analysis': {
            'affected_software': affected_software,
            'regression_areas': regression_areas,
            'diff_analysis': release_analysis['diff_analysis'],
            'defect_analysis': release_analysis['defect_analysis'],
            'summary': release_analysis['summary'],
        }
    }
    
    # Save report
    click.echo(f"\nSaving enhanced report: {output}")
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(enhanced_report, f, indent=2)
    
    # Print top-N selected tests
    click.echo("\nTOP 10 SELECTED TESTS:")
    for i, test in enumerate(result.ranked_tests[:10], 1):
        risk_level = "HIGH" if test.similarity_score >= planner.HIGH_RISK_THRESHOLD else "MEDIUM"
        click.echo(
            f"  {i:2d}. [{risk_level:6s}] {test.test_id} ({test.similarity_score:.3f}): {test.title}"
        )
        if test.visual_similarity_score is not None:
            click.echo(f"      Visual similarity: {test.visual_similarity_score:.3f} "
                       f"({test.visual_query} vs {test.visual_reference})")
    
    # Print gaps if any
    if result.gap_tickets:
        click.echo(f"\n{len(result.gap_tickets)} COVERAGE GAPS DETECTED:")
        for gap in result.gap_tickets[:5]:
            click.echo(f"  - {gap.suggested_id}: {gap.title}")
            click.echo(f"    Domain: {gap.domain}")
            click.echo(f"    Reason: {gap.gap_reason}")
    
    click.echo("\n✓ Analysis complete")


@cli.command()
def version():
    """Show version."""
    click.echo("e5-diff-to-test-planner v1.0.0")


if __name__ == '__main__':
    cli()
