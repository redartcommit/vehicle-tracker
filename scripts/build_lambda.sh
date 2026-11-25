#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build/lambda"

rm -rf "$BUILD" && mkdir -p "$BUILD"
pip install --quiet --target "$BUILD" \
  --platform manylinux2014_aarch64 --implementation cp --python-version 3.12 \
  --only-binary=:all: -r "$ROOT/api/requirements-lambda.txt"
cp -r "$ROOT/api/app" "$BUILD/app"
echo "Built $BUILD"