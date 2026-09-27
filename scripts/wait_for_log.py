"""Run a command that prints a log, and wait for a line in it.

    python scripts/wait_for_log.py --timeout 300 "mathlint: engine ready" -- adb logcat

CI starts the apps in an emulator or a simulator and follows the device's log
with this: it succeeds as soon as a line contains the text, and fails when the
command ends or the time runs out first, showing the end of the log so the
reason is in the job's output. The command is stopped either way.
"""

from __future__ import annotations

import argparse
import collections
import subprocess
import sys
import threading
import time


def wait_for(command: list[str], text: str, timeout: float, tail: int = 80) -> bool:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    last = collections.deque(maxlen=tail)
    found = threading.Event()

    def read() -> None:
        for line in process.stdout:
            last.append(line.rstrip("\n"))
            if text in line:
                print(line.rstrip("\n"), flush=True)
                found.set()
                return

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    started = time.monotonic()
    while not found.is_set() and reader.is_alive() and time.monotonic() - started < timeout:
        found.wait(0.5)
    process.kill()
    if not found.is_set():
        why = "ended" if not reader.is_alive() else f"ran {timeout:.0f} s"
        print(f"the log {why} without {text!r}; its last lines:", file=sys.stderr)
        print("\n".join(last), file=sys.stderr)
    return found.is_set()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("text")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("give the command after --")
    return 0 if wait_for(command, args.text, args.timeout) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
