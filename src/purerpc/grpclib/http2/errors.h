//
// Created by Andrew Stepanov on 2019-03-22.
//

#pragma once

#include <optional>
#include <stdexcept>
#include <string>

#include <fmt/format.h>
#include <nghttp2/nghttp2.h>

namespace grpclib::http2 {

struct MacroInfo {
  const char *expression; // #expression
  const char *file;       // __FILE__
  int line;               // __LINE__
};

constexpr int kGeneralError = -1000;

class Nghttp2Error : public std::runtime_error {
public:
  explicit Nghttp2Error(const std::string &message,
                        std::optional<MacroInfo> macro_info = std::nullopt,
                        std::optional<int> lib_error_code = std::nullopt)
      : std::runtime_error(
            GetErrorString(message, lib_error_code, macro_info)) {}

protected:
  virtual int DefaultErrorCode() { return kGeneralError; }

private:
  int GetErrorCodeOrDefault(std::optional<int> lib_error_code) {
    if (lib_error_code) {
      return *lib_error_code;
    } else {
      return DefaultErrorCode();
    }
  }

  std::string GetErrorString(const std::string &message,
                             std::optional<int> lib_error_code_optional,
                             std::optional<MacroInfo> macro_info) {
    int lib_error_code = GetErrorCodeOrDefault(lib_error_code_optional);
    if (lib_error_code == kGeneralError) {
      if (macro_info) {
        return fmt::format("{} (expr: {} at {}:{})", message,
                           macro_info->expression, macro_info->file,
                           macro_info->line);
      } else {
        return fmt::format("{}", message);
      }
    } else {
      if (macro_info) {
        return fmt::format("{}: {} (code: {}, expr: {} at {}:{})",
                           nghttp2_strerror(lib_error_code), message,
                           lib_error_code, macro_info->expression,
                           macro_info->file, macro_info->line);
      } else {
        return fmt::format("{}: {} (code: {})",
                           nghttp2_strerror(lib_error_code), message,
                           lib_error_code);
      }
    }
  }
};

class InvalidArgumentError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INVALID_ARGUMENT; }
};

class BufferError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_BUFFER_ERROR; }
};

class UnsupportedVersionError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_UNSUPPORTED_VERSION; }
};

class WouldBlockError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_WOULDBLOCK; }
};

class ProtocolError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_PROTO; }
};

class InvalidFrameError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INVALID_FRAME; }
};

class EOFError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_EOF; }
};

class DeferredError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_DEFERRED; }
};

class StreamIdNotAvailableError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override {
    return NGHTTP2_ERR_STREAM_ID_NOT_AVAILABLE;
  }
};

class StreamClosedError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_STREAM_CLOSED; }
};

class StreamClosingError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_STREAM_CLOSING; }
};

class StreamShutdownWriteError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_STREAM_SHUT_WR; }
};

class InvalidStreamIdError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INVALID_STREAM_ID; }
};

class InvalidStreamStateError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INVALID_STREAM_STATE; }
};

class DeferredDataExistError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_DEFERRED_DATA_EXIST; }
};

class StartStreamNotAllowedError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override {
    return NGHTTP2_ERR_START_STREAM_NOT_ALLOWED;
  }
};

class GoawayAlreadySentError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_GOAWAY_ALREADY_SENT; }
};

class InvalidHeaderBlockError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INVALID_HEADER_BLOCK; }
};

class InvalidStateError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INVALID_STATE; }
};

class TemporalCallbackFailureError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override {
    return NGHTTP2_ERR_TEMPORAL_CALLBACK_FAILURE;
  }
};

class FrameSizeError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_FRAME_SIZE_ERROR; }
};

class HeaderCompressionError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_HEADER_COMP; }
};

class FlowControlError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_FLOW_CONTROL; }
};

class InsufficientBufferSizeError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INSUFF_BUFSIZE; }
};

class PausedError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_PAUSE; }
};

class TooManyInflightSettingsError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override {
    return NGHTTP2_ERR_TOO_MANY_INFLIGHT_SETTINGS;
  }
};

class PushDisabledError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_PUSH_DISABLED; }
};

class DataExistError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_DATA_EXIST; }
};

class SessionClosingError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_SESSION_CLOSING; }
};

class HttpHeaderError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_HTTP_HEADER; }
};

class HttpMessagingError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_HTTP_MESSAGING; }
};

class RefusedStreamError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_REFUSED_STREAM; }
};

class InternalError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_INTERNAL; }
};

class CancelError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_CANCEL; }
};

class SettingsExpectedError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_SETTINGS_EXPECTED; }
};

class FatalError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_FATAL; }
};

class NoMemoryError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_NOMEM; }
};

class CallbackFailureError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_CALLBACK_FAILURE; }
};

class BadClientMagicError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_BAD_CLIENT_MAGIC; }
};

class FloodedError : public Nghttp2Error {
public:
  using Nghttp2Error::Nghttp2Error;

protected:
  int DefaultErrorCode() override { return NGHTTP2_ERR_FLOODED; }
};

void raise_error_from_code(int lib_error_code, const std::string &message = "",
                           std::optional<MacroInfo> macro_info = std::nullopt);

#define NGHTTP2_ASSERT(expression, message)                                    \
  do {                                                                         \
    auto val = (expression);                                                   \
    if (!val) {                                                                \
      throw grpclib::http2::Nghttp2Error(                                      \
                (message),                                                     \
                grpclib::http2::MacroInfo{ #expression, __FILE__, __LINE__ }); \
    }                                                                          \
  } while (false);

#define NGHTTP2_CHECK_CALL(lib_error_code, message)                            \
  do {                                                                         \
    auto res = (lib_error_code);                                               \
    if (res != 0) {                                                            \
      grpclib::http2::raise_error_from_code(                                   \
          res,                                                                 \
          message,                                                             \
          grpclib::http2::MacroInfo{ #lib_error_code, __FILE__, __LINE__ });   \
    }                                                                          \
  } while (false);

} // namespace grpclib::http2
