#!/bin/bash
if [[ -f "decky-disable-integrated-rog-ally-controller.zip" ]]; then
    rm -f decky-disable-integrated-rog-ally-controller.zip
fi
zip -r decky-disable-integrated-rog-ally-controller.zip plugin.json main.py dist
