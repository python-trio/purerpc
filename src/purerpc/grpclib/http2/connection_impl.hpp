//
// Created by Andrew Stepanov on 2019-03-22.
//

#include <tuple>
#include <utility>

#include "events.h"
#include "errors.h"
#include "connection.hpp"


namespace grpclib::http2 {


template<class Observer>
Connection<Observer>::Connection(bool client_side, Observer& observer): observer_(observer), client_side_(client_side) {
  NGHTTP2_CHECK_CALL(nghttp2_session_callbacks_new(&session_callbacks_), "failed to create callback struct");
  SetCallbacks();

  NGHTTP2_CHECK_CALL(nghttp2_option_new(&option_), "failed to create option struct");
  SetOption();

  if (client_side) {
    NGHTTP2_CHECK_CALL(nghttp2_session_client_new2(&session_, session_callbacks_, this, option_),
      "failed to create client session");
  } else {
    NGHTTP2_CHECK_CALL(nghttp2_session_server_new2(&session_, session_callbacks_, this, option_),
      "failed to create server session");
  }
}

template<class Observer>
Connection<Observer>::~Connection() {
  if (session_callbacks_ != nullptr) {
    nghttp2_session_callbacks_del(session_callbacks_);
  }

  if (session_ != nullptr) {
    nghttp2_session_del(session_);
  }

  if (option_ != nullptr) {
    nghttp2_option_del(option_);
  }
}


template<class Object, class Method, class Tuple, size_t... Index>
auto CallRest(Object *obj, Method fn, const Tuple &args, std::integer_sequence<size_t, Index...>) {
  return (obj->*fn)(std::get<Index>(args)...);
}


template<class Observer>
template<class Function, class... Args>
auto Connection<Observer>::CallNghttpCallback(Function fn, Args... args) {
  constexpr size_t split_index = sizeof...(args) - 1;
  auto args_tuple = std::make_tuple(args...);

  void *user_data = std::get<split_index>(args_tuple);
  auto connection_ptr = reinterpret_cast<Connection*>(user_data);

  using ReturnType = decltype(CallRest(connection_ptr, fn, args_tuple, std::make_index_sequence<split_index>()));

  try {
    return CallRest(connection_ptr, fn, args_tuple, std::make_index_sequence<split_index>());
  } catch (...) {
    connection_ptr->exception_ = std::current_exception();
    return static_cast<ReturnType>(0);
  }
}

template<class Observer>
void Connection<Observer>::RaiseCallbackExceptionIfAny() {
  if (exception_) {
    auto copy = exception_;
    exception_ = nullptr;
    std::rethrow_exception(copy);
  }
}

template<class Observer>
void Connection<Observer>::SetCallbacks() {
  nghttp2_session_callbacks_set_on_begin_headers_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::OnBeginHeaders, args...);
    });

  nghttp2_session_callbacks_set_on_header_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::OnHeaders, args...);
    });

  nghttp2_session_callbacks_set_on_frame_recv_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::OnFrameRecv, args...);
    });

  nghttp2_session_callbacks_set_on_data_chunk_recv_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::OnDataChunkRecv, args...);
    });

  nghttp2_session_callbacks_set_error_callback2(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::OnError, args...);
    });

  nghttp2_session_callbacks_set_on_frame_not_send_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::OnFrameNotSend, args...);
    });

  nghttp2_session_callbacks_set_on_invalid_frame_recv_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::OnInvalidFrameRecv, args...);
    });

  nghttp2_session_callbacks_set_select_padding_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::SelectPadding, args...);
    });

  nghttp2_session_callbacks_set_data_source_read_length_callback(
    session_callbacks_, [](auto... args) {
      return CallNghttpCallback(&Connection::DataSourceReadLength, args...);
    });




}

template<class Observer>
void Connection<Observer>::SetOption() {
  nghttp2_option_set_no_auto_window_update(option_, 1);
}

template<class Observer>
int Connection<Observer>::OnBeginHeaders(nghttp2_session *session, const nghttp2_frame *frame) {
  headers_[frame] = {{}, 0};
  return 0;
}

template<class Observer>
int Connection<Observer>::OnHeaders(nghttp2_session *session, const nghttp2_frame *frame, const uint8_t *name,
                                    size_t namelen, const uint8_t *value, size_t valuelen, uint8_t flags) {
  headers_[frame].total_size += namelen + valuelen;
  if (headers_[frame].total_size > kTotalHeadersSizePerStream) {
    headers_.erase(frame);
    return NGHTTP2_ERR_TEMPORAL_CALLBACK_FAILURE;
  }
  headers_[frame].headers.emplace_back(
    std::string(reinterpret_cast<const char *>(name), namelen),
    std::string(reinterpret_cast<const char *>(value), valuelen)
  );
  return 0;
}

template<class Observer>
int Connection<Observer>::OnFrameRecv(nghttp2_session *session, const nghttp2_frame *frame) {
  int32_t stream_id = frame->hd.stream_id;
  bool end_flag = (frame->hd.flags & NGHTTP2_FLAG_END_STREAM) != 0;
  bool ack_flag = (frame->hd.flags & NGHTTP2_FLAG_ACK) != 0;


  switch (frame->hd.type) {
    case NGHTTP2_DATA: {
      size_t data_len = data_[stream_id].size() + frame->data.padlen;
      auto ptr = std::make_unique<DataReceived>(stream_id, std::move(data_[stream_id]), data_len, end_flag);
      data_.erase(stream_id);
      observer_.OnEvent(std::move(ptr));
      break;
    }

    case NGHTTP2_HEADERS: {
      switch (frame->headers.cat) {
        // TODO: change std::nullopt to something meaningful
        case NGHTTP2_HCAT_REQUEST:
          observer_.OnEvent(std::make_unique<RequestReceived>(
            stream_id, std::move(headers_[frame].headers), end_flag, std::nullopt));
          break;
        case NGHTTP2_HCAT_RESPONSE:
        case NGHTTP2_HCAT_PUSH_RESPONSE:
          observer_.OnEvent(std::make_unique<ResponseReceived>(
            stream_id, std::move(headers_[frame].headers), end_flag, std::nullopt));
          break;
        case NGHTTP2_HCAT_HEADERS:
          observer_.OnEvent(std::make_unique<TrailersReceived>(
            stream_id, std::move(headers_[frame].headers), end_flag, std::nullopt));
          break;
      }
      headers_.erase(frame);
      break;
    }

    case NGHTTP2_PRIORITY: {
      observer_.OnEvent(std::make_unique<PriorityUpdated>(stream_id, frame->priority.pri_spec.weight,
        frame->priority.pri_spec.stream_id, frame->priority.pri_spec.exclusive));
      break;
    }

    case NGHTTP2_RST_STREAM: {
      observer_.OnEvent(std::make_unique<StreamReset>(stream_id, frame->rst_stream.error_code, true));
      break;
    }

    case NGHTTP2_SETTINGS: {
      if (ack_flag) {
        // TODO: acknowledge correct settings (make Settings class instead of map)
        observer_.OnEvent(std::make_unique<SettingsAcknowledged>(
          std::vector<nghttp2_settings_entry>(frame->settings.iv, frame->settings.iv + frame->settings.niv)));
      } else {
        observer_.OnEvent(std::make_unique<RemoteSettingsChanged>(
          std::vector<nghttp2_settings_entry>(frame->settings.iv, frame->settings.iv + frame->settings.niv)));
      }
      break;
    }

    case NGHTTP2_PUSH_PROMISE: {
      observer_.OnEvent(std::make_unique<PushedStreamReceived>(
        frame->push_promise.promised_stream_id, stream_id, std::move(headers_[frame].headers)));
      headers_.erase(frame);
      break;
    }

    case NGHTTP2_PING: {
      std::string data(reinterpret_cast<const char*>(frame->ping.opaque_data), 8);
      if (ack_flag) {
        observer_.OnEvent(std::make_unique<PingAckReceived>(std::move(data)));
      } else {
        observer_.OnEvent(std::make_unique<PingReceived>(std::move(data)));
      }
      break;
    }

    case NGHTTP2_WINDOW_UPDATE: {
      observer_.OnEvent(std::make_unique<WindowUpdated>(stream_id, frame->window_update.window_size_increment));
      break;
    }

    case NGHTTP2_GOAWAY: {
      std::string opaque_data(reinterpret_cast<char*>(frame->goaway.opaque_data), frame->goaway.opaque_data_len);
      observer_.OnEvent(std::make_unique<ConnectionTerminated>(frame->goaway.error_code, frame->goaway.last_stream_id,
        std::move(opaque_data)));
      break;
    }

    default: {
      observer_.OnEvent(std::make_unique<UnknownFrameReceived>());
      break;
    }
  }

  if (end_flag) {
    observer_.OnEvent(std::make_unique<StreamEnded>(stream_id));
  }
  return 0;
}

template<class Observer>
int Connection<Observer>::OnDataChunkRecv(nghttp2_session *session, uint8_t flags, int32_t stream_id, const uint8_t *data,
                                     size_t len) {
  data_[stream_id] += std::string(reinterpret_cast<const char*>(data), len);
  return 0;
}

template<class Observer>
int Connection<Observer>::OnError(nghttp2_session *session, int lib_error_code, const char *msg, size_t len) {
  raise_error_from_code(lib_error_code, "OnError: " + std::string(msg, len));
  return 0;
}

template<class Observer>
int Connection<Observer>::OnFrameNotSend(nghttp2_session *session, const nghttp2_frame *frame, int lib_error_code) {
  raise_error_from_code(lib_error_code, "OnFrameNotSend");
  return 0;
}

template<class Observer>
int Connection<Observer>::OnInvalidFrameRecv(nghttp2_session *session, const nghttp2_frame *frame, int lib_error_code) {
  raise_error_from_code(lib_error_code, "OnInvalidFrameRecv");
  return 0;
}

template<class Observer>
void Connection<Observer>::IncrementFlowContorlWindow(int32_t increment, int32_t stream_id) {
  NGHTTP2_CHECK_CALL(nghttp2_submit_window_update(session_, NGHTTP2_FLAG_NONE, stream_id, increment),
    "failed to submit window update");
}

template<class Observer>
int32_t Connection<Observer>::MaxInboundFrameSize() const {
  return nghttp2_session_get_local_settings(session_, NGHTTP2_SETTINGS_MAX_FRAME_SIZE);
}

template<class Observer>
int32_t Connection<Observer>::MaxOutboundFrameSize() const {
  return nghttp2_session_get_remote_settings(session_, NGHTTP2_SETTINGS_MAX_FRAME_SIZE);
}

template<class Observer>
int32_t Connection<Observer>::RemoteFlowControlWindow(int32_t stream_id) const {
  return std::min(
    nghttp2_session_get_stream_local_window_size(session_, stream_id),
    nghttp2_session_get_local_window_size(session_)
  );
}

template<class Observer>
int32_t Connection<Observer>::LocalFlowControlWindow(int32_t stream_id) const {
  return std::min(
    nghttp2_session_get_stream_remote_window_size(session_, stream_id),
    nghttp2_session_get_remote_window_size(session_)
  );
}

template<class Observer>
void Connection<Observer>::ClearOutboundDataBuffer() {
  data_to_send_.clear();
}

template<class Observer>
std::string Connection<Observer>::DataToSend(std::optional<size_t> amount) {
  if (amount) {
    size_t result_size = std::min(*amount, data_to_send_.size());
    std::string result(data_to_send_.begin(), data_to_send_.begin() + result_size);
    data_to_send_.erase(data_to_send_.begin(), data_to_send_.begin() + result_size);
    return result;
  } else {
    std::string result;
    using std::swap;
    swap(data_to_send_, result);
    return result;
  }
}

template<class Observer>
void Connection<Observer>::DrainSessionMemSend() {
  while (true) {
    const uint8_t* data_ptr;
    ssize_t num_bytes = nghttp2_session_mem_send(session_, &data_ptr);
    if (num_bytes < 0) {
      raise_error_from_code(num_bytes, "mem send failed");
    }
    if (num_bytes == 0) {
      break;
    }
    data_to_send_ += std::string(reinterpret_cast<const char*>(data_ptr), num_bytes);
  }

  RaiseCallbackExceptionIfAny();
}

template<class Observer>
void Connection<Observer>::AcknowledgeReceivedData(int32_t acknowledged_size, int32_t stream_id) {
  NGHTTP2_CHECK_CALL(nghttp2_session_consume(session_, stream_id, acknowledged_size), "failed to consume data");
}

template<class Observer>
void Connection<Observer>::ReceiveData(const std::string &data) {
  NGHTTP2_ASSERT(nghttp2_session_mem_recv(session_, reinterpret_cast<const uint8_t*>(data.c_str()),
    data.size()) == static_cast<ssize_t>(data.size()), "pause encountered in OnHeader or OnDataChunkRecv");
  DrainSessionMemSend();
}

template<class Observer>
void Connection<Observer>::CloseConnection(uint32_t error_code, const std::string& additional_data,
                                           std::optional<int32_t> last_stream_id) {
  if (!last_stream_id) {
    *last_stream_id = nghttp2_session_get_last_proc_stream_id(session_);
  }

  NGHTTP2_CHECK_CALL(nghttp2_submit_goaway(session_, NGHTTP2_FLAG_NONE, *last_stream_id, error_code,
    reinterpret_cast<const uint8_t*>(additional_data.c_str()), additional_data.size()), "submit goaway failed");
  DrainSessionMemSend();
}

template<class Observer>
int32_t Connection<Observer>::GetNextAvailableStreamId() {
  int32_t stream_id = nghttp2_session_get_next_stream_id(session_);
  if (stream_id == (1 << 31)) {
    throw Nghttp2Error("no available streams");
  }
  return stream_id;
}

template<class Observer>
void Connection<Observer>::Ping(const std::string& opaque_data) {
  if (opaque_data.size() != 8) {
    throw std::domain_error("expected string of length 8");
  }
  // TODO: can add optional boolean ack to acknowledge ping frames manually (should also enable this via
  //  nghttp2_option_set_no_auto_ping_ack())
  NGHTTP2_CHECK_CALL(nghttp2_submit_ping(session_, NGHTTP2_FLAG_NONE,
    reinterpret_cast<const uint8_t*>(opaque_data.c_str())), "submit ping failed");
  DrainSessionMemSend();
}

template<class Observer>
void Connection<Observer>::ResetStream(int32_t stream_id, uint32_t error_code) {
  NGHTTP2_ASSERT(nghttp2_session_find_stream(session_, stream_id) == nullptr, "no such stream");
  NGHTTP2_CHECK_CALL(nghttp2_submit_rst_stream(session_, NGHTTP2_FLAG_NONE, stream_id, error_code),
    "submit rst stream failed");
  DrainSessionMemSend();
}

template<class Observer>
 std::vector<nghttp2_nv> Connection<Observer>::ConvertToNv(Headers& headers) {
  std::vector<nghttp2_nv> result;
  for (auto& header: headers) {
    result.push_back(nghttp2_nv{
      reinterpret_cast<uint8_t*>(&header.name[0]),
      reinterpret_cast<uint8_t*>(&header.value[0]),
      header.name.size(),
      header.value.size(),
      NGHTTP2_NV_FLAG_NONE
    });
  }
  return result;
}

template<class Observer>
void Connection<Observer>::SendHeaders(int32_t stream_id, Headers &headers, bool end_stream,
                                       std::optional<int32_t> priority_weight,
                                       std::optional<int32_t> priority_depends_on,
                                       std::optional<bool> priority_exclusive) {
  nghttp2_priority_spec priority_spec;
  nghttp2_priority_spec_default_init(&priority_spec);
  if (priority_weight) {
    priority_spec.weight = *priority_weight;
  }
  if (priority_depends_on) {
    priority_spec.stream_id = *priority_depends_on;
  }
  if (priority_exclusive) {
    priority_spec.exclusive = *priority_exclusive;
  }

  std::vector<nghttp2_nv> nva = ConvertToNv(headers);

  int32_t ret_val = 0;
  if (nghttp2_session_find_stream(session_, stream_id) == nullptr) {
    int32_t next_stream_id = GetNextAvailableStreamId();
    if (next_stream_id > stream_id) {
      throw Nghttp2Error("stream id too low error");
    }
    NGHTTP2_CHECK_CALL(nghttp2_session_set_next_stream_id(session_, stream_id), "set next stream id failed");
    ret_val = stream_id;
    stream_id = -1;
  }

  uint8_t flags = (end_stream ? NGHTTP2_FLAG_END_STREAM : NGHTTP2_FLAG_NONE);

  NGHTTP2_ASSERT(nghttp2_submit_headers(session_, flags, stream_id, &priority_spec, nva.data(), nva.size(),
    nullptr) == ret_val, "submit headers failed");
  DrainSessionMemSend();
}

template<class Observer>
void Connection<Observer>::PushStream(int32_t stream_id, int32_t promised_stream_id, Headers &request_headers) {
  std::vector<nghttp2_nv> nva = ConvertToNv(request_headers);

  NGHTTP2_ASSERT(nghttp2_session_find_stream(session_, promised_stream_id) == nullptr,
    "promised stream id already exists");

  int32_t next_available_stream_id = GetNextAvailableStreamId();
  if (next_available_stream_id > promised_stream_id) {
    throw Nghttp2Error("stream id too low error");
  }
  NGHTTP2_CHECK_CALL(nghttp2_session_set_next_stream_id(session_, promised_stream_id), "set next stream id failed");
  NGHTTP2_ASSERT(nghttp2_submit_push_promise(session_, NGHTTP2_FLAG_NONE, stream_id, nva.data(), nva.size(),
    nullptr) == promised_stream_id, "submit push promise failed");
  DrainSessionMemSend();
}

template<class Observer>
void
Connection<Observer>::SendData(int32_t stream_id, const std::string& data, bool end_stream,
                               std::optional<ssize_t> pad_length) {
  if (pad_length && !(0 <= *pad_length && *pad_length <= 255)) {
    throw std::domain_error("pad_length should be between 0 and 255");
  }

  uint8_t flags = (end_stream ? NGHTTP2_FLAG_END_STREAM : NGHTTP2_FLAG_NONE);

  if (static_cast<ssize_t>(data.size()) > MaxOutboundFrameSize()) {
    throw Nghttp2Error("frame too large");
  }
  if (static_cast<ssize_t>(data.size()) > LocalFlowControlWindow(stream_id)) {
    throw Nghttp2Error("flow control error");
  }

  data_sources_[stream_id] = { 0, data };
  nghttp2_data_provider data_provider;
  data_provider.source.ptr = &data_sources_[stream_id];
  data_provider.read_callback = &Connection::DataSourceRead;

  if (pad_length) {
    padding_amount_ = 1 + *pad_length;
  }
  NGHTTP2_CHECK_CALL(nghttp2_submit_data(session_, flags, stream_id, &data_provider), "submit data failed");
  padding_amount_ = 0;
  DrainSessionMemSend();
}

template<class Observer>
ssize_t
Connection<Observer>::SelectPadding(nghttp2_session *session, const nghttp2_frame *frame, size_t max_payloadlen) {
  if (frame->hd.type == NGHTTP2_DATA) {
    return std::min(frame->hd.length + padding_amount_, max_payloadlen);
  }
  return frame->hd.length;
}

template<class Observer>
ssize_t Connection<Observer>::DataSourceReadLength(nghttp2_session *session, uint8_t frame_type, int32_t stream_id,
                                                   int32_t session_remote_window_size,
                                                   int32_t stream_remote_window_size, uint32_t remote_max_frame_size) {

  return std::min(
    std::min(
      static_cast<ssize_t>(session_remote_window_size),
      static_cast<ssize_t>(stream_remote_window_size)),
    static_cast<ssize_t>(remote_max_frame_size));
}

template<class Observer>
ssize_t Connection<Observer>::DataSourceRead(nghttp2_session *session, int32_t stream_id, uint8_t *buf, size_t length,
                                             uint32_t *data_flags, nghttp2_data_source *source, void *user_data) {
  auto conn = reinterpret_cast<Connection*>(user_data);
  DataSource& data_source = conn->data_sources_[stream_id];
  const std::string& data = data_source.data;
  size_t& pos = data_source.pos;
  size_t data_to_copy = std::min(length, data.size() - pos);
  std::copy(data.begin() + pos, data.begin() + pos + data_to_copy, buf);
  pos += data_to_copy;
  if (pos >= data.size()) {
    *data_flags |= NGHTTP2_DATA_FLAG_EOF;
    conn->data_sources_.erase(stream_id);  // data_source, data and pos point to freed memory from here
  }
  return data_to_copy;
}

template<class Observer>
void Connection<Observer>::EndStream(int32_t stream_id) {
  SendData(stream_id, "", true);
}

template<class Observer>
std::vector<nghttp2_settings_entry> Connection<Observer>::LocalSettings() const {
  std::vector<nghttp2_settings_entry> result;
  for (nghttp2_settings_id key: kSettingKeys) {
    nghttp2_settings_entry entry { key, nghttp2_session_get_local_settings(session_, key) };
    result.push_back(entry);
  }
  return result;
}

template<class Observer>
void Connection<Observer>::UpdateSettings(const std::vector<nghttp2_settings_entry> &new_settings) {
  NGHTTP2_CHECK_CALL(nghttp2_submit_settings(session_, NGHTTP2_FLAG_NONE, new_settings.data(), new_settings.size()),
    "submit settings failed");
  DrainSessionMemSend();
}

template<class Observer>
void Connection<Observer>::InitiateConnection(const std::vector<nghttp2_settings_entry> &settings_overrides) {
  std::unordered_map<nghttp2_settings_id, uint32_t> settings;
  for (auto& entry : kInitialSettings) {
    settings[static_cast<nghttp2_settings_id>(entry.settings_id)] = entry.value;
  }
  settings[NGHTTP2_SETTINGS_ENABLE_PUSH] = client_side_;
  for (auto& entry : settings_overrides) {
    settings[static_cast<nghttp2_settings_id>(entry.settings_id)] = entry.value;
  }

  std::vector<nghttp2_settings_entry> settings_to_update;
  settings_to_update.reserve(settings.size());
  for (auto& entry : settings) {
    settings_to_update.push_back({entry.first, entry.second});
  }
  UpdateSettings(settings_to_update);
}

}  // namespace grpclib::http2
