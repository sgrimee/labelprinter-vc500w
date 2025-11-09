#!/usr/bin/env python3
"""
Queue management commands for Brother VC-500W CUPS queue

Provides commands to list, cancel, and retry print jobs.
"""

import argparse
import sys

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


class QueueManager:
    """Manages CUPS print queue"""

    def __init__(self, queue_name):
        self.queue_name = queue_name
        try:
            self.conn = cups.Connection()
        except RuntimeError as e:
            print(f"ERROR: Cannot connect to CUPS: {e}", file=sys.stderr)
            sys.exit(1)

    def list_jobs(self, show_all=False):
        """List jobs in the queue"""
        try:
            which = 'all' if show_all else 'not-completed'
            jobs = self.conn.getJobs(
                which_jobs=which,
                my_jobs=False,
                requested_attributes=[
                    'job-id', 'job-name', 'job-state', 'job-state-reasons',
                    'job-originating-user-name', 'time-at-creation', 'job-printer-uri'
                ]
            )

            if not jobs:
                print("No jobs in queue")
                return

            # Filter to our queue
            queue_jobs = [
                (job_id, info) for job_id, info in jobs.items()
            ]

            if not queue_jobs:
                print(f"No jobs for queue '{self.queue_name}'")
                return

            # Print header
            print(f"\nJobs for queue '{self.queue_name}':")
            print(f"{'ID':<6} {'State':<12} {'User':<15} {'Job Name':<30}")
            print("-" * 70)

            # State mappings
            state_names = {
                3: 'pending',
                4: 'pending',
                5: 'held',
                6: 'processing',
                7: 'stopped',
                8: 'canceled',
                9: 'aborted',
                10: 'completed'
            }

            for job_id, info in sorted(queue_jobs, key=lambda x: x[0]):
                state_code = info.get('job-state', 0)
                state = state_names.get(state_code, f'unknown({state_code})')

                # Get state reasons
                reasons = info.get('job-state-reasons', [])
                if reasons and isinstance(reasons, list):
                    if 'job-held-on-create' in reasons:
                        state = 'held'
                    elif 'printer-stopped' in reasons:
                        state = 'stopped'

                user = info.get('job-originating-user-name', 'unknown')
                name = info.get('job-name', f'Job-{job_id}')

                # Truncate long names
                if len(name) > 30:
                    name = name[:27] + '...'

                print(f"{job_id:<6} {state:<12} {user:<15} {name:<30}")

            print(f"\nTotal: {len(queue_jobs)} job(s)")

            # Show summary by state
            from collections import Counter
            state_counts = Counter(
                state_names.get(info.get('job-state', 0), 'unknown')
                for _, info in queue_jobs
            )
            if state_counts:
                print("\nBy state:", end='')
                for state, count in state_counts.items():
                    print(f" {state}={count}", end='')
                print()

        except cups.IPPError as e:
            print(f"ERROR: Cannot list jobs: {e}", file=sys.stderr)
            sys.exit(1)

    def cancel_job(self, job_id, purge=False):
        """Cancel a specific job"""
        try:
            self.conn.cancelJob(job_id, purge_job=purge)
            action = "Purged" if purge else "Canceled"
            print(f"✓ {action} job {job_id}")
        except cups.IPPError as e:
            print(f"ERROR: Cannot cancel job {job_id}: {e}", file=sys.stderr)
            sys.exit(1)

    def cancel_all_jobs(self, purge=False):
        """Cancel all jobs in the queue"""
        try:
            jobs = self.conn.getJobs(which_jobs='not-completed')

            if not jobs:
                print("No jobs to cancel")
                return

            queue_jobs = list(jobs.keys())

            if not queue_jobs:
                print(f"No jobs for queue '{self.queue_name}' to cancel")
                return

            for job_id in queue_jobs:
                try:
                    self.conn.cancelJob(job_id, purge_job=purge)
                except cups.IPPError:
                    pass  # Continue with other jobs

            action = "Purged" if purge else "Canceled"
            print(f"✓ {action} {len(queue_jobs)} job(s)")

        except cups.IPPError as e:
            print(f"ERROR: Cannot cancel jobs: {e}", file=sys.stderr)
            sys.exit(1)

    def hold_job(self, job_id):
        """Hold a job (prevent it from printing)"""
        try:
            self.conn.setJobHoldUntil(job_id, 'indefinite')
            print(f"✓ Job {job_id} held")
        except cups.IPPError as e:
            print(f"ERROR: Cannot hold job {job_id}: {e}", file=sys.stderr)
            sys.exit(1)

    def release_job(self, job_id):
        """Release a held job"""
        try:
            self.conn.releaseJob(job_id)
            print(f"✓ Job {job_id} released")
        except cups.IPPError as e:
            print(f"ERROR: Cannot release job {job_id}: {e}", file=sys.stderr)
            sys.exit(1)

    def get_queue_status(self):
        """Get printer/queue status"""
        try:
            printers = self.conn.getPrinters()

            if self.queue_name not in printers:
                print(f"Queue '{self.queue_name}' not found", file=sys.stderr)
                return

            printer = printers[self.queue_name]

            print(f"\nQueue: {self.queue_name}")
            print(f"  Description: {printer.get('printer-info', 'N/A')}")
            print(f"  Location: {printer.get('printer-location', 'N/A')}")
            print(f"  State: {printer.get('printer-state-message', 'N/A')}")

            accepting = printer.get('printer-is-accepting-jobs', False)
            print(f"  Accepting jobs: {'Yes' if accepting else 'No'}")

        except cups.IPPError as e:
            print(f"ERROR: Cannot get queue status: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Manage print jobs for Brother VC-500W CUPS queue",
        epilog="""
Examples:
  label-queue list              # List pending jobs
  label-queue list --all        # List all jobs (including completed)
  label-queue cancel 123        # Cancel job 123
  label-queue cancel --all      # Cancel all pending jobs
  label-queue hold 123          # Hold job 123
  label-queue release 123       # Release held job 123
  label-queue status            # Show queue status
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List command
    list_parser = subparsers.add_parser('list', aliases=['ls'], help='List jobs in queue')
    list_parser.add_argument('--all', action='store_true', help='Show all jobs (including completed)')

    # Cancel command
    cancel_parser = subparsers.add_parser('cancel', aliases=['rm'], help='Cancel job(s)')
    cancel_parser.add_argument('job_id', nargs='?', type=int, help='Job ID to cancel')
    cancel_parser.add_argument('--all', action='store_true', help='Cancel all pending jobs')
    cancel_parser.add_argument('--purge', action='store_true', help='Purge job data from disk')

    # Hold command
    hold_parser = subparsers.add_parser('hold', help='Hold a job (prevent printing)')
    hold_parser.add_argument('job_id', type=int, help='Job ID to hold')

    # Release command
    release_parser = subparsers.add_parser('release', help='Release a held job')
    release_parser.add_argument('job_id', type=int, help='Job ID to release')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show queue status')

    # Process command (convenience wrapper for label-queue-worker)
    process_parser = subparsers.add_parser('process', help='Process pending jobs')
    process_parser.add_argument('--continuous', action='store_true', help='Keep processing until queue empty')
    process_parser.add_argument('--dry-run', action='store_true', help='Show what would be printed')

    # Queue name argument (global)
    parser.add_argument('--queue-name', help='Name of CUPS queue (defaults to config value)')

    args = parser.parse_args()

    # Show help if no command
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get queue name from config
    config = load_config()

    if args.queue_name:
        queue_name = args.queue_name
    elif config.get('cups', {}).get('enabled'):
        queue_name = config['cups'].get('queue_name', 'BrotherVC500W')
    else:
        print("ERROR: CUPS mode not enabled", file=sys.stderr)
        print("Run 'label-queue-setup' to configure CUPS queue", file=sys.stderr)
        sys.exit(1)

    # Execute command
    manager = QueueManager(queue_name)

    if args.command in ['list', 'ls']:
        manager.list_jobs(show_all=args.all)

    elif args.command in ['cancel', 'rm']:
        if args.all:
            manager.cancel_all_jobs(purge=args.purge)
        elif args.job_id:
            manager.cancel_job(args.job_id, purge=args.purge)
        else:
            print("ERROR: Specify job ID or --all", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'hold':
        manager.hold_job(args.job_id)

    elif args.command == 'release':
        manager.release_job(args.job_id)

    elif args.command == 'status':
        manager.get_queue_status()

    elif args.command == 'process':
        # Convenience wrapper - just call label-queue-worker
        import subprocess
        cmd = ['label-queue-worker']
        if args.continuous:
            cmd.append('--continuous')
        if args.dry_run:
            cmd.append('--dry-run')

        sys.exit(subprocess.call(cmd))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
