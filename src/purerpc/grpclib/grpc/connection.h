//
// Created by Andrew Stepanov on 2019-03-25.
//

#pragma once
#include <chrono>
#include "config.h"
#include "http2/connection.hpp"

namespace grpclib::grpc {


class GRPCConnection: private http2::DefaultObserver {
  using HttpConnection = http2::Connection<GRPCConnection>;
  friend class http2::Connection<GRPCConnection>;
 public:
  explicit GRPCConnection(GRPCConfiguration config);
  void InitiateConnection();
  std::string DataToSend(std::optional<size_t> amount = std::nullopt);
  void ReceiveData(const std::string& data);
  int32_t FlowControlWindow(int32_t stream_id) const;
  void ResetStream(int32_t stream_id);
  void AcknowledgeReceivedData(int32_t stream_id, int32_t flow_controlled_length);
  void SendData(int32_t stream_id, const std::string& data, bool end_stream = false);
  int32_t GetNextAvaiableStreamId() const;
  void StartRequest(int32_t stream_id, const std::string& scheme, const std::string& service_name,
    const std::string& method_name, std::optional<std::string> message_type = std::nullopt,
    std::optional<std::string> authority = std::nullopt,
    std::optional<std::chrono::microseconds> timeout = std::nullopt, const std::string& content_suffix_type = "",
    const http2::Headers& custom_metadata = {});
  void EndRequest(int32_t stream_id);
  void StartResponse(int32_t stream_id, const std::string& content_type_suffix = "",
    const http2::Headers& custom_metadata = {});
  void RespondStatus(int32_t stream_id, /*TODO: Status status*/ const std::string& content_type_suffix = "",
    const http2::Headers& custom_metadata = {});
  void EndResponse(int32_t stream_id, /*TODO: Status status*/ const http2::Headers& custom_metadata = {});

 private:

  using http2::DefaultObserver::OnEvent;
  void OnEvent(std::unique_ptr<http2::RequestReceived> event);
  void OnEvent(std::unique_ptr<http2::ResponseReceived> event);
  void OnEvent(std::unique_ptr<http2::TrailersReceived> event);
  void OnEvent(std::unique_ptr<http2::DataReceived> event);
  void OnEvent(std::unique_ptr<http2::WindowUpdated> event);
  void OnEvent(std::unique_ptr<http2::RemoteSettingsChanged> event);
  void OnEvent(std::unique_ptr<http2::StreamEnded> event);


  GRPCConfiguration config_;
  HttpConnection http_connection_;

};

}  // namespace grpclib::grpc
