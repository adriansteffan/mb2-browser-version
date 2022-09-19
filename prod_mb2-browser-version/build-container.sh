#!/bin/bash
set -e

cd ..
mkdir -p local-server/webroot
./build.sh
cp -r local-server/webroot prod_mb2-browser-version
cd prod_mb2-browser-version
docker-compose build --no-cache
docker-compose up -d
