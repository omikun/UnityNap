#!/usr/bin/env bash

cd src
if [ "$1" = "python3" ]
then
    python3 setup.py py2app
else
    python setup.py py2app
fi