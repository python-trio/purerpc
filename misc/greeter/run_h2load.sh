#! /usr/bin/env bash

NUM_REQUESTS=1000000
NUM_CLIENTS=100
NUM_STREAMS=100
WINDOW_SIZE_LOG=24
NUM_THREADS=8
AUTHORITY="192.168.1.10:50055"
AUTHORITY="localhost:50055"

h2load -n$NUM_REQUESTS -c$NUM_CLIENTS -m$NUM_STREAMS -w$WINDOW_SIZE_LOG -t$NUM_THREADS -d request.bin \
  -H 'te: trailers' -H 'content-type: application/grpc+proto' \
  http://$AUTHORITY/Greeter/SayHello
