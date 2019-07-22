//
// Created by Andrew Stepanov on 2019-03-25.
//

#include "connection.h"

namespace grpclib::grpc {

GRPCConnection::GRPCConnection(GRPCConfiguration config)
  : config_(std::move(config)), http_connection_(config.ClientSide(), *this) {

}

void GRPCConnection::OnEvent(std::unique_ptr<http2::RequestReceived> event) {
  DefaultObserver::OnEvent(std::move(event));
}

void GRPCConnection::OnEvent(std::unique_ptr<http2::ResponseReceived> event) {
  DefaultObserver::OnEvent(std::move(event));
}

void GRPCConnection::OnEvent(std::unique_ptr<http2::TrailersReceived> event) {
  DefaultObserver::OnEvent(std::move(event));
}

void GRPCConnection::OnEvent(std::unique_ptr<http2::DataReceived> event) {
  DefaultObserver::OnEvent(std::move(event));
}

void GRPCConnection::OnEvent(std::unique_ptr<http2::WindowUpdated> event) {
  DefaultObserver::OnEvent(std::move(event));
}

void GRPCConnection::OnEvent(std::unique_ptr<http2::RemoteSettingsChanged> event) {
  DefaultObserver::OnEvent(std::move(event));
}

void GRPCConnection::OnEvent(std::unique_ptr<http2::StreamEnded> event) {
  DefaultObserver::OnEvent(std::move(event));
}

}  // namespace grpclib::grpc
