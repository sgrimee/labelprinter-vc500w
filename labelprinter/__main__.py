#!/usr/bin/env python3
#
# Copyright (c) Andrea Micheloni 2021
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import argparse, json
import gzip
                                      
from PIL import Image
import tempfile
import io

import mimetypes 
from labelprinter.connection import Connection
from labelprinter.printer import LabelPrinter

def main():
    parser = argparse.ArgumentParser(description='Remotely control a VC-500W via TCP/IP.', allow_abbrev=False, add_help=False, prog='labelprinter.sh');
    parser.add_argument('-?', '--help', action='help', help='show this help message and exit');
    parser.add_argument('-h', '--host', default='192.168.0.1', help='the VC-500W\'s hostname or IP address, defaults to %(default)s');
    parser.add_argument('-p', '--port', type=int, default=9100, help='the VC-500W\'s port number, defaults to %(default)s');

    command_group = parser.add_argument_group('command argument')

    group = command_group.add_mutually_exclusive_group(required=True);
    group.add_argument('--print-jpeg', type=argparse.FileType('rb'), action='store', metavar='JPEG', help='prints a JPEG image out of the VC-500W');
    group.add_argument('--get-status', action='store_true', help='connects to the VC-500W and returns its status');
    group.add_argument('--release', type=str, metavar='JOB_ID', help='tries to release the printer from an unclean lock earlier on');

    print_group = parser.add_argument_group('print options')

    print_group.add_argument('--print-lock', action='store_true', help='use the lock/release mechanism for printing (error prone, do not use unless strictly required)');
    print_group.add_argument('--print-mode', choices=['vivid', 'normal'], default='vivid', help='sets the print mode for a vivid or normal printing, defaults to %(default)s');
    print_group.add_argument('--print-cut', choices=['none', 'half', 'full'], default='full', help='sets the cut mode after printing, either not cutting (none), allowing the user to slide to cut (half) up to a complete cut of the label (full), defaults to %(default)s');
    print_group.add_argument('--wait-after-print', action='store_true', help='wait for the printer to turn idle after printing before returning');

    status_group = parser.add_argument_group('status options')
    status_group.add_argument('-j', '--json', action='store_true', help='return the status information in JSON format');

    # Printing mode overrides (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--direct', action='store_true',
                           help='Force direct printing mode (ignore CUPS config)')
    mode_group.add_argument('--queue', action='store_true',
                           help='Force queue mode via CUPS (ignore config)')

    process_arguments(parser.parse_args());

def _get_configuration_and_display_connection(printer):
    configuration = printer.get_configuration();

    tape_info = None;

    if configuration.tape_width:
        tape_info = '%smm tape inserted.' % int(configuration.tape_width * 25.4);
    else:
        tape_info = 'no tape detected.'
        
    print('Connected to the VC-500W [model %s]: %s' % (configuration.model, tape_info));

    return configuration

def get_status_json(printer):
    configuration = printer.get_configuration();

    device_json = {'model': configuration.model, 'serial': configuration.serial, 'wlan_mac': configuration.wlan_mac};
    

    status = printer.get_status();
    status_json = {'state': status.print_state, 'job_stage': status.print_job_stage, 'job_error': status.print_job_error};

    tape_remain = '';

    if configuration.tape_length_initial and status.tape_length_remaining != -1.0:
        mm_total = configuration.tape_length_initial * 2.54;
        mm_remain = status.tape_length_remaining * 2.54;

        tape_json = {'present': True, 'type': int(configuration.tape_width * 25.4), 'total': int(mm_total), 'remain': int(mm_remain)};
    else:
        tape_json = {'present': False};

    json_result = {'connected': True, 'device': device_json, 'tape': tape_json, 'status': status_json};

    print(json.dumps(json_result));

def get_status(printer):    
    configuration = _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    tape_remain = '';

    if configuration.tape_length_initial and status.tape_length_remaining != -1.0:
        mm_total = configuration.tape_length_initial * 2.54;
        mm_remain = status.tape_length_remaining * 2.54;
        tape_percent = mm_remain * 100 / mm_total;

        tape_remain = ' Remaining tape %s%% (%smm out of %smm).' % (int(tape_percent), int(mm_remain), int(mm_total));

    print('Status is (%s, %s, %s).%s' % (status.print_state, status.print_job_stage, status.print_job_error, tape_remain));

def print_jpeg(printer, use_lock, mode, cut, jpeg_file, wait_after_print):
    _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    # Check if printer is busy and wait for it to become idle
    if status.print_state != "IDLE":
        print('Printer is currently %s (%s, %s). Waiting for it to become idle...' % (
            status.print_state, status.print_job_stage, status.print_job_error));
        printer.wait_to_turn_idle();
        print('Printer is now idle, proceeding with print job...');

    if use_lock:
        lock = printer.lock(); 
        print('Printer locked with message "%s", started printing job %s...' % (lock.comment, lock.job_number));

    try:
        if use_lock:
            job_status = printer.get_job_status();
            print('Job status: %s, %s, %s. Sending the print command...' %(job_status.print_state, job_status.print_job_stage, job_status.print_job_error));
        file_type = mimetypes.guess_type(jpeg_file.name)[0];
        print('Input file type is %s' % (file_type));
        if file_type.startswith('image/') and not file_type == 'image/jpeg':
            print('Is %s but not jpeg, try convert' % file_type)
            try:
                with tempfile.NamedTemporaryFile() as tmp:
                    im1 = Image.open(jpeg_file.name)
                    imX = im1.convert('RGB')
                    pathName = tmp.name + '.jpg'
                    imX.save(pathName)
                    
                    jpeg_file = open(pathName, 'rb') 
                    old_file_type = file_type
                    file_type = mimetypes.guess_type(jpeg_file.name)[0];
                    print('%s convert to %s' % ( old_file_type, file_type))
            except:
                print('fail for convert to jpg, ')
       

        if file_type == 'image/jpeg':
            print_answer = printer.print_jpeg(jpeg_file, mode, cut);
            if wait_after_print:
                printer.wait_to_turn_idle();
            print("PRINT OK");
        else:
            print('not a JPEG file');
            print('PRINT FAILED');
    finally:
        if use_lock:
            print('Releasing lock for job %s...' % lock.job_number);
            printer.release();

def release_lock(printer, job_id):
    _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    print('Releasing lock for job %s...' % job_id);
    printer.release(job_id);

def should_use_cups_mode(args):
    """Determine if CUPS queue mode should be used based on config and flags"""
    # Priority: CLI flags > config setting

    # Explicit --direct flag always uses direct mode
    if args.direct:
        return False

    # Explicit --queue flag always uses queue mode
    if args.queue:
        return True

    # Otherwise, check config file
    try:
        from pathlib import Path
        config_file = Path.home() / ".config" / "labelprinter" / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('cups', {}).get('enabled', False)
    except:
        pass

    # Default to direct mode
    return False

def submit_to_cups_queue(image_path, args):
    """Submit print job to CUPS queue"""
    import subprocess
    import sys
    from pathlib import Path

    # Load config to get queue name
    try:
        config_file = Path.home() / ".config" / "labelprinter" / "config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
            queue_name = config.get('cups', {}).get('queue_name', 'BrotherVC500W')
    except:
        queue_name = 'BrotherVC500W'

    print(f'Submitting job to CUPS queue "{queue_name}"...')

    try:
        cmd = [
            "lp",
            "-d", queue_name,
            "-o", "fit-to-page",
            "-t", f"Label: {Path(image_path).stem}",
            str(image_path)
        ]

        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)

        if result.stdout:
            print(f'✓ {result.stdout.strip()}')
            print(f'   Image: {image_path}')
            print('\nJob queued successfully!')
            print('To process queued jobs, run: label-queue-worker')

        return 0
    except subprocess.CalledProcessError as e:
        print(f'❌ Error submitting to CUPS: {e.stderr.strip() if e.stderr else "Unknown error"}', file=sys.stderr)
        print(f'\nMake sure CUPS queue is configured. Run: label-queue-setup', file=sys.stderr)
        return 1
    except Exception as e:
        print(f'❌ Error: {e}', file=sys.stderr)
        return 1

def process_arguments(args):
    connection = None;
    try:
        # For print jobs, check if we should use CUPS mode
        if args.print_jpeg != None and should_use_cups_mode(args):
            # Save JPEG to a temporary file if needed, then submit to CUPS
            import sys
            result = submit_to_cups_queue(args.print_jpeg.name, args)
            sys.exit(result)

        # Otherwise use direct printing mode
        printer = LabelPrinter(Connection(args.host, args.port))

        if args.get_status:
            if args.json:
                get_status_json(printer);
            else:
                get_status(printer);
        elif args.print_jpeg != None:
            print_jpeg(printer, args.print_lock, args.print_mode, args.print_cut, args.print_jpeg, args.wait_after_print);
        elif args.release != None:
            release_lock(printer, args.release);
        else:
            raise ValueError('Unreachable code.');
    except:
        if args.get_status and args.json:
            print(json.dumps({'connected': False}));
            return;
        raise;
    finally:
        if connection:
            connection.close();

if __name__ == "__main__":
    main();
