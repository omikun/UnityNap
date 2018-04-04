#!/usr/bin/python

from __future__ import print_function

import time
import sys
import subprocess
import os
import signal
import logging


try:
    from AppKit import NSWorkspace
except ImportError:
    print('AppKit module not found, script should be run using system-default Python installations')
    sys.exit(1)

SUSPENSION_WHITELIST = ['Terminal', 'Activity Monitor', 'iTerm2']  # set of apps to never suspend/resume
suspended_pids = set()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', '%b %d %H:%M:%S')
stdout = logging.StreamHandler(sys.stdout)
stdout.setFormatter(formatter)
logger.addHandler(stdout)


class Application:
    def __init__(self, instance):
        self.instance = instance
        self.name = instance['NSApplicationName'].encode('utf8', 'ignore')
        self.pid = instance['NSApplicationProcessIdentifier']


    def get_pids(self):
        '''
        Returns all process IDs for a given application by name
        :return: pids {List[Int]} all process IDs association to that application
        '''
        pids = [self.pid]
        try:
            pids.extend([int(pid) for pid in subprocess.check_output(['pgrep', '-P %s' % self.pid]).split()])
        except subprocess.CalledProcessError:
            pass
        return pids


    def suspend(self):
        '''
        Suspend application and all processes associated with it
        '''
        if self.name in SUSPENSION_WHITELIST:
            return

        for pid in self.get_pids():
            if pid not in suspended_pids:
                logger.debug('Suspending %s (%s)', self.pid, self.name)
                suspended_pids.add(pid)
                os.kill(pid, signal.SIGSTOP)
        return


    def resume(self):
        '''
        Resume application and all processes associated with it
        '''
        for pid in self.get_pids():
            if pid in suspended_pids:
                logger.debug('Resuming %s (%s)', self.pid, self.name)
                suspended_pids.discard(pid)
                os.kill(pid, signal.SIGCONT)
        return


def suspend_background_apps():
    '''
    Suspends all apps except app in focus
    '''
    previous_app = None
    while True:
        app = Application(NSWorkspace.sharedWorkspace().activeApplication())
        if previous_app is None:
            previous_app = app
        if previous_app and app != previous_app:
            previous_app.suspend()
        app.resume()
        previous_app = app
        time.sleep(0.7)


def suspend_apps(app_names):
    '''
    Suspend apps of given names
    :param app_names: {List[String]} list of app names 
    '''
    previous_app = None
    while True:
        app = Application(NSWorkspace.sharedWorkspace().activeApplication())
        if previous_app != app:
            logger.debug('Currently focused on %s', app.name)
            if app.name in app_names:
                app.resume()
            if previous_app and previous_app.name in app_names:
                previous_app.suspend()
            previous_app = app
        time.sleep(0.7)


def main():
    if len(sys.argv) > 1:
        input_app_names = sys.argv[1:]
        logger.info('Napping %s', ', '.join(input_app_names))
        suspend_apps(input_app_names)
    else:
        suspend_background_apps()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Resuming all suspended apps')
        for pid in suspended_pids:
            os.kill(pid, signal.SIGCONT)