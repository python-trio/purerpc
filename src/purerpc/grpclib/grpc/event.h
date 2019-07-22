//
// Created by Andrew Stepanov on 2019-03-25.
//

#pragma once

#include <cstdint>
#include <string>
#include <optional>
#include <utility>
#include <chrono>
#include <http2/headers.h>
#include <unordered_map>


namespace grpclib::grpc {

struct Event {
  virtual ~Event() = default;
};


struct WindowUpdated: public Event {
  int32_t stream_id;
  int32_t delta;

  WindowUpdated(int32_t stream_id, int32_t delta);
  std::string ToString() const;
};


struct RequestReceived: public Event {
  int32_t stream_id;
  std::string scheme;
  std::string service_name;
  std::string method_name;
  std::string content_type;
  std::optional<std::string> authority;
  std::optional<std::chrono::microseconds> timeout;
  std::optional<std::string> message_type;
  std::optional<std::string> message_encoding;
  std::optional<std::string> message_accept_encoding;
  std::optional<std::string> user_agent;
  http2::Headers custom_metadata;

  RequestReceived(int32_t stream_id, std::string scheme, std::string service_name, std::string method_name,
                  std::string content_type)
    : stream_id(stream_id), scheme(std::move(scheme)), service_name(std::move(service_name)),
      method_name(std::move(method_name)), content_type(std::move(content_type)) {
  }

  static RequestReceived ParseFromStreamIdAndHeaders(int32_t stream_id, std::unordered_multimap<std::string, std::string>& ) {

  }



};


struct MessageReceived: public Event {

};


struct RequestEnded: public Event {

};


struct ResponseReceived: public Event {

};


struct ResponseEnded: public Event {

};

}  // namespace grpclib::grpc
