#!/bin/bash
SCRIPT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pushd $SCRIPT_DIRECTORY > /dev/null

rm -rf .package sh-insights-collector.zip

cd package
zip -r ../sh-insights-collector.zip .
cd ../
zip -g sh-insights-collector.zip sh-insights-collector.py

popd > /dev/null