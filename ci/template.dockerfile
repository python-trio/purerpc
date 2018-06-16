FROM %BASE_IMAGE%
COPY . /purerpc
WORKDIR /purerpc
RUN pip install .
