cmake_minimum_required(VERSION 3.13)
project(grpclib)

include_directories(.)

pybind11_add_module(_grpclib_bindings
        bindings.cc
        http2/utility.cc
        http2/events.cc
        http2/headers.cc
        http2/errors.cc
        grpc/config.cc
        grpc/connection.cc
        )
target_compile_options(_grpclib_bindings PRIVATE -Werror -Wall -Wextra -Wno-unused-parameter)
target_link_libraries(_grpclib_bindings PRIVATE nghttp2_static fmt)
