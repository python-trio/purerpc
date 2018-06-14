#! /usr/bin/env bash

python3 -m pip install twine
twine upload -u $TWINE_USER -p $TWINE_PASSWORD dist/*.whl

