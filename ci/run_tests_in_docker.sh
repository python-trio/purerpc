#! /usr/bin/env bash

set -e

BASE_IMAGE="$1"
PURERPC_BACKEND="$2"
BUILD_TAG=${BASE_IMAGE//:/-}
BUILD_TAG=${BUILD_TAG//\//-}

docker build --build-arg BASE_IMAGE=${BASE_IMAGE} -t "standy/purerpc:${BUILD_TAG}" .

echo "Runnig tests with $PURERPC_BACKEND backend"
if [[ $BASE_IMAGE == pypy* ]]; then
  CMD="pypy3 setup.py test"
else
  CMD="python setup.py test"
fi

docker run -it -e PURERPC_BACKEND=${PURERPC_BACKEND} "standy/purerpc:$BUILD_TAG" bash -c "$CMD"
