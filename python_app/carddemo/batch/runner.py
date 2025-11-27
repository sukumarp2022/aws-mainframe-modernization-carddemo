"""
Batch job runner for CardDemo.

This module provides a command-line interface for running batch jobs,
replacing the mainframe JCL job submission process.
"""

import argparse
import json
import logging
import sys
from datetime import date
from typing import Optional

from .transaction_posting import run_transaction_posting
from .interest_calculation import run_interest_calculation
from .statement_generation import run_statement_generation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_job(
    job_name: str,
    input_file: Optional[str] = None,
    output_file: Optional[str] = None,
    process_date: Optional[date] = None,
) -> dict:
    """
    Run a batch job by name.

    Args:
        job_name: Name of the job to run
        input_file: Optional input file path
        output_file: Optional output file path
        process_date: Optional processing date

    Returns:
        Job result as dictionary
    """
    logger.info(f"Starting batch job: {job_name}")

    if job_name == "post_transactions":
        result = run_transaction_posting(input_file)
    elif job_name == "calculate_interest":
        result = run_interest_calculation(process_date)
    elif job_name == "generate_statements":
        result = run_statement_generation(process_date)
    else:
        raise ValueError(f"Unknown job: {job_name}")

    result_dict = result.to_dict()

    if output_file:
        with open(output_file, "w") as f:
            json.dump(result_dict, f, indent=2)
        logger.info(f"Results written to: {output_file}")

    logger.info(f"Batch job {job_name} completed")
    return result_dict


def main():
    """Main entry point for batch job runner."""
    parser = argparse.ArgumentParser(
        description="CardDemo Batch Job Runner",
        epilog="""
Available jobs:
  post_transactions   - Post daily transactions (POSTTRAN equivalent)
  calculate_interest  - Calculate monthly interest (INTCALC equivalent)
  generate_statements - Generate account statements (CREASTMT equivalent)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--job",
        "-j",
        required=True,
        choices=["post_transactions", "calculate_interest", "generate_statements"],
        help="Name of the batch job to run",
    )

    parser.add_argument(
        "--input",
        "-i",
        help="Input file path (for post_transactions)",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Output file path for job results (JSON format)",
    )

    parser.add_argument(
        "--date",
        "-d",
        help="Processing date (YYYY-MM-DD format)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    process_date = None
    if args.date:
        try:
            process_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            sys.exit(1)

    try:
        result = run_job(
            job_name=args.job,
            input_file=args.input,
            output_file=args.output,
            process_date=process_date,
        )

        # Print summary
        print("\n" + "=" * 60)
        print(f"JOB COMPLETED: {args.job}")
        print("=" * 60)
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Job failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
