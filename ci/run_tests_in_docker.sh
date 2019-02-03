#! /usr/bin/env bash

set -e

BASE_IMAGE="$1"
PURERPC_BACKEND="$2"
BUILD_TAG=${BASE_IMAGE//:/-}
BUILD_TAG=${BUILD_TAG//\//-}

docker build --build-arg BASE_IMAGE=${BASE_IMAGE} -t "standy/purerpc:${BUILD_TAG}" .
echo "Runnig tests with $PURERPC_BACKEND backend"
docker run -it -e PURERPC_BACKEND=${PURERPC_BACKEND} "standy/purerpc:$BUILD_TAG" bash -c 'python setup.py test'
