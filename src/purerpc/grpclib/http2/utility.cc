//
// Created by Andrew Stepanov on 2019-03-25.
//

#include "utility.h"

#include <fmt/format.h>


namespace grpclib::http2 {

std::string BytesToHex(const std::string &data) {
  size_t num_bytes_to_display = std::min(static_cast<size_t>(16), data.size());
  std::string formatted_data("0x");
  for (size_t idx = 0; idx < num_bytes_to_display; ++idx) {
    formatted_data += fmt::format("{:X}", static_cast<uint8_t>(data[idx]));
  }
  if (num_bytes_to_display < data.size()) {
    formatted_data += "...";
  }
  return formatted_data;
}

}  // namespace grpclib::http2
