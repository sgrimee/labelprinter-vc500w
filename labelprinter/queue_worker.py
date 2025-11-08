#!/usr/bin/env python3
"""
CUPS queue worker for Brother VC-500W label printer

This worker processes jobs from the CUPS queue and sends them to the printer.
It handles printer busy states with retries and provides clear status updates.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Try to import pycups, show helpful error if not installed
try:
    import cups
except ImportError:
    print("ERROR: pycups is not installed", file=sys.stderr)
    print("\nCUPS queue mode requires the pycups library.", file=sys.stderr)
    print("Install it with:", file=sys.stderr)
    print("  uv tool install --with pycups labelprinter", file=sys.stderr)
    print("  # or", file=sys.stderr)
    print("  pip install pycups", file=sys.stderr)
    sys.exit(1)

from labelprinter.print_text import load_config
from labelprinter.connection import Connection
from labelprinter.printer import LabelPrinter


class QueueWorker:
    """Processes print jobs from CUPS queue"""

    def __init__(self, queue_name, dry_run=False, verbose=False):
        self.queue_name = queue_name
        self.dry_run = dry_run
        self.verbose = verbose
        self.conn = cups.Connection()
        self.config = load_config()

    def log(self, message, force=False):
        """Print log message if verbose or forced"""
        if self.verbose or force:
            print(message)

    def get_held_jobs(self):
        """Get all held/pending jobs from the queue"""
        try:
            jobs = self.conn.getJobs(
                which_jobs='not-completed',
                my_jobs=False,
                requested_attributes=['job-id', 'job-name', 'job-state',
                                     'job-state-reasons', 'job-originating-user-name']
            )

            # Filter to our queue and held jobs
            held_jobs = []
            for job_id, job_info in jobs.items():
                # CUPS job state: 4 = pending, 5 = held, 6 = processing
                if job_info.get('job-state') in [4, 5]:  # pending or held
                    held_jobs.append((job_id, job_info))

            return sorted(held_jobs, key=lambda x: x[0])  # Sort by job ID

        except cups.IPPError as e:
            self.log(f"Error getting jobs from CUPS: {e}", force=True)
            return []

    def get_job_file(self, job_id):
        """Get the file path for a CUPS job"""
        try:
            # CUPS spool directory is typically /var/spool/cups
            # Job files are named d<job_id>-001
            spool_dir = Path("/var/spool/cups")

            # Try to find the job file
            for job_file in spool_dir.glob(f"d{job_id:05d}-*"):
                return job_file

            # If not found in expected location, try alternative patterns
            for job_file in spool_dir.glob(f"d{job_id}-*"):
                return job_file

            return None

        except Exception as e:
            self.log(f"Error finding job file: {e}", force=True)
            return None

    def print_job(self, job_id, job_info):
        """
        Print a job using the existing label-raw infrastructure

        Returns:
            (success, error_message, should_retry)
        """
        job_name = job_info.get('job-name', f'Job {job_id}')

        self.log(f"\n{'='*60}", force=True)
        self.log(f"Processing job {job_id}: {job_name}", force=True)
        self.log(f"{'='*60}", force=True)

        # Get the job file
        job_file = self.get_job_file(job_id)
        if not job_file or not job_file.exists():
            error = f"Job file not found for job {job_id}"
            self.log(f"✗ {error}", force=True)
            return (False, error, False)  # Don't retry, file is missing

        self.log(f"Job file: {job_file}")

        if self.dry_run:
            self.log(f"[DRY RUN] Would print: {job_file}", force=True)
            return (True, None, False)

        # Build label-raw command
        cmd = [
            "label-raw",
            "--host", self.config['host'],
            str(job_file)
        ]

        if self.verbose:
            cmd.append("--debug")

        # Execute label-raw
        try:
            self.log(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # Same timeout as direct printing
            )

            if result.returncode == 0:
                self.log(f"✓ Job {job_id} printed successfully", force=True)
                return (True, None, False)
            else:
                error_output = result.stderr.strip() or result.stdout.strip()

                # Check if error is due to printer being busy
                if "BUSY" in error_output.upper() or "did not become idle" in error_output:
                    self.log(f"⏸  Printer is busy, job {job_id} will be retried", force=True)
                    return (False, "Printer busy", True)  # Retry later

                # Other error
                self.log(f"✗ Job {job_id} failed: {error_output}", force=True)
                return (False, error_output, False)  # Don't retry

        except subprocess.TimeoutExpired:
            error = "Print command timed out (120s)"
            self.log(f"✗ Job {job_id} timed out", force=True)
            return (False, error, True)  # Retry timeout

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            self.log(f"✗ Job {job_id} error: {error}", force=True)
            return (False, error, False)  # Don't retry unexpected errors

    def mark_job_completed(self, job_id):
        """Mark a job as completed in CUPS"""
        try:
            self.conn.cancelJob(job_id, purge_job=False)
            return True
        except cups.IPPError as e:
            self.log(f"Warning: Could not mark job {job_id} as completed: {e}", force=True)
            return False

    def mark_job_failed(self, job_id, error_message):
        """Mark a job as failed (for now, just cancel it)"""
        try:
            # In a more sophisticated system, we might move to a dead letter queue
            # For now, we'll just cancel with a message
            self.log(f"Canceling failed job {job_id}: {error_message}", force=True)
            self.conn.cancelJob(job_id, purge_job=False)
            return True
        except cups.IPPError as e:
            self.log(f"Warning: Could not cancel job {job_id}: {e}", force=True)
            return False

    def process_queue(self, continuous=False, retry_delay=30):
        """
        Process all pending jobs in the queue

        Args:
            continuous: If True, keep processing until queue is empty
            retry_delay: Seconds to wait before retrying busy printer
        """
        processed = 0
        failed = 0
        busy_jobs = []

        while True:
            jobs = self.get_held_jobs()

            if not jobs:
                if continuous and busy_jobs:
                    self.log(f"\nWaiting {retry_delay}s before retrying {len(busy_jobs)} busy job(s)...", force=True)
                    time.sleep(retry_delay)
                    continue
                else:
                    break

            self.log(f"\nFound {len(jobs)} job(s) to process", force=True)

            for job_id, job_info in jobs:
                # Release the job so we can process it
                try:
                    self.conn.releaseJob(job_id)
                except cups.IPPError:
                    pass  # Might already be released

                success, error, should_retry = self.print_job(job_id, job_info)

                if success:
                    self.mark_job_completed(job_id)
                    processed += 1
                elif should_retry:
                    busy_jobs.append(job_id)
                    if not continuous:
                        self.log(f"  Job {job_id} will remain in queue for retry", force=True)
                else:
                    self.mark_job_failed(job_id, error)
                    failed += 1

            if not continuous:
                break

        # Summary
        self.log(f"\n{'='*60}", force=True)
        self.log(f"Queue processing complete", force=True)
        self.log(f"  Processed: {processed}", force=True)
        self.log(f"  Failed: {failed}", force=True)
        if busy_jobs:
            self.log(f"  Waiting (busy): {len(busy_jobs)}", force=True)
        self.log(f"{'='*60}", force=True)

        return processed, failed, len(busy_jobs)


def main():
    parser = argparse.ArgumentParser(
        description="Process print jobs from CUPS queue for Brother VC-500W"
    )
    parser.add_argument(
        '--queue-name',
        help='Name of CUPS queue (defaults to config value)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Keep processing until queue is empty (retry busy jobs)'
    )
    parser.add_argument(
        '--retry-delay',
        type=int,
        default=30,
        help='Seconds to wait before retrying busy jobs (default: 30)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be printed without actually printing'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    # Get config
    config = load_config()

    # Determine queue name
    if args.queue_name:
        queue_name = args.queue_name
    elif config.get('cups', {}).get('enabled'):
        queue_name = config['cups'].get('queue_name', 'BrotherVC500W')
    else:
        print("ERROR: CUPS mode not enabled", file=sys.stderr)
        print("Run 'label-queue-setup' to configure CUPS queue", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("[DRY RUN MODE - no actual printing will occur]")

    # Create worker and process queue
    worker = QueueWorker(queue_name, dry_run=args.dry_run, verbose=args.verbose)

    try:
        processed, failed, busy = worker.process_queue(
            continuous=args.continuous,
            retry_delay=args.retry_delay
        )

        # Exit code indicates if there were failures
        if failed > 0:
            sys.exit(1)
        elif busy > 0 and not args.continuous:
            sys.exit(2)  # Jobs waiting due to busy printer
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
