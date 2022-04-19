# Release history

## Release 0.7.1 (2022-04-19)

### Bug Fixes

* fix server end-of-stream handling, where normal client disconnects were
  being logged as exceptions


## Release 0.7.0 (2022-04-17)

### Features

* add Server.serve_async(), allowing the grpc server to run concurrently
  with other async tasks.  (Server.serve() is deprecated.)
* upgrade anyio dependency, which will resolve conflicts when trying to use
  purerpc together with other packages depending on anyio

### BREAKING CHANGES

* drop curio backend support (since anyio has dropped it)
* drop Python 3.5, 3.6 support


## [Release 0.6.1](https://github.com/python-trio/purerpc/compare/v0.6.0...v0.6.1) (2020-04-13)

### Bug Fixes

* build in PyPy 3.6, remove 3.5 builds from CI ([d1bcc9d](https://github.com/python-trio/purerpc/commit/d1bcc9d))
* remove CPython 3.5 builds ([7488ba8](https://github.com/python-trio/purerpc/commit/7488ba8))



## [Release 0.6.0](https://github.com/python-trio/purerpc/compare/v0.5.2...v0.6.0) (2020-04-13)

### Features

* Add TLS Support


## [Release 0.5.2](https://github.com/python-trio/purerpc/compare/v0.5.1...v0.5.2) (2019-07-23)


### Features

* additional exception shielding for asyncio ([3cbd35c](https://github.com/python-trio/purerpc/commit/3cbd35c))



## [Release 0.5.1](https://github.com/python-trio/purerpc/compare/v0.5.0...v0.5.1) (2019-07-23)


### Bug Fixes

* async generators on python 3.5 ([1c19229](https://github.com/python-trio/purerpc/commit/1c19229))



## [Release 0.5.0](https://github.com/python-trio/purerpc/compare/v0.4.1...v0.5.0) (2019-07-23)


### Features

* can now pass contextmngr or setup_fn/teardown_fn to add_service ([208dd95](https://github.com/python-trio/purerpc/commit/208dd95))



## [Release 0.4.1](https://github.com/python-trio/purerpc/compare/v0.4.0...v0.4.1) (2019-07-22)


### Features

* remove undocumented use of raw_socket in anyio ([6de2c9a](https://github.com/python-trio/purerpc/commit/6de2c9a))



## [Release 0.4.0](https://github.com/python-trio/purerpc/compare/v0.3.2...v0.4.0) (2019-07-22)


### Bug Fixes

* speed improvements ([1cb3d46](https://github.com/python-trio/purerpc/commit/1cb3d46))


### Features

* add state property to GRPCStream ([0019d8c](https://github.com/python-trio/purerpc/commit/0019d8c))
* answer PING frames ([c829901](https://github.com/python-trio/purerpc/commit/c829901))
* change MAX_CONCURRENT_STREAMS from 1000 to 65536 ([d2d461f](https://github.com/python-trio/purerpc/commit/d2d461f))
* decouple h2 and grpclib logic ([1f4e6b0](https://github.com/python-trio/purerpc/commit/1f4e6b0))
* support percent-encoded grpc-message header ([c6636f4](https://github.com/python-trio/purerpc/commit/c6636f4))
* change default max message length to 32 MB


## [Release 0.3.2](https://github.com/python-trio/purerpc/compare/v0.3.1...v0.3.2) (2019-02-15)


### Bug Fixes

* fix dependencies, remove some of anyio monkey patches ([ac6c5c2](https://github.com/python-trio/purerpc/commit/ac6c5c2))



## [Release 0.3.1](https://github.com/python-trio/purerpc/compare/v0.3.0...v0.3.1) (2019-02-15)


### Bug Fixes

* fix pickling error in purerpc.test_utils._WrappedResult ([9f0a63d](https://github.com/python-trio/purerpc/commit/9f0a63d))



## [Release 0.3.0](https://github.com/python-trio/purerpc/compare/v0.2.1...v0.3.0) (2019-02-14)


### Features

* expose new functions in purerpc.test_utils ([07b10e1](https://github.com/python-trio/purerpc/commit/07b10e1))
* migrate to pytest ([95c0a8b](https://github.com/python-trio/purerpc/commit/95c0a8b))


### BREAKING CHANGES

* purerpc.test_utils.PureRPCTestCase is removed



## [Release 0.2.0](https://github.com/python-trio/purerpc/compare/v0.1.6...v0.2.0) (2019-02-10)


### Features

* add backend option to Server.serve ([5f47f8e](https://github.com/python-trio/purerpc/commit/5f47f8e))
* add support for Python 3.5 ([a681192](https://github.com/python-trio/purerpc/commit/a681192))
* improved exception handling in test utils ([b1df796](https://github.com/python-trio/purerpc/commit/b1df796))
* migrate to anyio ([746b1c2](https://github.com/python-trio/purerpc/commit/746b1c2))


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
