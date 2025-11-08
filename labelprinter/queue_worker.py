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
                                     'job-state-reasons', 'job-originating-user-name',
                                     'job-printer-uri', 'document-name-supplied']
            )

            self.log(f"Found {len(jobs)} total not-completed jobs")

            # Filter to our queue and held jobs
            held_jobs = []
            for job_id, job_info in jobs.items():
                state = job_info.get('job-state')
                doc_name = job_info.get('document-name-supplied', '')
                self.log(f"  Job {job_id}: state={state}, document={doc_name}")

                # CUPS job state: 3 = pending (stopped printer), 4 = pending, 5 = held, 6 = processing
                if job_info.get('job-state') in [3, 4, 5]:  # pending or held
                    held_jobs.append((job_id, job_info))
                    self.log(f"    -> Added to processing list")

            self.log(f"Total jobs to process: {len(held_jobs)}")
            return sorted(held_jobs, key=lambda x: x[0])  # Sort by job ID

        except cups.IPPError as e:
            self.log(f"Error getting jobs from CUPS: {e}", force=True)
            return []

    def get_job_file(self, job_id, job_info):
        """
        Get the file path for a CUPS job

        Since we can't access /var/spool/cups without root,
        we use the document-name-supplied attribute which contains
        the original filename (basename only).
        """
        try:
            # document-name-supplied contains just the filename
            doc_name = job_info.get('document-name-supplied', '')

            if doc_name:
                # Try as absolute path first
                image_file = Path(doc_name)
                if image_file.exists():
                    self.log(f"Found image file: {image_file}")
                    return image_file

                # Otherwise look in images/ directory
                image_file = Path('images') / doc_name
                if image_file.exists():
                    self.log(f"Found image file: {image_file}")
                    return image_file

                self.log(f"Image file not found: {doc_name} (tried both absolute and images/)")
            else:
                self.log(f"No document name in job info")

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
        job_file = self.get_job_file(job_id, job_info)
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
            "--print-jpeg", str(job_file)
        ]

        # Note: label-raw doesn't have --debug flag
        # Verbose output is handled by capturing stderr

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
        """
        Mark a job as failed

        Leaves the job in the queue so user can investigate and retry manually.
        User can cancel with: label-queue cancel <job_id>
        """
        try:
            self.log(f"✗ Job {job_id} FAILED: {error_message}", force=True)
            self.log(f"  Job {job_id} remains in queue. To cancel: label-queue cancel {job_id}", force=True)
            # Don't cancel - leave in queue for manual intervention
            return True
        except Exception as e:
            self.log(f"Warning: Error marking job {job_id} as failed: {e}", force=True)
            return False

    def process_queue(self, continuous=False, watch=False, retry_delay=30, poll_interval=5):
        """
        Process all pending jobs in the queue

        Args:
            continuous: If True, keep processing until queue is empty
            watch: If True, keep running and wait for new jobs (daemon mode)
            retry_delay: Seconds to wait before retrying busy printer
            poll_interval: Seconds to wait before checking for new jobs in watch mode
        """
        processed = 0
        failed = 0
        busy_jobs = []
        failed_jobs = []  # Track jobs that failed in this run (don't retry)

        if watch:
            self.log("👀 Watch mode enabled - worker will keep running until stopped (Ctrl+C)", force=True)

        while True:
            jobs = self.get_held_jobs()

            # Check if all jobs are already failed in this run
            new_jobs = [job for job in jobs if job[0] not in failed_jobs]

            if not new_jobs:
                if busy_jobs:
                    # Have busy jobs to retry
                    self.log(f"\nWaiting {retry_delay}s before retrying {len(busy_jobs)} busy job(s)...", force=True)
                    time.sleep(retry_delay)
                    continue
                elif watch:
                    # Watch mode: wait for new jobs
                    # (all current jobs have already failed)
                    if failed_jobs:
                        self.log(f"All {len(failed_jobs)} job(s) failed. Waiting {poll_interval}s for new jobs...", force=False)
                    else:
                        self.log(f"Queue empty, waiting {poll_interval}s for new jobs...", force=False)
                    time.sleep(poll_interval)
                    continue
                else:
                    # Not watch mode and no new jobs: exit
                    break

            self.log(f"\nFound {len(new_jobs)} job(s) to process", force=True)

            for job_id, job_info in jobs:
                # Skip jobs we've already failed in this run
                if job_id in failed_jobs:
                    self.log(f"  Skipping job {job_id} (already failed in this run)")
                    continue

                # Process the job (no need to release since printer is disabled, not held)
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
                    failed_jobs.append(job_id)  # Don't retry this job in this run
                    failed += 1

            # In watch mode, keep going after processing batch
            # In one-shot mode, exit after processing once
            if not continuous and not watch:
                break

        # Summary (only shown when exiting, not in watch mode)
        self.log(f"\n{'='*60}", force=True)
        self.log(f"Queue processing complete", force=True)
        self.log(f"  Processed: {processed}", force=True)
        self.log(f"  Failed: {failed}", force=True)
        if busy_jobs:
            self.log(f"  Waiting (busy): {len(busy_jobs)}", force=True)
        if failed_jobs:
            self.log(f"  Remaining in queue (failed): {len(failed_jobs)}", force=True)
            self.log(f"  To cancel failed jobs: label-queue cancel <job-id>", force=True)
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
        '--watch', '-w',
        action='store_true',
        help='Keep running and wait for new jobs (daemon mode). Use Ctrl+C to stop.'
    )
    parser.add_argument(
        '--retry-delay',
        type=int,
        default=30,
        help='Seconds to wait before retrying busy jobs (default: 30)'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Seconds to wait before checking for new jobs in watch mode (default: 5)'
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
            watch=args.watch,
            retry_delay=args.retry_delay,
            poll_interval=args.poll_interval
        )

        # Exit code indicates if there were failures
        if failed > 0:
            sys.exit(1)
        elif busy > 0 and not args.continuous and not args.watch:
            sys.exit(2)  # Jobs waiting due to busy printer
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⏹  Worker stopped by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
