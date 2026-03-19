#!/bin/bash
if [[ -d "package" ]]; then
    rm -rf package
fi
pnpm build
mkdir -p package/decky-disable-integrated-rog-ally-controller/dist
cp dist/index.js package/decky-disable-integrated-rog-ally-controller/dist/
cp main.py package/decky-disable-integrated-rog-ally-controller/
cp plugin.json package/decky-disable-integrated-rog-ally-controller/
cp package.json package/decky-disable-integrated-rog-ally-controller/
cd package
zip -r ../decky-disable-integrated-rog-ally-controller.zip decky-disable-integrated-rog-ally-controller/
rm -rf ~/repos/decky-disable-integrated-rog-ally-controller/package
cd ..
