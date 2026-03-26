# fd-limits-monitor

Quick tool to check file descriptor limits and usage on Linux. I wrote this because hitting FD limits in production is no fun, and I wanted something simple to monitor before things go sideways.

## What it does

- Shows system-wide FD allocation vs max limit
- Shows per-process FD usage and limits (soft/hard)
- Lists top FD consumers
- Threshold checking for monitoring/alerting

## Installation

```bash
pip install -r requirements.txt
```

Or just run it directly if you're lazy:

```bash
python fd_limits_monitor.py
```

## Usage

### Basic check (system + current process)

```bash
python fd_limits_monitor.py
```

### Check a specific process

```bash
python fd_limits_monitor.py -p 1234
```

### See top FD consumers

```bash
python fd_limits_monitor.py -t
python fd_limits_monitor.py -t 20
```

### Show everything

```bash
python fd_limits_monitor.py -a
```

### For monitoring scripts (Nagios, Prometheus, whatever)

```bash
python fd_limits_monitor.py --check
echo $?  # 0=OK, 1=WARNING, 2=CRITICAL

python fd_limits_monitor.py --check --warning 80 --critical 95
```

## Output example

```
SYSTEM-WIDE FILE DESCRIPTOR LIMITS
------------------------------------------------------------
  Allocated FDs:     4,224
  System Max:        922,337,203,685,477,5807
  Usage:             0.00% [OK]
  Available:         922,337,203,685,473,383

PROCESS FD LIMITS (PID: 12345, python3)
------------------------------------------------------------
  Current Usage:     23
  Soft Limit:        1024
  Hard Limit:        1048576
  Usage:             2.25% [OK]
  Available:         1001
```

## Why I built this

Debugged a nasty FD leak last month. By the time we noticed, the service was already hosed. This tool lets me:

1. Quick-check if FD usage is creeping up
2. Spot which process is hogging descriptors
3. Plug it into monitoring before things get bad

## Notes

- Linux only (reads from `/proc`)
- Needs read access to `/proc/{pid}/` dirs
- Some info might be limited without root

## License

MIT. Do what you want.
