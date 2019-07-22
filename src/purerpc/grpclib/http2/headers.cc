//
// Created by Andrew Stepanov on 2019-03-25.
//

#include "headers.h"
#include <fmt/format.h>

namespace grpclib::http2 {

std::string HeaderValuePair::ToString() const {
  return fmt::format(R"(("{}", "{}"))", name, value);
}

HeaderValuePair::HeaderValuePair(std::string name, std::string value)
  : name(std::move(name)), value(std::move(value)) {}

}