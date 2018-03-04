#!/usr/bin/python                                                                                            

''' This script automatically finds PIDs for desiredApp
    and suspend those processes whenever desired app  is not in focus. 
    This script is meant to stay running and polls window focus every 1 second
    On receiving keyboard interrupt, will resume
'''
from datetime import datetime
from time import sleep
import sys
import subprocess
import os
import signal

try:
    from AppKit import NSWorkspace
except ImportError:
    print "Can't import AppKit -- maybe you're running python from brew?"
    print "Try running with Apple's /usr/bin/python instead."
    exit(1)

def get_pid(name):
    try:
        result = subprocess.check_output(['pgrep '+name], shell=True)
        return result.strip().split('\n')
    except:
        print '''Invalid app name, will not suspend/resume anything
        Will monitor apps in focus, switch to your desired app to see valid name'''
        return None

# if script invoked with an argument, use that as the pid
if len(sys.argv) > 1:
    da = sys.argv[1]
    if da == 'Terminal':
        print 'Can\'t suspend Terminal, especially if you are calling from Terminal'
    else:
        desiredApp = da
        pids = get_pid(desiredApp)

if pids:
    print "Monitoring %s, with PIDs: %s" % (desiredApp, pids) 

try:
    last_active_app = None
    stop = True
    while True:
        active_app = NSWorkspace.sharedWorkspace().activeApplication()
        if last_active_app != active_app['NSApplicationName']:
            last_active_app = active_app['NSApplicationName']
            print "Currently focused on", last_active_app
            if last_active_app == desiredApp:
                stop = True
                if pids:
                    print "Continuing", desiredApp
                    for pid in pids:
                        os.kill(pid, signal.SIGCONT)
            elif stop:
                stop = False
                if pids:
                    print "Stopping", desiredApp
                    for pid in pids:
                        os.kill(pid, signal.SIGSTOP)
        sleep(1)
except KeyboardInterrupt:
    print '\nExiting script'
    if pids:
        print '\nResuming %s' % desiredApp
        for pid in pids:
            os.kill(pid, signal.SIGCONT)
    sys.exit()
