//
// Created by Andrew Stepanov on 2019-03-25.
//

#include "config.h"

namespace grpclib::grpc {

GRPCConfiguration::GRPCConfiguration(bool client_side, std::optional<std::string> server_string,
                                     std::optional<std::string> user_agent, std::optional<std::string> message_encoding,
                                     std::optional<std::string> message_accept_encoding, size_t max_message_length)
  : client_side_(client_side), server_string_(std::move(server_string)), user_agent_(std::move(user_agent)),
    message_encoding_(std::move(message_encoding)), message_accept_encoding_(std::move(message_accept_encoding)),
    max_message_length_(max_message_length) {}

bool GRPCConfiguration::ClientSide() const {
  return client_side_;
}

const std::optional<std::string>& GRPCConfiguration::ServerString() const {
  return server_string_;
}

const std::optional<std::string>& GRPCConfiguration::UserAgent() const {
  return user_agent_;
}

const std::optional<std::string>& GRPCConfiguration::MessageEncoding() const {
  return message_encoding_;
}

const std::optional<std::string>& GRPCConfiguration::MessageAcceptEncoding() const {
  return message_accept_encoding_;
}

size_t GRPCConfiguration::MaxMessageLength() const {
  return max_message_length_;
}

};