//
// Created by Andrew Stepanov on 2019-03-25.
//

#include "events.h"


#include <fmt/format.h>

#include "utility.h"

std::string grpclib::http2::UnknownFrameReceived::ToString() const {
  return fmt::format("<UnknownFrameReceive>");
  
}

std::string grpclib::http2::ConnectionTerminated::ToString() const {
  return fmt::format("<ConnectionTerminated error_code: {} last_stream_id: {} additional_data: {}>",
                     error_code, last_stream_id, additional_data);
  
}

grpclib::http2::ConnectionTerminated::ConnectionTerminated(uint32_t error_code, int32_t last_stream_id,
                                                           std::string additional_data)
  : error_code(error_code), last_stream_id(last_stream_id), additional_data(std::move(additional_data)) {}

std::string grpclib::http2::WindowUpdated::ToString() const {
  return fmt::format("<WindowUpdated stream_id: {} delta: {}>", stream_id, delta);
}

grpclib::http2::WindowUpdated::WindowUpdated(int32_t stream_id, int32_t delta) : stream_id(stream_id), delta(delta) {}

std::string grpclib::http2::PingReceived::ToString() const {
  return fmt::format("<PingReceived ping_data: {}>", BytesToHex(ping_data));
  
}

grpclib::http2::PingReceived::PingReceived(std::string ping_data) : ping_data(std::move(ping_data)) {}

std::string grpclib::http2::PingAckReceived::ToString() const {
  return fmt::format("<PingAckReceived ping_data: {}>", BytesToHex(ping_data));
  
}

grpclib::http2::PingAckReceived::PingAckReceived(std::string ping_data) : ping_data(std::move(ping_data)) {}

std::string grpclib::http2::PushedStreamReceived::ToString() const {
  return fmt::format("<PushedStreamReceived pushed_stream_id: {} parent_stream_id: {} headers: {}>",
                     pushed_stream_id, parent_stream_id, headers);
  
}

grpclib::http2::PushedStreamReceived::PushedStreamReceived(int32_t pushed_stream_id, int32_t parent_stream_id,
                                                           grpclib::http2::Headers headers)
  : pushed_stream_id(pushed_stream_id), parent_stream_id(parent_stream_id), headers(std::move(headers)) {}

std::string grpclib::http2::RemoteSettingsChanged::ToString() const {
  return fmt::format("<RemoteSettingsChanged changed_settings: {}>", changed_settings);
  
}

grpclib::http2::RemoteSettingsChanged::RemoteSettingsChanged(std::vector<nghttp2_settings_entry> changed_settings)
  : changed_settings(std::move(changed_settings)) {}

std::string grpclib::http2::SettingsAcknowledged::ToString() const {
  return fmt::format("<SettingsAcknowledged changed_settings: {}>", changed_settings);
  
}

grpclib::http2::SettingsAcknowledged::SettingsAcknowledged(std::vector<nghttp2_settings_entry> changed_settings)
  : changed_settings(std::move(changed_settings)) {}

std::string grpclib::http2::StreamReset::ToString() const {
  return fmt::format("<StreamReset stream_id: {} error_code: {} remote_reset: {}>",
                     stream_id, error_code, remote_reset);
  
}

grpclib::http2::StreamReset::StreamReset(int32_t stream_id, uint32_t error_code, bool remote_reset)
  : stream_id(stream_id), error_code(error_code), remote_reset(remote_reset) {}

std::string grpclib::http2::TrailersReceived::ToString() const {
  if (priority_updated) {
    return fmt::format("<TrailersReceived stream_id: {} headers: {} stream_ended: {} priority_updated: {}>",
                       stream_id, headers, stream_ended, *priority_updated);
  } else {
    return fmt::format("<TrailersReceived stream_id: {} headers: {} stream_ended: {}>",
                       stream_id, headers, stream_ended);
  }
  
}

grpclib::http2::TrailersReceived::TrailersReceived(int32_t stream_id, grpclib::http2::Headers headers,
                                                   bool stream_ended,
                                                   std::optional<grpclib::http2::PriorityUpdated> priority_updated)
  : stream_id(stream_id), headers(std::move(headers)), stream_ended(stream_ended),
    priority_updated(priority_updated) {}

std::string grpclib::http2::ResponseReceived::ToString() const {
  if (priority_updated) {
    return fmt::format("<ResponseReceived stream_id: {} headers: {} stream_ended: {} priority_updated: {}>",
                       stream_id, headers, stream_ended, *priority_updated);
  } else {
    return fmt::format("<ResponseReceived stream_id: {} headers: {} stream_ended: {}>",
                       stream_id, headers, stream_ended);
  }
  
}

grpclib::http2::ResponseReceived::ResponseReceived(int32_t stream_id, grpclib::http2::Headers headers,
                                                   bool stream_ended,
                                                   std::optional<grpclib::http2::PriorityUpdated> priority_updated)
  : stream_id(stream_id), headers(std::move(headers)), stream_ended(stream_ended),
    priority_updated(priority_updated) {}

std::string grpclib::http2::RequestReceived::ToString() const {
  if (priority_updated) {
    return fmt::format("<RequestReceived stream_id: {} headers: {} stream_ended: {} priority_updated: {}>",
                       stream_id, headers, stream_ended, *priority_updated);
  } else {
    return fmt::format("<RequestReceived stream_id: {} headers: {} stream_ended: {}>",
                       stream_id, headers, stream_ended);
  }
  
}

grpclib::http2::RequestReceived::RequestReceived(int32_t stream_id, grpclib::http2::Headers headers, bool stream_ended,
                                                 std::optional<grpclib::http2::PriorityUpdated> priority_updated)
  : stream_id(stream_id), headers(std::move(headers)), stream_ended(stream_ended),
    priority_updated(priority_updated) {}

std::string grpclib::http2::PriorityUpdated::ToString() const {
  return fmt::format("<PriorityUpdated stream_id: {} weight: {} depends_on: {} exclusive: {}>",
                     stream_id, weight, depends_on, exclusive);
  
}

grpclib::http2::PriorityUpdated::PriorityUpdated(int32_t stream_id, int32_t weight, int32_t depends_on, bool exclusive)
  : stream_id(stream_id), weight(weight), depends_on(depends_on), exclusive(exclusive) {}

std::string grpclib::http2::DataReceived::ToString() const {
  return fmt::format("<DataReceived stream_id: {} data: {} flow_controlled_length: {} stream_ended: {}>",
                     stream_id, BytesToHex(data), flow_controlled_length, stream_ended);
  
}

grpclib::http2::DataReceived::DataReceived(int32_t stream_id, std::string data, size_t flow_controlled_length,
                                           bool stream_ended)
  : stream_id(stream_id), data(std::move(data)), flow_controlled_length(flow_controlled_length),
    stream_ended(stream_ended) {}

std::string grpclib::http2::StreamEnded::ToString() const {
  return fmt::format("<StreamEnded stream_id: {}>", stream_id);
  
}

grpclib::http2::StreamEnded::StreamEnded(int32_t stream_id) : stream_id(stream_id) {}
