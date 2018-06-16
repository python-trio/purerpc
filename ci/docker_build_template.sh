#! /usr/bin/env bash

set -e

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 BUILD_IMAGE_TAG BASE_IMAGE";
    exit -1;
fi

BUILD_IMAGE_NAME="standy/purerpc"

BUILD_IMAGE_TAG=${1}
if [[ ! -z ${BUILD_IMAGE_TAG} ]]; then
    BUILD_IMAGE_TAG=":${BUILD_IMAGE_TAG}"
fi

BASE_IMAGE=${2}

DOCKERFILE=$(mktemp /tmp/Dockerfile-XXXXXXXXX)
sed 's,%BASE_IMAGE%,'${BASE_IMAGE}',g' ./ci/Dockerfile.template > ${DOCKERFILE}

echo "Building Dockerfile:"
cat ${DOCKERFILE}

docker build -t ${BUILD_IMAGE_NAME}${BUILD_IMAGE_TAG} -f ${DOCKERFILE} .

rm ${DOCKERFILE}
