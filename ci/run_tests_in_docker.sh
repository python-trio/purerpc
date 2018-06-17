#! /usr/bin/env bash

set -e

BASE_IMAGE="$1"
BUILD_TAG=${BASE_IMAGE/:/-}
BUILD_TAG=${BUILD_TAG/\//-}
echo $BUILD_TAG

./ci/docker_build_template.sh "$BUILD_TAG" "$BASE_IMAGE"
docker run -it "standy/purerpc:$BUILD_TAG" bash -c 'python setup.py test'
