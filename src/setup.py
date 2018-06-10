from setuptools import setup

APP = ['ForceNap.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': '../img/Icon.icns',
    'packages': ['rumps'],
    'plist': {
        'LSUIElement': True,
        'CFBundleVersion': '0.4.0'
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'], install_requires=['pyobjc', 'rumps', 'six']
)
