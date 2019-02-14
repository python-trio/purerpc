ARG BASE_IMAGE=python:3.6
FROM ${BASE_IMAGE}
COPY . /purerpc
WORKDIR /purerpc
RUN pip install .
RUN pip install uvloop curio trio==0.10  # Optional, for tests
RUN pip install https://github.com/dfee/forge/archive/v18.6.0.zip