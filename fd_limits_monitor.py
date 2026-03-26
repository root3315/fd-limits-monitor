#!/usr/bin/env python3
"""
fd-limits-monitor - Monitor file descriptor limits and usage on Linux systems.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Tuple


def get_system_fd_limits() -> Tuple[int, int]:
    """
    Get system-wide file descriptor limits from /proc/sys/fs/file-max
    and current usage from /proc/sys/fs/file-nr.
    
    Returns:
        Tuple of (current_usage, max_limit)
    """
    file_max_path = Path("/proc/sys/fs/file-max")
    file_nr_path = Path("/proc/sys/fs/file-nr")
    
    if not file_max_path.exists():
        return 0, 0
    
    max_limit = 0
    try:
        max_limit = int(file_max_path.read_text().strip())
    except (ValueError, PermissionError):
        pass
    
    current_usage = 0
    if file_nr_path.exists():
        try:
            parts = file_nr_path.read_text().strip().split()
            if len(parts) >= 1:
                current_usage = int(parts[0])
        except (ValueError, PermissionError):
            pass
    
    return current_usage, max_limit


def get_process_fd_limits(pid: Optional[int] = None) -> Tuple[int, int]:
    """
    Get soft and hard file descriptor limits for a process.
    
    Args:
        pid: Process ID (None for current process)
    
    Returns:
        Tuple of (soft_limit, hard_limit)
    """
    if pid is None:
        pid = os.getpid()
    
    limits_path = Path(f"/proc/{pid}/limits")
    
    if not limits_path.exists():
        return 0, 0
    
    try:
        content = limits_path.read_text()
        for line in content.splitlines():
            if "Max open files" in line or "open files" in line.lower():
                parts = line.split()
                if len(parts) >= 6:
                    soft = int(parts[3]) if parts[3] != "unlimited" else 1048576
                    hard = int(parts[4]) if parts[4] != "unlimited" else 1048576
                    return soft, hard
    except (ValueError, PermissionError, IndexError):
        pass
    
    return 0, 0


def count_process_fds(pid: Optional[int] = None) -> int:
    """
    Count the number of open file descriptors for a process.
    
    Args:
        pid: Process ID (None for current process)
    
    Returns:
        Number of open file descriptors
    """
    if pid is None:
        pid = os.getpid()
    
    fd_path = Path(f"/proc/{pid}/fd")
    
    if not fd_path.exists():
        return 0
    
    try:
        return len(list(fd_path.iterdir()))
    except PermissionError:
        return 0


def get_fd_usage_percentage(current: int, limit: int) -> float:
    """Calculate usage percentage."""
    if limit == 0:
        return 0.0
    return (current / limit) * 100


def format_percentage(percentage: float) -> str:
    """Format percentage with color-coded status."""
    if percentage >= 90:
        status = "CRITICAL"
    elif percentage >= 75:
        status = "WARNING"
    elif percentage >= 50:
        status = "MODERATE"
    else:
        status = "OK"
    return f"{percentage:6.2f}% [{status}]"


def print_separator(char: str = "=", length: int = 60) -> None:
    """Print a separator line."""
    print(char * length)


def display_system_limits() -> None:
    """Display system-wide file descriptor limits."""
    print("\nSYSTEM-WIDE FILE DESCRIPTOR LIMITS")
    print_separator("-")
    
    current, max_limit = get_system_fd_limits()
    percentage = get_fd_usage_percentage(current, max_limit)
    
    print(f"  Allocated FDs:     {current:,}")
    print(f"  System Max:        {max_limit:,}")
    print(f"  Usage:             {format_percentage(percentage)}")
    
    if max_limit > 0:
        remaining = max_limit - current
        print(f"  Available:         {remaining:,}")


def display_process_limits(pid: Optional[int] = None) -> None:
    """Display file descriptor limits for a specific process."""
    target_pid = pid if pid is not None else os.getpid()
    process_name = get_process_name(target_pid)
    
    print(f"\nPROCESS FD LIMITS (PID: {target_pid}, {process_name})")
    print_separator("-")
    
    soft_limit, hard_limit = get_process_fd_limits(target_pid)
    current_usage = count_process_fds(target_pid)
    percentage = get_fd_usage_percentage(current_usage, soft_limit)
    
    print(f"  Current Usage:     {current_usage:,}")
    print(f"  Soft Limit:        {soft_limit:,}")
    print(f"  Hard Limit:        {hard_limit:,}")
    print(f"  Usage:             {format_percentage(percentage)}")
    
    if soft_limit > 0:
        remaining = soft_limit - current_usage
        print(f"  Available:         {remaining:,}")


def get_process_name(pid: int) -> str:
    """Get process name from /proc/{pid}/comm."""
    comm_path = Path(f"/proc/{pid}/comm")
    try:
        return comm_path.read_text().strip()
    except (PermissionError, FileNotFoundError):
        return "unknown"


def list_top_fd_consumers(limit: int = 10) -> None:
    """List processes with most open file descriptors."""
    print(f"\nTOP {limit} PROCESSES BY FD USAGE")
    print_separator("-")
    
    proc_path = Path("/proc")
    fd_counts = []
    
    try:
        for entry in proc_path.iterdir():
            if not entry.name.isdigit():
                continue
            
            pid = int(entry.name)
            fd_count = count_process_fds(pid)
            if fd_count > 0:
                name = get_process_name(pid)
                fd_counts.append((pid, name, fd_count))
    except PermissionError:
        pass
    
    fd_counts.sort(key=lambda x: x[2], reverse=True)
    
    if not fd_counts:
        print("  No processes found or insufficient permissions")
        return
    
    print(f"  {'PID':<10} {'Name':<25} {'FD Count':<10}")
    print(f"  {'-'*10} {'-'*25} {'-'*10}")
    
    for pid, name, count in fd_counts[:limit]:
        print(f"  {pid:<10} {name:<25} {count:<10}")


def check_thresholds(warning: float = 75.0, critical: float = 90.0) -> int:
    """
    Check FD usage against thresholds and return exit code.
    
    Returns:
        0 if OK, 1 if WARNING, 2 if CRITICAL
    """
    current, max_limit = get_system_fd_limits()
    percentage = get_fd_usage_percentage(current, max_limit)
    
    if percentage >= critical:
        print(f"CRITICAL: System FD usage at {percentage:.2f}%")
        return 2
    elif percentage >= warning:
        print(f"WARNING: System FD usage at {percentage:.2f}%")
        return 1
    else:
        print(f"OK: System FD usage at {percentage:.2f}%")
        return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor file descriptor limits and usage on Linux systems."
    )
    parser.add_argument(
        "-p", "--pid",
        type=int,
        help="Check FD limits for specific process ID"
    )
    parser.add_argument(
        "-t", "--top",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help="Show top N processes by FD usage (default: 10)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check thresholds and return exit code (for monitoring)"
    )
    parser.add_argument(
        "--warning",
        type=float,
        default=75.0,
        help="Warning threshold percentage (default: 75)"
    )
    parser.add_argument(
        "--critical",
        type=float,
        default=90.0,
        help="Critical threshold percentage (default: 90)"
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Show all information (system + process + top consumers)"
    )
    
    args = parser.parse_args()
    
    if args.check:
        return check_thresholds(args.warning, args.critical)
    
    if args.top is not None:
        list_top_fd_consumers(args.top)
        return 0
    
    if args.all:
        display_system_limits()
        display_process_limits(args.pid)
        list_top_fd_consumers(10)
        return 0
    
    if args.pid is not None:
        display_process_limits(args.pid)
    else:
        display_system_limits()
        print()
        display_process_limits()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
