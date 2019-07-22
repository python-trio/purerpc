//
// Created by Andrew Stepanov on 2019-03-22.
//

#pragma once

#include <cstdint>
#include <vector>
#include <optional>

#include <nghttp2/nghttp2.h>

#include "headers.h"
#include <common/format.h>


namespace grpclib::http2 {


struct Event {
  virtual ~Event() = default;
};


struct StreamEnded: public Event {
  int32_t stream_id;

  explicit StreamEnded(int32_t stream_id);
  std::string ToString() const;
};

struct DataReceived: public Event {
  int32_t stream_id;
  std::string data;
  size_t flow_controlled_length;
  bool stream_ended;

  DataReceived(int32_t stream_id, std::string data, size_t flow_controlled_length, bool stream_ended);
  std::string ToString() const;
};

struct PriorityUpdated: public Event {
  int32_t stream_id;
  int32_t weight;
  int32_t depends_on;
  bool exclusive;

  PriorityUpdated(int32_t stream_id, int32_t weight, int32_t depends_on, bool exclusive);
  std::string ToString() const;
};

struct RequestReceived: public Event {
  int32_t stream_id;
  Headers headers;
  bool stream_ended;
  std::optional<PriorityUpdated> priority_updated;

  RequestReceived(int32_t stream_id, Headers headers, bool stream_ended,
                  std::optional<PriorityUpdated> priority_updated);
  std::string ToString() const;

};

struct ResponseReceived: public Event {
  int32_t stream_id;
  Headers headers;
  bool stream_ended;
  std::optional<PriorityUpdated> priority_updated;

  ResponseReceived(int32_t stream_id, Headers headers, bool stream_ended,
                   std::optional<PriorityUpdated> priority_updated);
  std::string ToString() const;
};

struct TrailersReceived: public Event {
  int32_t stream_id;
  Headers headers;
  bool stream_ended;
  std::optional<PriorityUpdated> priority_updated;

  TrailersReceived(int32_t stream_id, Headers headers, bool stream_ended,
                   std::optional<PriorityUpdated> priority_updated);
  std::string ToString() const;
};

struct StreamReset: public Event {
  int32_t stream_id;
  uint32_t error_code;
  bool remote_reset;

  StreamReset(int32_t stream_id, uint32_t error_code, bool remote_reset);
  std::string ToString() const;
};

struct SettingsAcknowledged: public Event {
  std::vector<nghttp2_settings_entry> changed_settings;

  explicit SettingsAcknowledged(std::vector<nghttp2_settings_entry> changed_settings);
  std::string ToString() const;
};

struct RemoteSettingsChanged: public Event {
  std::vector<nghttp2_settings_entry> changed_settings;

  explicit RemoteSettingsChanged(std::vector<nghttp2_settings_entry> changed_settings);
  std::string ToString() const;
};

struct PushedStreamReceived: public Event {
  int32_t pushed_stream_id;
  int32_t parent_stream_id;
  Headers headers;

  PushedStreamReceived(int32_t pushed_stream_id, int32_t parent_stream_id, Headers headers);
  std::string ToString() const;
};

struct PingAckReceived: public Event {
  std::string ping_data;

  explicit PingAckReceived(std::string ping_data);
  std::string ToString() const;
};

struct PingReceived: public Event {
  std::string ping_data;

  explicit PingReceived(std::string ping_data);
  std::string ToString() const;
};

struct WindowUpdated: public Event {
  int32_t stream_id;
  int32_t delta;

  WindowUpdated(int32_t stream_id, int32_t delta);
  std::string ToString() const;
};

struct ConnectionTerminated: public Event {
  uint32_t error_code;
  int32_t last_stream_id;
  std::string additional_data;

  ConnectionTerminated(uint32_t error_code, int32_t last_stream_id, std::string additional_data);
  std::string ToString() const;
};

struct UnknownFrameReceived: public Event {
  UnknownFrameReceived() = default;

  std::string ToString() const;
};


}  // namespace grpclib::http2
