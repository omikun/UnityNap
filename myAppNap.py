#!/usr/bin/python
"""
Automatically suspend applications which are not in focus.
The applications are polled every second.
"""
from __future__ import print_function

import subprocess
import sys
import time

try:
    from AppKit import NSWorkspace
except ImportError:
    print("Can't import AppKit -- maybe you're running python from brew?")
    print("Try running with Apple's /usr/bin/python instead.")
    sys.exit(1)


def get_pids(name):
    try:
        result = subprocess.check_output(["pgrep", name])
        return result.strip().splitlines()
    except:
        # XXX: You should specify the exception type here.
        print("Invalid app name, will not suspend/resume anything",
              "Will monitor apps in focus, "
              "switch to your desired app to see valid name",
              sep="\n")
        return None


def continue_pids(pids):
    # We need to make sure that each process continues correctly, so we
    # store a list of the `kill` processes to make sure they complete
    # later.
    processes = []
    for pid in pids:
        process = subprocess.Popen(["kill", "-CONT", pid])
        processes.append((pid, process))

    for (pid, process) in processes:
        returncode = process.wait()

        if returncode != 0:
            print("Process", pid, "did not continue properly.",
                  "It exited with the status code:", returncode)


def stop_pids(pids):
    # The code here is mostly duplicated from `continue_pids`. I just
    # copy-pasted for clarity, but it might be smart to create a separate
    # function.
    processes = []
    for pid in pids:
        process = subprocess.Popen(["kill", "-STOP", pid])
        processes.append((pid, process))

    for (pid, process) in processes:
        returncode = process.wait()

        if returncode != 0:
            print("Process", pid, "did not continue properly.",
                  "It exited with the status code:", returncode)


def monitor_apps(desired_app, pids):
    last_active_app = None
    is_stopped = True

    while True:
        active_app = NSWorkspace.sharedWorkspace().activeApplication()
        active_app_name = active_app["NSApplicationName"]

        if last_active_app != active_app_name:
            last_active_app = active_app_name
            print("Currently focused on", last_active_app)

            if last_active_app == desired_app:
                is_stopped = True
                continue_pids(pids)
            elif is_stopped:
                is_stopped = False
                stop_pids(pids)

        time.sleep(1)


def main():
    if len(sys.argv) < 2:
        print("USAGE: python myAppNap.py APPLICATION")
        sys.exit(1)

    desired_app = sys.argv[1]
    if desired_app == "Terminal":
        print("Can't suspend Terminal, "
              "especially if you are calling from Terminal")

    pids = get_pids(desired_app)
    if pids:
        print("Monitoring %s, with PIDs: %s" % (desired_app, pids))

    try:
        monitor_apps(desired_app, pids)
    except KeyboardInterrupt:
        pass
    finally:
        print()
        print("Exiting script")
        print()
        print("Resuming", desired_app)

        continue_pids(pids)


if __name__ == "__main__":
    # XXX: I've removed `shell=True` in a few calls. You should verify that
    # it still works, seeing as I sadly can't test anything on OSX.
    main()
