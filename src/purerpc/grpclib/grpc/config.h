//
// Created by Andrew Stepanov on 2019-03-25.
//

#pragma once
#include <string>
#include <optional>

namespace grpclib::grpc {

class GRPCConfiguration {
 private:
  static constexpr size_t kDefaultMaxMessageLength = 4194304;  // 4MB
 public:
  GRPCConfiguration(bool client_side, std::optional<std::string> server_string, std::optional<std::string> user_agent,
                    std::optional<std::string> message_encoding, std::optional<std::string> message_accept_encoding,
                    size_t max_message_length = kDefaultMaxMessageLength);


  bool ClientSide() const;

  const std::optional<std::string>& ServerString() const;

  const std::optional<std::string>& UserAgent() const;

  const std::optional<std::string>& MessageEncoding() const;

  const std::optional<std::string>& MessageAcceptEncoding() const;

  size_t MaxMessageLength() const;

 private:
  bool client_side_;
  std::optional<std::string> server_string_;
  std::optional<std::string> user_agent_;
  std::optional<std::string> message_encoding_;
  std::optional<std::string> message_accept_encoding_;
  size_t max_message_length_;
};

}  // namespace grpclib::grpc