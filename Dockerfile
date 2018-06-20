ARG BASE_IMAGE=python:3.6
FROM ${BASE_IMAGE}
COPY . /purerpc
WORKDIR /purerpc
RUN pip install .
