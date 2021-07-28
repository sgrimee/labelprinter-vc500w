Fork from [https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/](https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/)

LICENSED under AGPLv3 (Details please read LICENSE file)

This CLI command only support for [Brother VC-500W](https://www.brother.com.hk/en/labellers/vc500w.html).
Make sure the model is correct before download this.

# Disclaimer
This command / python script / program is open-sourced under AGPLv3 and public here. This is unoffcial package and there no any support guarantee so you must know, YOU decide to download this, RUN this and it might break your machine or break offical warranty. 
Take all risk by yourself when you download and running this. Thank you.

# Installation
## Manually
1. Download as zip /tar.gz and unzip it, OR git clone this repo.
2. Run labelprinter.sh as command with paramaters

## Arch Linux from AUR (Suggest)
You can install this from AUR: [https://aur.archlinux.org/packages/brother-color-label-printer/](https://aur.archlinux.org/packages/brother-color-label-printer/)

```bash
git clone https://aur.archlinux.org/brother-color-label-printer.git
cd brother-color-label-printer/
makepkg -si
```
OR use [paru](https://github.com/Morganamilo/paru)
```bash
paru -S brother-color-label-printer 
```

Then you can use "bclprinter" global command instead of labelprinter.sh

For example:
```
bclprinter --print-jpeg '/home/user/my_screenshot.jpeg' --host 192.168.82.2
```

# Host?
Yes, you must with --host of your VC-500W Printer's IP. If you donno your printer IP, you can download Offical App to scan, or use nmap scan local netowrk.
```bash
# Install nmap
pacman -S nbtscan
# Scan
nbtscan -v -s : 192.168.1.1/24 | grep "VC-500W"
```


# Usage
Minium request to print JPEG:
```bash
# for AUR install
bclprinter --host 192.168.5.5 --print-jpeg '/home/user/my_screenshot.jpeg' 

# for manual install
sh labelprinter.sh --host 192.168.5.5 --print-jpeg '/home/user/my_screenshot.jpeg'
```

Full options of printg:
```bash
# for AUR install
bclprinter --host 192.168.5.5 --print-mode vivid --print-cut full --print-jpeg '/home/user/my_screenshot.jpeg' 

# for manual install
sh labelprinter.sh --host 192.168.5.5 --print-mode vivid --print-cut full --print-jpeg '/home/user/my_screenshot.jpeg' 
```

If print still locked but print job is done / jammed, use lock command to unlock it:
```bash
# for AUR install
bclprinter --host 192.168.5.5 --print-lock

# for manual install
sh labelprinter.sh --host 192.168.5.5 --print-lock 
```


## Usage docs
Quote from original repo:

The module itself can be downloaded below and can be started directly with the included labelprinter.sh helper script or via python3 -m labelprinter. Here is an overview of the options offered by the main routine:
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

# Technical Details
Read the original post, thank you.
[https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/](https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/)
