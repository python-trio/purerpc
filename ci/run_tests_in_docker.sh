#! /usr/bin/env bash

# TODO: add python3.7-rc and pypy
for image in python:3.6; do
  docker run -it -v `pwd`:/project_root -w /project_root $image bash -c 'pip install dist/*.whl && python setup.py test' || exit -1;
done

