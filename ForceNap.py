#!/usr/bin/python

from __future__ import print_function
import time
import sys
import subprocess
import os
import signal
import logging
import rumps
from threading import Thread

try:
  from AppKit import NSWorkspace
except ImportError:
  print("Can't import AppKit -- maybe you're running python from brew?")
  print("Try running with Apple's /usr/bin/python instead.")
  sys.exit(1)

SUSPENDED = set()  #set of PIDs that has been suspended
DONT_SUSPEND_NAME = ('iTerm2', 'Terminal', 'Activity Monitor') #set of apps to never suspend/resume

sucky_app_names = set()
last_sucky_app_names = set()
settings_updated = [False]
# if user changes one or more settings in 1 tick:
# in next tick
# unsuspend everything not selected, suspend everything selected (except active app)
nap_this_app = None
menuStates = {}
launchedApps = None

def init_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s', '%b %d %H:%M:%S')
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(formatter)
    logger.addHandler(stdout)
    return logger

def name_of(app):
    if app is None:
        return None
    app_name = app['NSApplicationName']
    if sys.version_info.major < 3 and isinstance(app_name, unicode):
        # TODO handle errors instead of ignoring them
        app_name = app_name.encode("utf8", "ignore")
    return app_name

def update_state(adding, appName):
    settings_updated[0] = True
    print("setting updated!!!!!")
    if adding:
        sucky_app_names.add(appName)
    else:
        sucky_app_names.discard(appName)


def clearOtherStates(appName):
    'only used for keeping only 1 app monitored at a time'
    for k, v in menuStates.items():
        if k == appName:
            continue
        v.state = False

class ForceNapBarApp(rumps.App):
    pass

def menu_quit(sender):
    print('Quiting with cleanup')
    clean_exit()
    rumps.quit_application()

def menu_item(appName):
    def helper(sender):
        sender.state = not sender.state
        print ('clicked on', appName)
        update_state(sender.state, appName)
    return helper

prev_names = set()
def refresh_list(app):
    def helper(sender):
        print('just clicked refresh')
        #app.menu.clear()
        #populate_bar(app)
        old_update(app.menu)

    return helper

def old_update(menu):
    global prev_names
    launchedApps = NSWorkspace.sharedWorkspace().launchedApplications()
    app_names = sorted([name_of(la) for la in launchedApps])
    curr_names = set(app_names)
    # get difference between old list and cur list
    new_names = curr_names - prev_names
    gone_names = prev_names - curr_names
    # delete all prev_names
    for app_name in gone_names:
        print('Deleting', app_name)
        del menu[app_name]
    for index, app_name in enumerate(app_names):
        if app_name not in new_names or app_name in DONT_SUSPEND_NAME:
            continue
        print('Adding', app_name)
        if sender == []:
            menu.add(rumps.MenuItem(app_name, callback=menu_item(app_name)))
            continue
        if index == 0:
            menu.insert_after('Refresh',
                              rumps.MenuItem(app_name, callback=menu_item(app_name)))
        else:
            menu.insert_after(app_names[index-1],
                              rumps.MenuItem(app_name, callback=menu_item(app_name)))
        # this will keep adding
        # todo: must only add new apps and remove old ones
    prev_names = curr_names


def start_bar():
    app = ForceNapBarApp('FN', quit_button=None)
    populate_bar(app)
    app.run()

def populate_bar(app):
    'add refresh, app buttons, and quit button to menu'
    refresh_item = refresh_list(app)
    app.menu.add(rumps.MenuItem('Refresh', callback=refresh_item))
    app.menu.add(rumps.separator)

    launchedApps = NSWorkspace.sharedWorkspace().launchedApplications()
    app_names = sorted([name_of(la) for la in launchedApps])
    for index, app_name in enumerate(app_names):
        if app_name in DONT_SUSPEND_NAME:
            continue
        print('Adding', app_name)
        app.menu.add(rumps.MenuItem(app_name, callback=menu_item(app_name)))
    app.menu.add(rumps.MenuItem('Quit', callback=menu_quit))

def clean_exit():
    for pid in SUSPENDED:
        os.kill(int(pid), signal.SIGCONT)

def get_pids(app):
    """Returns list of all process IDs for given application."""
    if not app:
        return []
    pid = app['NSApplicationProcessIdentifier']
    pids = [pid]
    try:
        pids += map(int, subprocess.check_output(['pgrep', '-P %s' % pid]).split())
    except subprocess.CalledProcessError:
        pass
    return pids

def suspend(prev_app):
    if name_of(prev_app) in DONT_SUSPEND_NAME:
        print(name_of(prev_app) + ' not suspended, in dont suspend list')
        return
    pids = get_pids(prev_app)
    logger.debug('Suspending %s (%s)', pids, name_of(prev_app))
    for pid in pids:
        SUSPENDED.add(pid)
        os.kill(int(pid), signal.SIGSTOP)


def resume(app):
    'Resume apps that have been suspended and arent on the do not suspend list'
    if name_of(app) in DONT_SUSPEND_NAME: 
        print(name_of(app) + ' not resumed, in dont suspend list')
        return
    pids = get_pids(app)
    for pid in pids:
        if pid in SUSPENDED:
            break
    else:
        return
    # only resume pids that are suspended
    logger.debug('Resuming %s (%s)', pids, name_of(app))
    for pid in pids:
        SUSPENDED.discard(pid)
        os.kill(int(pid), signal.SIGCONT)
    for pid in pids:
        os.kill(int(pid), signal.SIGCONT)

def on_update_settings(launchedApps, cur_app):
    global last_sucky_app_names
    settings_updated[0] = False
    # resume all apps
    # suspend all sucky_app_names
    print("updating settings:")
    new_sucky = sucky_app_names - last_sucky_app_names
    not_sucky = last_sucky_app_names - sucky_app_names
    last_sucky_app_names = set(sucky_app_names)
    for l_app in launchedApps:
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
            if cur_app['NSApplicationName'] in sucky_app_names:
                resume(cur_app)
            if prev_app and prev_app['NSApplicationName'] in sucky_app_names:
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

