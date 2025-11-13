"""
CLI commands for the AutoGrader system.

Implements Click-based command-line interface with commands for grading,
batch processing, validation, and configuration management.
"""

import asyncio
import click
from pathlib import Path
from typing import Optional, List
import json
import sys

from models.core import GradingRequest
from agents.orchestrator_agent import OrchestratorAgent
from config.config_loader import ConfigLoader
from cli.output import output


@click.group()
@click.version_option(version='0.1.0', prog_name='autograder')
def cli():
    """
    AutoGrader - AI-powered academic project grading system.

    Grade M.Sc. Computer Science project submissions with adaptive evaluation
    using Claude AI and multi-agent architecture.
    """
    pass


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--self-grade',
    '-s',
    type=click.IntRange(0, 100),
    required=True,
    help='Student self-assessed grade (0-100)'
)
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(path_type=Path),
    default='workspace/outputs',
    help='Output directory for reports'
)
@click.option(
    '--formats',
    '-f',
    multiple=True,
    default=['markdown'],
    type=click.Choice(['markdown', 'json', 'csv']),
    help='Output formats (can specify multiple)'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output with detailed logs'
)
def grade(
    pdf_path: Path,
    self_grade: int,
    output_dir: Path,
    formats: tuple,
    verbose: bool
):
    """
    Grade a single submission PDF.

    Example:
        autograder grade submission.pdf --self-grade 85
        autograder grade project.pdf -s 90 -f markdown -f json
    """
    output.header(f"AutoGrader - Grading {pdf_path.name}")

    # Validate inputs
    if not pdf_path.exists():
        output.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    if pdf_path.suffix.lower() != '.pdf':
        output.error(f"File must be a PDF: {pdf_path}")
        sys.exit(1)

    # Create grading request
    request = GradingRequest(
        pdf_path=pdf_path,
        self_grade=self_grade
    )

    # Show request info
    output.info(f"PDF: {pdf_path}")
    output.info(f"Self-Grade: {self_grade}")
    output.info(f"Output: {output_dir}")
    output.info(f"Formats: {', '.join(formats)}")

    # Initialize orchestrator
    try:
        config_loader = ConfigLoader()
        system_config = config_loader.load_config()

        # Override output settings
        system_config.reporter['output_dir'] = str(output_dir)
        system_config.reporter['formats'] = list(formats)

        orchestrator = OrchestratorAgent({})

    except Exception as e:
        output.error(f"Failed to initialize system: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Execute grading
    output.section("Phase 1: Validating submission")
    output.info("Checking PDF and inputs...")

    output.section("Phase 2: Parsing PDF")
    output.info("Extracting text, code blocks, and structure...")

    output.section("Phase 3: Calculating criticism multiplier")

    output.section("Phase 4: Evaluating criteria")
    output.info("Spawning 17 evaluator agents in parallel...")

    try:
        # Run async grading
        result = asyncio.run(orchestrator.execute(request))

        if not result.success:
            output.error(f"Grading failed: {result.error}")
            sys.exit(1)

        grading_result = result.output

        # Display results
        output.grading_summary({
            'submission_id': grading_result.submission_id,
            'self_grade': grading_result.self_grade,
            'final_score': grading_result.final_score,
            'processing_time_seconds': grading_result.processing_time_seconds,
            'comparison_message': grading_result.comparison_message
        })

        # Category breakdown
        if grading_result.breakdown:
            output.category_breakdown(
                {name: cat.model_dump() for name, cat in grading_result.breakdown.items()}
            )

        # Criterion details (top performers and issues)
        if verbose and grading_result.evaluations:
            output.criterion_details(
                [e.model_dump() for e in grading_result.evaluations]
            )

        # Cost summary
        if 'total_cost' in result.metadata:
            output.cost_summary({
                'total_cost': result.metadata.get('total_cost', 0.0),
                'api_calls': len(grading_result.evaluations)
            })

        # Report paths
        if 'reports' in result.metadata:
            output.file_paths(result.metadata['reports'])

        output.success(f"\nGrading complete! Final score: {grading_result.final_score:.2f}")

    except KeyboardInterrupt:
        output.warning("\nGrading interrupted by user")
        sys.exit(130)

    except Exception as e:
        output.error(f"Grading failed with error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('submissions_dir', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(path_type=Path),
    default='workspace/outputs',
    help='Output directory for reports'
)
@click.option(
    '--formats',
    '-f',
    multiple=True,
    default=['markdown', 'csv'],
    type=click.Choice(['markdown', 'json', 'csv']),
    help='Output formats'
)
@click.option(
    '--manifest',
    '-m',
    type=click.Path(exists=True, path_type=Path),
    help='JSON manifest file with submission metadata'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output'
)
def batch(
    submissions_dir: Path,
    output_dir: Path,
    formats: tuple,
    manifest: Optional[Path],
    verbose: bool
):
    """
    Grade multiple submissions in batch mode.

    Requires a manifest.json file with submission metadata:
    [
        {"pdf": "student1.pdf", "self_grade": 85},
        {"pdf": "student2.pdf", "self_grade": 90}
    ]

    Example:
        autograder batch ./submissions -m manifest.json
    """
    output.header("AutoGrader - Batch Processing")

    # Load manifest
    if not manifest:
        manifest = submissions_dir / "manifest.json"

    if not manifest.exists():
        output.error(f"Manifest file not found: {manifest}")
        output.info("Create a manifest.json with: [{\"pdf\": \"file.pdf\", \"self_grade\": 85}, ...]")
        sys.exit(1)

    try:
        with open(manifest, 'r') as f:
            submission_data = json.load(f)
    except Exception as e:
        output.error(f"Failed to load manifest: {e}")
        sys.exit(1)

    # Validate manifest
    if not isinstance(submission_data, list):
        output.error("Manifest must be a JSON array")
        sys.exit(1)

    output.info(f"Found {len(submission_data)} submissions")

    # Create grading requests
    requests = []
    for i, item in enumerate(submission_data, 1):
        pdf_path = submissions_dir / item['pdf']
        if not pdf_path.exists():
            output.warning(f"Skipping missing file: {pdf_path}")
            continue

        requests.append(GradingRequest(
            pdf_path=pdf_path,
            self_grade=item['self_grade']
        ))

    if not requests:
        output.error("No valid submissions found")
        sys.exit(1)

    output.info(f"Processing {len(requests)} submissions...")

    # Initialize orchestrator
    try:
        orchestrator = OrchestratorAgent({})
    except Exception as e:
        output.error(f"Failed to initialize system: {e}")
        sys.exit(1)

    # Process batch
    results = []
    successful = 0
    failed = 0

    for i, request in enumerate(requests, 1):
        output.section(f"Submission {i}/{len(requests)}: {request.pdf_path.name}")

        try:
            result = asyncio.run(orchestrator.execute(request))

            if result.success:
                successful += 1
                score = result.output.final_score
                output.success(f"Complete - Score: {score:.2f}")
                results.append({
                    'pdf': request.pdf_path.name,
                    'self_grade': request.self_grade,
                    'final_score': score,
                    'status': 'success'
                })
            else:
                failed += 1
                output.error(f"Failed: {result.error}")
                results.append({
                    'pdf': request.pdf_path.name,
                    'self_grade': request.self_grade,
                    'status': 'failed',
                    'error': result.error
                })

        except Exception as e:
            failed += 1
            output.error(f"Error: {e}")
            results.append({
                'pdf': request.pdf_path.name,
                'status': 'error',
                'error': str(e)
            })

        # Progress bar
        print(output.progress_bar(i, len(requests)))

    # Summary
    output.section("Batch Summary")
    output.success(f"Successful: {successful}/{len(requests)}")
    if failed > 0:
        output.error(f"Failed: {failed}/{len(requests)}")

    # Total cost
    total_cost = orchestrator.cost_tracker.get_total_cost()
    output.info(f"Total API Cost: ${total_cost:.4f}")

    # Save batch results
    batch_results_file = output_dir / "batch_summary.json"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(batch_results_file, 'w') as f:
            json.dump(results, f, indent=2)
        output.success(f"Batch summary saved to {batch_results_file}")
    except Exception as e:
        output.warning(f"Failed to save batch summary: {e}")


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--self-grade',
    '-s',
    type=click.IntRange(0, 100),
    help='Optional self-grade to validate'
)
def validate(pdf_path: Path, self_grade: Optional[int]):
    """
    Validate a submission PDF without grading.

    Checks if the PDF is valid and can be processed.

    Example:
        autograder validate submission.pdf --self-grade 85
    """
    output.header("AutoGrader - Validation")

    # Create request
    request = GradingRequest(
        pdf_path=pdf_path,
        self_grade=self_grade or 0
    )

    from agents.validation_agent import ValidationAgent

    try:
        validator = ValidationAgent({})
        result = asyncio.run(validator.execute(request))

        if result.success and result.output.is_valid:
            output.success("Validation passed!")

            if result.output.warnings:
                output.warning("Warnings:")
                for warning in result.output.warnings:
                    print(f"  • {warning}")

        else:
            output.error("Validation failed!")
            for error in result.output.errors:
                print(f"  • {error}")

            sys.exit(1)

    except Exception as e:
        output.error(f"Validation error: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    '--show',
    '-s',
    is_flag=True,
    help='Show current configuration'
)
@click.option(
    '--key',
    '-k',
    help='Configuration key to show (e.g., llm.model)'
)
def config(show: bool, key: Optional[str]):
    """
    Show or edit configuration.

    Example:
        autograder config --show
        autograder config --key llm.model
    """
    output.header("AutoGrader - Configuration")

    try:
        config_loader = ConfigLoader()
        system_config = config_loader.load_config()

        if key:
            # Show specific key
            parts = key.split('.')
            value = system_config
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    output.error(f"Configuration key not found: {key}")
                    sys.exit(1)

            output.info(f"{key} = {value}")

        elif show:
            # Show all config
            config_dict = system_config.model_dump()
            print(json.dumps(config_dict, indent=2))

        else:
            # Show usage
            output.info("Configuration file: config/default.yaml")
            output.info("Override with environment variables: AUTOGRADER_*")
            output.info("\nExamples:")
            print("  export AUTOGRADER_LLM__API_KEY=your-api-key")
            print("  export AUTOGRADER_LLM__MODEL=claude-sonnet-4-20250514")

    except Exception as e:
        output.error(f"Configuration error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
