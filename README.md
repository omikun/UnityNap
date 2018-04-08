# ForceNap <img src="/img/Icon.png" width="32" height="32" />

Useful for times when you want to keep a battery-hogging application running in the background to switch to intermittently, but don't want to pay the battery penalty of keeping it running when you don't need it. Examples include Unity, Matlab, Civilization, etc.

- Force one or more apps to stop when not in focus and resumes each app when they regain focus.
- This script runs every 0.5 second, but otherwise should introduce no additional lag. 
- Apps that are ForceNapped cannot be interacted with in the background (scroll with another app in focus).
- You may see spinning beachball over ForceNapped apps and they will show as "Not responding" in Activity Monitor. Click on the app or alt-tab back to it to resume the app.
- Suspend only stops the app from using CPU but keeps data in memory.

This differs from App Nap which throttles and potentially stops apps, but only if they are supported.

## Usage:
- Download the pre-release [ForceNap](https://github.com/omikun/MyAppNap/releases)
- Open and select the application(s) to force nap in the status bar (look for FN). 
![Screen shot](/img/ForceNap_screen_shot.png)

## Limitations:
- ForceNap does not support when target application spawns a new window.
- ForceNap must be started after target applications have been started. 
- This is not a stable product yet. 
- Not suited for mission critical applications.

## Compile 
You can also compile your own using [rumps](https://github.com/jaredks/rumps/blob/master/rumps/rumps.py) and py2app.

    python setup.py py2app
    
### Deprecated:
Start desired app, then run script with one or more app names as arguments:`python nap_my_app.py app_name(s)`

For example, to suspend Unity and Safari:

    python nap_my_app.py Unity Safari

If no argument is given, all defocused apps (apps that get focus then lose it) are automatically suspended.

On exit, all suspended apps will be resumed.

Tested in Mac OS Sierra

## TODO:

    - Done - Disallow suspending Terminal (useful if you're launching from Terminal)
    - DONE - do nothing if invalid name given
    - DONE - Integrate with rumps so this can be accessed from the status bar instead of terminal
    - DONE - Select multiple apps to nap at the same time
    - Refactor code
    - Dynamically update menu
    - Handle new windows spawned by target applications
    - Handle target application shutdown
