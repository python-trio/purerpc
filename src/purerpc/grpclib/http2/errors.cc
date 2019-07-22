#include "errors.h"

namespace grpclib::http2 {
void raise_error_from_code(int lib_error_code, const std::string &message, std::optional<MacroInfo> macro_info) {
  switch (lib_error_code) {

    case NGHTTP2_ERR_FLOODED:
      throw FloodedError(message, macro_info);
    case NGHTTP2_ERR_BAD_CLIENT_MAGIC:
      throw BadClientMagicError(message, macro_info);
    case NGHTTP2_ERR_CALLBACK_FAILURE:
      throw CallbackFailureError(message, macro_info);
    case NGHTTP2_ERR_NOMEM:
      throw NoMemoryError(message, macro_info);
    case NGHTTP2_ERR_FATAL:
      throw FatalError(message, macro_info);
    case NGHTTP2_ERR_SETTINGS_EXPECTED:
      throw SettingsExpectedError(message, macro_info);
    case NGHTTP2_ERR_CANCEL:
      throw CancelError(message, macro_info);
    case NGHTTP2_ERR_INTERNAL:
      throw InternalError(message, macro_info);
    case NGHTTP2_ERR_REFUSED_STREAM:
      throw InternalError(message, macro_info);
    case NGHTTP2_ERR_HTTP_MESSAGING:
      throw HttpMessagingError(message, macro_info);
    case NGHTTP2_ERR_HTTP_HEADER:
      throw HttpHeaderError(message, macro_info);
    case NGHTTP2_ERR_SESSION_CLOSING:
      throw SessionClosingError(message, macro_info);
    case NGHTTP2_ERR_DATA_EXIST:
      throw DataExistError(message, macro_info);
    case NGHTTP2_ERR_PUSH_DISABLED:
      throw PushDisabledError(message, macro_info);
    case NGHTTP2_ERR_TOO_MANY_INFLIGHT_SETTINGS:
      throw TooManyInflightSettingsError(message, macro_info);
    case NGHTTP2_ERR_PAUSE:
      throw PausedError(message, macro_info);
    case NGHTTP2_ERR_INSUFF_BUFSIZE:
      throw InsufficientBufferSizeError(message, macro_info);
    case NGHTTP2_ERR_FLOW_CONTROL:
      throw FlowControlError(message, macro_info);
    case NGHTTP2_ERR_HEADER_COMP:
      throw HeaderCompressionError(message, macro_info);
    case NGHTTP2_ERR_FRAME_SIZE_ERROR:
      throw FrameSizeError(message, macro_info);
    case NGHTTP2_ERR_TEMPORAL_CALLBACK_FAILURE:
      throw TemporalCallbackFailureError(message, macro_info);
    case NGHTTP2_ERR_INVALID_STATE:
      throw InvalidStateError(message, macro_info);
    case NGHTTP2_ERR_INVALID_HEADER_BLOCK:
      throw InvalidHeaderBlockError(message, macro_info);
    case NGHTTP2_ERR_GOAWAY_ALREADY_SENT:
      throw GoawayAlreadySentError(message, macro_info);
    case NGHTTP2_ERR_START_STREAM_NOT_ALLOWED:
      throw StartStreamNotAllowedError(message, macro_info);
    case NGHTTP2_ERR_DEFERRED_DATA_EXIST:
      throw DeferredDataExistError(message, macro_info);
    case NGHTTP2_ERR_INVALID_STREAM_STATE:
      throw InvalidStreamStateError(message, macro_info);
    case NGHTTP2_ERR_INVALID_STREAM_ID:
      throw InvalidStreamIdError(message, macro_info);
    case NGHTTP2_ERR_STREAM_SHUT_WR:
      throw StreamShutdownWriteError(message, macro_info);
    case NGHTTP2_ERR_STREAM_CLOSING:
      throw StreamClosingError(message, macro_info);
    case NGHTTP2_ERR_STREAM_CLOSED:
      throw StreamClosedError(message, macro_info);
    case NGHTTP2_ERR_STREAM_ID_NOT_AVAILABLE:
      throw StreamIdNotAvailableError(message, macro_info);
    case NGHTTP2_ERR_EOF:
      throw EOFError(message, macro_info);
    case NGHTTP2_ERR_INVALID_FRAME:
      throw InvalidFrameError(message, macro_info);
    case NGHTTP2_ERR_PROTO:
      throw ProtocolError(message, macro_info);
    case NGHTTP2_ERR_WOULDBLOCK:
      throw WouldBlockError(message, macro_info);
    case NGHTTP2_ERR_UNSUPPORTED_VERSION:
      throw UnsupportedVersionError(message, macro_info);
    case NGHTTP2_ERR_BUFFER_ERROR:
      throw BufferError(message, macro_info);
    case NGHTTP2_ERR_INVALID_ARGUMENT:
      throw InvalidArgumentError(message, macro_info);
    case NGHTTP2_ERR_DEFERRED:
      throw DeferredError(message, macro_info);
    default:
      throw Nghttp2Error(message, macro_info, lib_error_code);

  }
}
}  // namespace grpclib::http2