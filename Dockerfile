ARG BASE_IMAGE=python:3.6
FROM ${BASE_IMAGE}
COPY . /purerpc
WORKDIR /purerpc
RUN pip install https://github.com/dfee/forge/archive/v18.6.0.zip
RUN pip install .