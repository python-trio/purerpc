#! /usr/bin/env bash

set -e

BASE_IMAGE="$1"
BUILD_TAG=${BASE_IMAGE//:/-}
BUILD_TAG=${BUILD_TAG//\//-}

docker build --build-arg BASE_IMAGE=${BASE_IMAGE} -t "standy/purerpc:${BUILD_TAG}" .
docker run -it "standy/purerpc:$BUILD_TAG" bash -c 'python setup.py test'
