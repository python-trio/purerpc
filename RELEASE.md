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
