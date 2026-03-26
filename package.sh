#!/bin/bash
if [[ -d "package" ]]; then
    rm -rf package
fi

PACKAGE_FILE="package.json"
version=$(jq -r '.version' "$PACKAGE_FILE")
if [ "$1" == "-release" ]; then
    echo "Incrementing version for release..."
    IFS='.' read -r major minor patch <<< "$version"
    ((patch++))
    version="${major}.${minor}.${patch}"
    jq ".version = \"$version\"" "$PACKAGE_FILE" > "/tmp/$PACKAGE_FILE"
    mv -f "/tmp/$PACKAGE_FILE" "$PACKAGE_FILE"
fi
echo "Version is: $version"

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
