cmake_minimum_required(VERSION 3.13)
project(purerpc)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
#set(CMAKE_C_FLAGS -fsanitize=address,undefined,leak)
#set(CMAKE_CXX_FLAGS "-fsanitize=address,undefined,leak -ftemplate-backtrace-limit=0")

add_subdirectory(third_party/fmt)

add_subdirectory(third_party/pybind11)

set(ENABLE_STATIC_LIB ON CACHE BOOL "build nghttp2 static lib")
set(ENABLE_LIB_ONLY ON CACHE BOOL "build nghttp2 lib only")
add_subdirectory(third_party/nghttp2)
include_directories(third_party/nghttp2/lib/includes)
include_directories(third_party/nghttp2ver/includes)

add_subdirectory(src/purerpc/grpclib)
