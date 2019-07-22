//
// Created by Andrew Stepanov on 2019-03-25.
//

#include "event.h"

#include <fmt/format.h>

namespace grpclib::grpc {


WindowUpdated::WindowUpdated(int32_t stream_id, int32_t delta)
  : stream_id(stream_id), delta(delta) { }

std::string WindowUpdated::ToString() const {
  return fmt::format("<WindowUpdated stream_id: {} delta: {}>", stream_id, delta);
}

}  // namespace grpclib::grpc