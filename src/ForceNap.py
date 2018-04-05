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
    raise ImportError("Can't import AppKit -- maybe you're running python from brew? \n "
                      "Try running with Apple's /usr/bin/python instead.")

SUSPENDED = set()  # set of PIDs that has been suspended

DONT_SUSPEND_NAME = ('iTerm2', 'Terminal', 'Activity Monitor')  # set of apps to never suspend/resume

bad_app_names = set()
last_bad_app_names = set()
settings_updated = [False]
# If user changes one or more settings in 1 tick, in next tick, Resume everything not selected, suspend everything 
# selected (except active app)
nap_this_app = None
menuStates = {}
launchedApps = None


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
    print("setting updated!!!!!")
    if adding:
        bad_app_names.add(app_name)
    else:
        bad_app_names.discard(app_name)


def clear_other_states(app_name):
    # only used for keeping only 1 app monitored at a time
    for k, v in menuStates.items():
        if k == app_name:
            continue
        v.state = False


class ForceNapBarApp(rumps.App):
    # noinspection PyUnusedLocal
    @rumps.clicked('Quit')
    def my_quit(self, sender):
        print('Quiting with cleanup')
        clean_exit()
        rumps.quit_application()


def menu_item(app_name):
    def helper(sender):
        sender.state = not sender.state
        print('clicked on', app_name)
        update_state(sender.state, app_name)

    return helper


def refresh_list(menu):
    # noinspection PyUnusedLocal
    def helper(sender):
        print('just clicked refresh')
        print('type of launchedApps:', type(launchedApps), type(launchedApps[0]))
        # launchedApps.sort(key=lambda x: name_of(x))
        for i, launchedApp in enumerate(launchedApps):
            app_name = name_of(launchedApp)
            print('Adding', app_name)
            if app_name in DONT_SUSPEND_NAME:
                continue
            # this doesn't add after the first click
            # menu.insert_before('Quit', rumps.MenuItem(appName,
            #                                         callback=menu_item(appName)))
            # this will keep adding
            menu.add(rumps.MenuItem(app_name, callback=menu_item(app_name)))
            # todo: must only add new apps and remove old ones

    return helper


def start_bar():
    app = ForceNapBarApp('FN', quit_button=None)
    app.menu.add(rumps.MenuItem('Refresh', callback=refresh_list(app.menu)))
    app.menu.add(rumps.separator)
    app.run()


def clean_exit():
    for this_pid in SUSPENDED:
        os.kill(int(this_pid), signal.SIGCONT)


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
    if name_of(prev_app) in DONT_SUSPEND_NAME:
        print(name_of(prev_app) + ' not suspended, in dont suspend list')
        return

    pids = get_pids(prev_app)
    logger.debug('Suspending %s (%s)', pids, name_of(prev_app))
    for this_pid in pids:
        SUSPENDED.add(this_pid)
        os.kill(int(this_pid), signal.SIGSTOP)


def resume(app):
    # Resume apps that have been suspended and aren't on the do not suspend list
    if name_of(app) in DONT_SUSPEND_NAME:
        print(name_of(app) + ' not resumed, in dont suspend list')
        return
    pids = get_pids(app)
    for this_pid in pids:
        if this_pid in SUSPENDED:
            break
    else:
        return
    # only resume pids that are suspended
    logger.debug('Resuming %s (%s)', pids, name_of(app))
    for this_pid in pids:
        SUSPENDED.discard(this_pid)
        os.kill(int(this_pid), signal.SIGCONT)
    for this_pid in pids:
        os.kill(int(this_pid), signal.SIGCONT)


def on_update_settings(launched_apps, cur_app):
    global last_bad_app_names
    settings_updated[0] = False
    # resume all apps
    # suspend all sucky_app_names
    print("updating settings:")
    new_sucky = bad_app_names - last_bad_app_names
    not_sucky = last_bad_app_names - bad_app_names
    print(bad_app_names)
    print(last_bad_app_names)
    last_bad_app_names = set(bad_app_names)
    for l_app in launched_apps:
        if l_app == cur_app:
            print(name_of(l_app), "is current app, skipping")
            continue
        if name_of(l_app) in new_sucky:
            suspend(l_app)
        if name_of(l_app) in not_sucky:
            resume(l_app)


def my_app_nap():
    prev_app = None
    while True:
        cur_app = NSWorkspace.sharedWorkspace().activeApplication()
        if settings_updated[0]:
            print("settings update detected in my_app_nap()")
            on_update_settings(launchedApps, cur_app)
        if prev_app != cur_app:
            if cur_app['NSApplicationName'] in bad_app_names:
                resume(cur_app)
            if prev_app and prev_app['NSApplicationName'] in bad_app_names:
                suspend(prev_app)
            prev_app = cur_app
        time.sleep(0.5)


if __name__ == '__main__':
    try:
        # TODO precaution: resume all launched apps in case last shutdown left some apps hanging
        logger = init_logger()
        launchedApps = NSWorkspace.sharedWorkspace().launchedApplications()
        thread = Thread(target=my_app_nap)
        thread.start()
        start_bar()
        thread.join()
    except KeyboardInterrupt:
        print('\nResuming all suspended apps')
        for pid in SUSPENDED:
            os.kill(int(pid), signal.SIGCONT)
