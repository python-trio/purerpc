//
// Created by Andrew Stepanov on 2019-03-22.
//

#pragma once

#include <stdexcept>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <optional>

#include <nghttp2/nghttp2.h>

#include "headers.h"


namespace grpclib::http2 {

struct DefaultObserver {
  template<class Event>
  void OnEvent(std::unique_ptr<Event> event) {}
};

template<class Observer>
class Connection {
 public:

  explicit Connection(bool client_side, Observer& observer);
  ~Connection();

  void IncrementFlowContorlWindow(int32_t increment, int32_t stream_id = 0);
  int32_t RemoteFlowControlWindow(int32_t stream_id) const;
  int32_t LocalFlowControlWindow(int32_t stream_id) const;
  int32_t MaxInboundFrameSize() const;
  int32_t MaxOutboundFrameSize() const;
  void ClearOutboundDataBuffer();
  std::string DataToSend(std::optional<size_t> amount = std::nullopt);
  void AcknowledgeReceivedData(int32_t acknowledged_size, int32_t stream_id);
  void ReceiveData(const std::string& data);
  void CloseConnection(uint32_t error_code = NGHTTP2_NO_ERROR, const std::string& additional_data = "",
                       std::optional<int32_t> last_stream_id = std::nullopt);
  int32_t GetNextAvailableStreamId();
  void Ping(const std::string& opaque_data);
  void ResetStream(int32_t stream_id, uint32_t error_code);
  void SendHeaders(int32_t stream_id, Headers& headers, bool end_stream = false,
                   std::optional<int32_t> priority_weight = std::nullopt,
                   std::optional<int32_t> priority_depends_on = std::nullopt,
                   std::optional<bool> priority_exclusive = std::nullopt);
  void PushStream(int32_t stream_id, int32_t promised_stream_id, Headers& request_headers);
  void SendData(int32_t stream_id, const std::string& data, bool end_stream = false,
    std::optional<ssize_t> pad_length = std::nullopt);
  void EndStream(int32_t stream_id);
  std::vector<nghttp2_settings_entry> LocalSettings() const;
  void UpdateSettings(const std::vector<nghttp2_settings_entry>& new_settings);
  void InitiateConnection(const std::vector<nghttp2_settings_entry>& settings_overrides = {});

 private:
  static constexpr nghttp2_settings_id kSettingKeys[] {
    NGHTTP2_SETTINGS_HEADER_TABLE_SIZE, NGHTTP2_SETTINGS_ENABLE_PUSH, NGHTTP2_SETTINGS_MAX_CONCURRENT_STREAMS,
    NGHTTP2_SETTINGS_INITIAL_WINDOW_SIZE, NGHTTP2_SETTINGS_MAX_FRAME_SIZE, NGHTTP2_SETTINGS_MAX_HEADER_LIST_SIZE,
    NGHTTP2_SETTINGS_ENABLE_CONNECT_PROTOCOL
  };
  static constexpr nghttp2_settings_entry kInitialSettings[] {
    {NGHTTP2_SETTINGS_HEADER_TABLE_SIZE, 4096},
    {NGHTTP2_SETTINGS_ENABLE_PUSH, static_cast<uint32_t>(-1)},  // this is set to correct value in initiate_connection
    {NGHTTP2_SETTINGS_MAX_CONCURRENT_STREAMS, 100},
    {NGHTTP2_SETTINGS_INITIAL_WINDOW_SIZE, 65536},
    {NGHTTP2_SETTINGS_MAX_FRAME_SIZE, 16384},
    {NGHTTP2_SETTINGS_MAX_HEADER_LIST_SIZE, 1024},
    {NGHTTP2_SETTINGS_ENABLE_CONNECT_PROTOCOL, 0},
  };
  static constexpr size_t kTotalHeadersSizePerStream = 65536;  // 64KB
  struct HeadersParsingState {
    Headers headers;
    size_t total_size;
  };
  struct DataSource {
    size_t pos;
    std::string data;
  };

  template<class Function, class... Args>
  static auto CallNghttpCallback(Function fn, Args... args);
  void RaiseCallbackExceptionIfAny();
  void DrainSessionMemSend();
  void SetCallbacks();
  void SetOption();
  static std::vector<nghttp2_nv> ConvertToNv(Headers& headers);

  int OnBeginHeaders(nghttp2_session *session, const nghttp2_frame *frame);
  int OnHeaders(nghttp2_session *session, const nghttp2_frame *frame, const uint8_t *name, size_t namelen,
                const uint8_t *value, size_t valuelen, uint8_t flags);
  int OnFrameRecv(nghttp2_session *session, const nghttp2_frame *frame);
  int OnDataChunkRecv(nghttp2_session *session, uint8_t flags, int32_t stream_id, const uint8_t *data, size_t len);
  int OnError(nghttp2_session *session, int lib_error_code, const char *msg, size_t len);
  int OnFrameNotSend(nghttp2_session *session, const nghttp2_frame *frame, int lib_error_code);
  int OnInvalidFrameRecv(nghttp2_session *session, const nghttp2_frame *frame, int lib_error_code);
  ssize_t SelectPadding(nghttp2_session *session, const nghttp2_frame *frame, size_t max_payloadlen);
  ssize_t DataSourceReadLength(nghttp2_session *session, uint8_t frame_type, int32_t stream_id,
                               int32_t session_remote_window_size, int32_t stream_remote_window_size,
                               uint32_t remote_max_frame_size);
  static ssize_t DataSourceRead(nghttp2_session *session, int32_t stream_id, uint8_t *buf, size_t length,
                                uint32_t *data_flags, nghttp2_data_source *source, void *user_data);

  Observer& observer_;
  bool client_side_;
  std::exception_ptr exception_;
  nghttp2_session_callbacks *session_callbacks_;
  nghttp2_option *option_;
  nghttp2_session *session_;
  std::unordered_map<const nghttp2_frame *, HeadersParsingState> headers_;
  std::unordered_map<int32_t, std::string> data_;
  std::string data_to_send_;
  std::unordered_map<int32_t, DataSource> data_sources_;
  ssize_t padding_amount_;
};

}  // namespace grpclib::http2


#include "connection_impl.hpp"
