#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "http2/connection.hpp"

namespace py = pybind11;
using namespace grpclib::http2;
using namespace py::literals;

class H2Connection : public Connection<H2Connection> {
public:
  explicit H2Connection(bool client_side) : Connection(client_side, *this) {}

  std::vector<std::unique_ptr<Event>> ReceiveData(const std::string &data) {
    Connection::ReceiveData(data);
    std::vector<std::unique_ptr<Event>> result;
    using std::swap;
    swap(result, events_);
    return result;
  }

  template <class Event> void OnEvent(std::unique_ptr<Event> event) {
    events_.push_back(std::move(event));
  }

private:
  std::vector<std::unique_ptr<Event>> events_;
};

PYBIND11_MODULE(_grpclib_bindings, m) {
  m.doc() = "grpclib bindings";

  py::enum_<nghttp2_settings_id>(m, "SettingCodes")
      .value("HEADER_TABLE_SIZE",
             nghttp2_settings_id::NGHTTP2_SETTINGS_HEADER_TABLE_SIZE)
      .value("ENABLE_PUSH", nghttp2_settings_id::NGHTTP2_SETTINGS_ENABLE_PUSH)
      .value("MAX_CONCURRENT_STREAMS",
             nghttp2_settings_id::NGHTTP2_SETTINGS_MAX_CONCURRENT_STREAMS)
      .value("INITIAL_WINDOW_SIZE",
             nghttp2_settings_id::NGHTTP2_SETTINGS_INITIAL_WINDOW_SIZE)
      .value("MAX_FRAME_SIZE",
             nghttp2_settings_id::NGHTTP2_SETTINGS_MAX_FRAME_SIZE)
      .value("MAX_HEADER_LIST_SIZE",
             nghttp2_settings_id::NGHTTP2_SETTINGS_MAX_HEADER_LIST_SIZE)
      .value("ENABLE_CONNECT_PROTOCOL",
             nghttp2_settings_id::NGHTTP2_SETTINGS_ENABLE_CONNECT_PROTOCOL);

  py::enum_<nghttp2_error_code>(m, "ErrorCodes")
      .value("NO_ERROR", nghttp2_error_code::NGHTTP2_NO_ERROR)
      .value("PROTOCOL_ERROR", nghttp2_error_code::NGHTTP2_PROTOCOL_ERROR)
      .value("INTERNAL_ERROR", nghttp2_error_code::NGHTTP2_INTERNAL_ERROR)
      .value("FLOW_CONTROL_ERROR",
             nghttp2_error_code::NGHTTP2_FLOW_CONTROL_ERROR)
      .value("SETTINGS_TIMEOUT", nghttp2_error_code::NGHTTP2_SETTINGS_TIMEOUT)
      .value("STREAM_CLOSED", nghttp2_error_code::NGHTTP2_STREAM_CLOSED)
      .value("FRAME_SIZE_ERROR", nghttp2_error_code::NGHTTP2_FRAME_SIZE_ERROR)
      .value("REFUSED_STREAM", nghttp2_error_code::NGHTTP2_REFUSED_STREAM)
      .value("CANCEL", nghttp2_error_code::NGHTTP2_CANCEL)
      .value("COMPRESSION_ERROR", nghttp2_error_code::NGHTTP2_COMPRESSION_ERROR)
      .value("CONNECT_ERROR", nghttp2_error_code::NGHTTP2_CONNECT_ERROR)
      .value("ENHANCE_YOUR_CALM", nghttp2_error_code::NGHTTP2_ENHANCE_YOUR_CALM)
      .value("INADEQUATE_SECURITY",
             nghttp2_error_code::NGHTTP2_INADEQUATE_SECURITY)
      .value("HTTP_1_1_REQUIRED",
             nghttp2_error_code::NGHTTP2_HTTP_1_1_REQUIRED);

  py::register_exception<Nghttp2Error>(m, "Nghttp2Error");

  py::register_exception<FloodedError>(m, " FloodedError");

  py::register_exception<BadClientMagicError>(m, " BadClientMagicError");

  py::register_exception<CallbackFailureError>(m, " CallbackFailureError");

  py::register_exception<NoMemoryError>(m, " NoMemoryError");

  py::register_exception<FatalError>(m, " FatalError");

  py::register_exception<SettingsExpectedError>(m, " SettingsExpectedError");

  py::register_exception<CancelError>(m, " CancelError");

  py::register_exception<InternalError>(m, " InternalError");

  py::register_exception<InternalError>(m, " InternalError");

  py::register_exception<HttpMessagingError>(m, " HttpMessagingError");

  py::register_exception<HttpHeaderError>(m, " HttpHeaderError");

  py::register_exception<SessionClosingError>(m, " SessionClosingError");

  py::register_exception<DataExistError>(m, " DataExistError");

  py::register_exception<PushDisabledError>(m, " PushDisabledError");

  py::register_exception<TooManyInflightSettingsError>(
      m, " TooManyInflightSettingsError");

  py::register_exception<PausedError>(m, " PausedError");

  py::register_exception<InsufficientBufferSizeError>(
      m, " InsufficientBufferSizeError");

  py::register_exception<FlowControlError>(m, " FlowControlError");

  py::register_exception<HeaderCompressionError>(m, " HeaderCompressionError");

  py::register_exception<FrameSizeError>(m, " FrameSizeError");

  py::register_exception<TemporalCallbackFailureError>(
      m, " TemporalCallbackFailureError");

  py::register_exception<InvalidStateError>(m, " InvalidStateError");

  py::register_exception<InvalidHeaderBlockError>(m,
                                                  " InvalidHeaderBlockError");

  py::register_exception<GoawayAlreadySentError>(m, " GoawayAlreadySentError");

  py::register_exception<StartStreamNotAllowedError>(
      m, " StartStreamNotAllowedError");

  py::register_exception<DeferredDataExistError>(m, " DeferredDataExistError");

  py::register_exception<InvalidStreamStateError>(m,
                                                  " InvalidStreamStateError");

  py::register_exception<InvalidStreamIdError>(m, " InvalidStreamIdError");

  py::register_exception<StreamShutdownWriteError>(m,
                                                   " StreamShutdownWriteError");

  py::register_exception<StreamClosingError>(m, " StreamClosingError");

  py::register_exception<StreamClosedError>(m, " StreamClosedError");

  py::register_exception<StreamIdNotAvailableError>(
      m, " StreamIdNotAvailableError");

  py::register_exception<EOFError>(m, " EOFError");

  py::register_exception<InvalidFrameError>(m, " InvalidFrameError");

  py::register_exception<ProtocolError>(m, " ProtocolError");

  py::register_exception<WouldBlockError>(m, " WouldBlockError");

  py::register_exception<UnsupportedVersionError>(m,
                                                  " UnsupportedVersionError");

  py::register_exception<BufferError>(m, " BufferError");

  py::register_exception<InvalidArgumentError>(m, " InvalidArgumentError");

  py::register_exception<DeferredError>(m, " DeferredError");

  py::class_<HeaderValuePair>(m, "HeaderValuePair")
      .def(py::init([](py::tuple tuple) {
        if (tuple.size() != 2) {
          throw std::domain_error(
              fmt::format("Expected tuple of size 2, got: {}", tuple.size()));
        }
        return std::make_unique<HeaderValuePair>(tuple[0].cast<std::string>(),
                                                 tuple[1].cast<std::string>());
      }))
      .def_readwrite("name", &HeaderValuePair::name)
      .def_readwrite("value", &HeaderValuePair::value)
      .def("__iter__", [](HeaderValuePair& pair) {
        return py::make_iterator(
            reinterpret_cast<std::string*>(&pair),
            reinterpret_cast<std::string*>(&pair + 1));
      }, py::keep_alive<0, 1>());

  py::implicitly_convertible<py::tuple, HeaderValuePair>();

  py::class_<nghttp2_settings_entry>(m, "SettingsEntry")
      .def(py::init([](py::tuple tuple) {
        if (tuple.size() != 2) {
          throw std::domain_error(
              fmt::format("Expected tuple of size 2, got: {}", tuple.size()));
        }
        return nghttp2_settings_entry{tuple[0].cast<int32_t>(),
                                      tuple[1].cast<uint32_t>()};
      }))
      .def_readwrite("settings_id", &nghttp2_settings_entry::settings_id)
      .def_readwrite("value", &nghttp2_settings_entry::value);

  py::implicitly_convertible<py::tuple, nghttp2_settings_entry>();

  py::class_<Event>(m, "Event");

  py::class_<StreamEnded, Event>(m, "StreamEnded")
      .def_readonly("stream_id", &StreamEnded::stream_id)
      .def("__repr__", &StreamEnded::ToString);

  py::class_<DataReceived, Event>(m, "DataReceived")
      .def_readonly("stream_id", &DataReceived::stream_id)
      .def_property_readonly("data", [](DataReceived& event) {
        return py::bytes(event.data);
      })
      .def_readonly("flow_controlled_length",
                    &DataReceived::flow_controlled_length)
      .def_readonly("stream_ended", &DataReceived::stream_ended)
      .def("__repr__", &DataReceived::ToString);

  py::class_<PriorityUpdated, Event>(m, "PriorityUpdated")
      .def_readonly("stream_id", &PriorityUpdated::stream_id)
      .def_readonly("weight", &PriorityUpdated::weight)
      .def_readonly("depends_on", &PriorityUpdated::depends_on)
      .def_readonly("exclusive", &PriorityUpdated::exclusive)
      .def("__repr__", &PriorityUpdated::ToString);

  py::class_<RequestReceived, Event>(m, "RequestReceived")
      .def_readonly("stream_id", &RequestReceived::stream_id)
      .def_readonly("headers", &RequestReceived::headers)
      .def_readonly("stream_ended", &RequestReceived::stream_ended)
      .def_readonly("priority_updated", &RequestReceived::priority_updated)
      .def("__repr__", &RequestReceived::ToString);

  py::class_<ResponseReceived, Event>(m, "ResponseReceived")
      .def_readonly("stream_id", &ResponseReceived::stream_id)
      .def_readonly("headers", &ResponseReceived::headers)
      .def_readonly("stream_ended", &ResponseReceived::stream_ended)
      .def_readonly("priority_updated", &ResponseReceived::priority_updated)
      .def("__repr__", &ResponseReceived::ToString);

  py::class_<TrailersReceived, Event>(m, "TrailersReceived")
      .def_readonly("stream_id", &TrailersReceived::stream_id)
      .def_readonly("headers", &TrailersReceived::headers)
      .def_readonly("stream_ended", &TrailersReceived::stream_ended)
      .def_readonly("priority_updated", &TrailersReceived::priority_updated)
      .def("__repr__", &TrailersReceived::ToString);

  py::class_<StreamReset, Event>(m, "StreamReset")
      .def_readonly("stream_id", &StreamReset::stream_id)
      .def_readonly("error_code", &StreamReset::error_code)
      .def_readonly("remote_reset", &StreamReset::remote_reset)
      .def("__repr__", &StreamReset::ToString);

  py::class_<SettingsAcknowledged, Event>(m, "SettingsAcknowledged")
      .def_readonly("changed_settings", &SettingsAcknowledged::changed_settings)
      .def("__repr__", &SettingsAcknowledged::ToString);

  py::class_<RemoteSettingsChanged, Event>(m, "RemoteSettingsChanged")
      .def_readonly("changed_settings",
                    &RemoteSettingsChanged::changed_settings)
      .def("__repr__", &RemoteSettingsChanged::ToString);

  py::class_<PushedStreamReceived, Event>(m, "PushedStreamReceived")
      .def_readonly("pushed_stream_id", &PushedStreamReceived::pushed_stream_id)
      .def_readonly("parent_stream_id", &PushedStreamReceived::parent_stream_id)
      .def_readonly("headers", &PushedStreamReceived::headers)
      .def("__repr__", &PushedStreamReceived::ToString);

  py::class_<PingAckReceived, Event>(m, "PingAckReceived")
      .def_readonly("ping_data", &PingAckReceived::ping_data)
      .def("__repr__", &PingAckReceived::ToString);

  py::class_<PingReceived, Event>(m, "PingReceived")
      .def_readonly("ping_data", &PingReceived::ping_data)
      .def("__repr__", &PingReceived::ToString);

  py::class_<WindowUpdated, Event>(m, "WindowUpdated")
      .def_readonly("stream_id", &WindowUpdated::stream_id)
      .def_readonly("delta", &WindowUpdated::delta)
      .def("__repr__", &WindowUpdated::ToString);

  py::class_<ConnectionTerminated, Event>(m, "ConnectionTerminated")
      .def_readonly("error_code", &ConnectionTerminated::error_code)
      .def_readonly("last_stream_id", &ConnectionTerminated::last_stream_id)
      .def_readonly("additional_data", &ConnectionTerminated::additional_data)
      .def("__repr__", &ConnectionTerminated::ToString);

  py::class_<UnknownFrameReceived, Event>(m, "UnknownFrameReceived")
      .def("__repr__", &UnknownFrameReceived::ToString);

  py::class_<H2Connection>(m, "H2Connection")
      .def(py::init<bool>(), "client_side"_a)
      .def("incremet_flow_control_window",
           &H2Connection::IncrementFlowContorlWindow, "increment"_a,
           "stream_id"_a = 0)
      .def("remote_flow_control_window", &H2Connection::RemoteFlowControlWindow,
           "stream_id"_a)
      .def("local_flow_control_window", &H2Connection::LocalFlowControlWindow,
           "stream_id"_a)
      .def_property_readonly("max_inbound_frame_size",
                             &H2Connection::MaxInboundFrameSize)
      .def_property_readonly("max_outbound_frame_size",
                             &H2Connection::MaxOutboundFrameSize)
      .def("clear_outbound_data_buffer", &H2Connection::ClearOutboundDataBuffer)
      .def("data_to_send",
           [](H2Connection *self, std::optional<size_t> amount) {
             return py::bytes(self->DataToSend(amount));
           },
           "amount"_a = std::nullopt)
      .def("acknowledge_received_data", &H2Connection::AcknowledgeReceivedData,
           "acknowledged_size"_a, "stream_id"_a)
      .def("receive_data", &H2Connection::ReceiveData, "data"_a)
      .def("close_connection", &H2Connection::CloseConnection,
           "error_code"_a = static_cast<uint32_t>(NGHTTP2_NO_ERROR),
           "additional_data"_a = "", "last_stream_id"_a = std::nullopt)
      .def("get_next_available_stream_id",
           &H2Connection::GetNextAvailableStreamId)
      .def("ping", &H2Connection::Ping, "opaque_data"_a)
      .def("reset_stream", &H2Connection::ResetStream, "stream_id"_a,
           "error_code"_a)
      .def("send_headers", &H2Connection::SendHeaders, "stream_id"_a,
           "headers"_a, "end_stream"_a = false,
           "priority_weight"_a = std::nullopt,
           "priority_depends_on"_a = std::nullopt,
           "priority_exclusive"_a = std::nullopt)
      .def("push_stream", &H2Connection::PushStream, "stream_id"_a,
           "promised_stream_id"_a, "request_headers"_a)
      .def("send_data", &H2Connection::SendData, "stream_id"_a, "data"_a,
           "end_stream"_a = false, "pad_length"_a = std::nullopt)
      .def("end_stream", &H2Connection::EndStream, "stream_id"_a)
      .def_property_readonly("local_settings", &H2Connection::LocalSettings)
      .def("update_settings", &H2Connection::UpdateSettings, "new_settings"_a)
      .def("initiate_connection", &H2Connection::InitiateConnection,
           "settings_overrides"_a = std::vector<nghttp2_settings_entry>{});
}
