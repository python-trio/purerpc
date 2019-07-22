# [Release 0.4.0](https://github.com/standy66/purerpc/compare/v0.3.2...v0.4.0) (2019-07-22)


### Bug Fixes

* speed improvements ([1cb3d46](https://github.com/standy66/purerpc/commit/1cb3d46))


### Features

* add state property to GRPCStream ([0019d8c](https://github.com/standy66/purerpc/commit/0019d8c))
* answer PING frames ([c829901](https://github.com/standy66/purerpc/commit/c829901))
* change MAX_CONCURRENT_STREAMS from 1000 to 65536 ([d2d461f](https://github.com/standy66/purerpc/commit/d2d461f))
* decouple h2 and grpclib logic ([1f4e6b0](https://github.com/standy66/purerpc/commit/1f4e6b0))
* support percent-encoded grpc-message header ([c6636f4](https://github.com/standy66/purerpc/commit/c6636f4))
* change default max message length to 32 MB


# [Release 0.3.2](https://github.com/standy66/purerpc/compare/v0.3.1...v0.3.2) (2019-02-15)


### Bug Fixes

* fix dependencies, remove some of anyio monkey patches ([ac6c5c2](https://github.com/standy66/purerpc/commit/ac6c5c2))



# [Release 0.3.1](https://github.com/standy66/purerpc/compare/v0.3.0...v0.3.1) (2019-02-15)


### Bug Fixes

* fix pickling error in purerpc.test_utils._WrappedResult ([9f0a63d](https://github.com/standy66/purerpc/commit/9f0a63d))



# [Release 0.3.0](https://github.com/standy66/purerpc/compare/v0.2.1...v0.3.0) (2019-02-14)


### Features

* expose new functions in purerpc.test_utils ([07b10e1](https://github.com/standy66/purerpc/commit/07b10e1))
* migrate to pytest ([95c0a8b](https://github.com/standy66/purerpc/commit/95c0a8b))


### BREAKING CHANGES

* purerpc.test_utils.PureRPCTestCase is removed



# [Release 0.2.0](https://github.com/standy66/purerpc/compare/v0.1.6...v0.2.0) (2019-02-10)


### Features

* add backend option to Server.serve ([5f47f8e](https://github.com/standy66/purerpc/commit/5f47f8e))
* add support for Python 3.5 ([a681192](https://github.com/standy66/purerpc/commit/a681192))
* improved exception handling in test utils ([b1df796](https://github.com/standy66/purerpc/commit/b1df796))
* migrate to anyio ([746b1c2](https://github.com/standy66/purerpc/commit/746b1c2))


### BREAKING CHANGES

* Server and test now use asyncio event loop by default,
this behaviour can be changed with PURERPC_BACKEND environment variable
* purerpc.Channel is removed, migrate to
purerpc.insecure_channel async context manager (now supports correct
shutdown)

## Release 0.1.6

* Allow passing request headers to method handlers in request argument
* Allow passing custom metadata to method stub calls (in metadata optional keyword argument)

## Release 0.1.5

* Enforce SO_KEEPALIVE with small timeouts
* Expose PureRPCTestCase in purerpc API for unit testing purerpc services

## Release 0.1.4

* Speed up protoc plugin

## Release 0.1.3 [PyPI only]

* Fix long description on PyPI

## Release 0.1.2

* Fix unit tests on Python 3.7

## Release 0.1.0

* Implement immediate mode

## Release 0.0.1

* Initial release
