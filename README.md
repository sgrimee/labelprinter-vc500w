Fork from ![https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/](https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/)

LICENSED at AGPLv3 
# Installation
1. Download as zip /tar.gz and unzip it.
2. Run labelprinter.sh as command with paramaters

# Usage 


Quote:
> The module itself can be downloaded below and can be started directly with the included labelprinter.sh helper script or via python3 -m labelprinter. Here is an overview of the options offered by the main routine:
```
usage: labelprinter.sh [-?] [-h HOST] [-p PORT]
                       (--print-jpeg JPEG | --get-status | --release JOB_ID)
                       [--print-lock] [--print-mode {vivid,normal}]
                       [--print-cut {none,half,full}] [--wait-after-print]
                       [-j]
 
Remotely control a VC-500W via TCP/IP.
 
optional arguments:
  -?, --help            show this help message and exit
  -h HOST, --host HOST  the VC-500W's hostname or IP address, defaults to
                        192.168.0.1
  -p PORT, --port PORT  the VC-500W's port number, defaults to 9100
 
command argument:
  --print-jpeg JPEG     prints a JPEG image out of the VC-500W
  --get-status          connects to the VC-500W and returns its status
  --release JOB_ID      tries to release the printer from an unclean lock
                        earlier on
 
print options:
  --print-lock          use the lock/release mechanism for printing (error
                        prone, do not use unless strictly required)
  --print-mode {vivid,normal}
                        sets the print mode for a vivid or normal printing,
                        defaults to normal
  --print-cut {none,half,full}
                        sets the cut mode after printing, either not cutting
                        (none), allowing the user to slide to cut (half) up to
                        a complete cut of the label (full), defaults to full
  --wait-after-print    wait for the printer to turn idle after printing
                        before returning
 
status options:
  -j, --json            return the status information in JSON format
  ```