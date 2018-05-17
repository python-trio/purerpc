#! /usr/bin/env bash

NUM_REQUESTS=10000
NUM_CLIENTS=1
NUM_STREAMS=1
WINDOW_SIZE_LOG=20
NUM_THREADS=1
AUTHORITY="localhost:50055"

h2load -n$NUM_REQUESTS -c$NUM_CLIENTS -m$NUM_STREAMS -w$WINDOW_SIZE_LOG -t$NUM_THREADS -d request.bin \
  -H 'te: trailers' -H 'content-type: application/grpc+proto' \
  http://$AUTHORITY/service/SayHelloToMany
