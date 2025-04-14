#!/usr/bin/env bash


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo $SCRIPT_DIR

cd $SCRIPT_DIR/src

rm -rf ./public/*

hugo server  -D --disableFastRender --noHTTPCache --logLevel debug


