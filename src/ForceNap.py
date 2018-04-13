#!/usr/bin/python

from __future__ import absolute_import, print_function

import logging
import os
import signal
import subprocess
import sys
import time
from threading import Thread

from six import string_types

import rumps

try:
    from AppKit import NSWorkspace
except ImportError:
    NSWorkspace = None
    raise ImportError("Can't import AppKit, maybe you're running python from brew? \n "
                      "Try running with Apple's /usr/bin/python instead.")

DO_NOT_SUSPEND_BY_NAME = ('iTerm2', 'Terminal', 'Activity Monitor')
DO_NOT_SUSPEND_BY_PID = set()
DEBUG = False

suspended = set()  # set of PIDs that has been suspended
bad_app_names = set()
last_bad_app_names = set()
settings_updated = [False]

# If user changes one or more settings in 1 tick, in next tick, Resume everything not selected, suspend everything 
# selected (except active app)
nap_this_app = None
menuStates = {}
launched_apps = None


# Parameter 'sender' needs to be there for rumps to be happy
# noinspection PyUnusedLocal
class ForceNapBarApp(rumps.App):
    def __init__(self):
        super(ForceNapBarApp, self).__init__("FN", quit_button=None)
        self.refresh_button(None)

    # FIXME Not being triggered for some reason
    @rumps.clicked("Refresh...")
    def refresh_button(self, sender):
        print("Refreshing application list...")
        print("Type of launchedApps: ", type(launched_apps), type(launched_apps[0]))
        for i, launchedApp in enumerate(launched_apps):
            app_name = name_of(launchedApp)
            # TODO Check if the app is already in there
            if app_name not in DO_NOT_SUSPEND_BY_NAME:
                print("Adding ", app_name)
                self.menu.add(rumps.MenuItem(app_name, callback=application_menu_item(app_name)))

    @rumps.clicked('Quit')
    def my_quit(self, sender):
        quit_clean()


def quit_clean():
    print('Quitting with cleanup...')
    for this_pid in suspended:
        os.kill(int(this_pid), signal.SIGCONT)
    rumps.quit_application()


def init_logger():
    this_logger = logging.getLogger()
    this_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s', '%b %d %H:%M:%S')
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(formatter)
    this_logger.addHandler(stdout)
    return this_logger


def name_of(app):
    if app is None:
        return None
    app_name = app['NSApplicationName']
    if sys.version_info.major < 3 and isinstance(app_name, string_types):
        # TODO handle errors instead of ignoring them
        app_name = app_name.encode("utf8", "ignore")
    return app_name


def update_state(adding, app_name):
    settings_updated[0] = True
    if adding:
        bad_app_names.add(app_name)
    else:
        bad_app_names.discard(app_name)


def application_menu_item(app_name):
    def helper(sender):
        sender.state = not sender.state
        if DEBUG:
            print('Clicked on', app_name)
        update_state(sender.state, app_name)

    return helper


def get_pids(app):
    """Returns list of all process IDs for given application."""
    if not app:
        return []
    this_pid = app['NSApplicationProcessIdentifier']

    pids = [this_pid]
    try:
        pids += map(int, subprocess.check_output(['pgrep', '-P %s' % this_pid]).split())
    except subprocess.CalledProcessError:
        pass
    return pids


def suspend(prev_app):
    if name_of(prev_app) in DO_NOT_SUSPEND_BY_NAME:
        if DEBUG:
            print(name_of(prev_app) + ' not suspended, in do not suspend list')
        return

    pids = get_pids(prev_app)
    logger.debug('Suspending %s (%s)', pids, name_of(prev_app))
    for this_pid in pids:
        suspended.add(this_pid)
        os.kill(int(this_pid), signal.SIGSTOP)


def resume(app):
    # Resume apps that have been suspended and aren't on the do not suspend list
    if name_of(app) in DO_NOT_SUSPEND_BY_NAME:
        print(name_of(app) + ' not resumed, in dont suspend list')
        return
    pids = get_pids(app)
    for this_pid in pids:
        if this_pid in suspended:
            break
    else:
        return
    # only resume pids that are suspended
    logger.debug('Resuming %s (%s)', pids, name_of(app))
    for this_pid in pids:
        suspended.discard(this_pid)
        os.kill(int(this_pid), signal.SIGCONT)
    for this_pid in pids:
        os.kill(int(this_pid), signal.SIGCONT)


def on_update_settings(apps, cur_app):
    global last_bad_app_names
    settings_updated[0] = False
    # resume all apps
    # suspend all sucky_app_names
    new_sucky = bad_app_names - last_bad_app_names
    not_sucky = last_bad_app_names - bad_app_names
    if DEBUG:
        print("Updating settings:")
        print(bad_app_names)
        print(last_bad_app_names)
    last_bad_app_names = set(bad_app_names)
    for l_app in apps:
        if l_app == cur_app:
            print(name_of(l_app), "is current app, skipping")
            continue
        if name_of(l_app) in new_sucky:
            suspend(l_app)
        if name_of(l_app) in not_sucky:
            resume(l_app)


def run():
    prev_app = None
    while True:
        cur_app = NSWorkspace.sharedWorkspace().activeApplication()
        if settings_updated[0]:
            print("Settings update detected in my_app_nap()")
            on_update_settings(launched_apps, cur_app)
        if prev_app != cur_app:
            if cur_app['NSApplicationName'] in bad_app_names:
                resume(cur_app)
            if prev_app and prev_app['NSApplicationName'] in bad_app_names:
                suspend(prev_app)
            prev_app = cur_app
        time.sleep(0.5)


if __name__ == '__main__':
    # In the case that the thread is interrupted (which should generate a KeyboardInterrupt), resume all the apps
    logger = init_logger()
    launched_apps = NSWorkspace.sharedWorkspace().launchedApplications()

    # The actual checking needs to be spun out into a separate thread, otherwise it'll be blocked by the running, and we
    # can't spin out the rumps stuff since that demands that it be invoked form the main thread

    try:
        thread = Thread(target=run)
        thread.setDaemon(True)
        thread.start()

        ForceNapBarApp().run()
    except KeyboardInterrupt:
        quit_clean()
