//
// Created by Andrew Stepanov on 2019-03-22.
//

#pragma once
#include <string>
#include <vector>


namespace grpclib::http2 {

struct HeaderValuePair {
  std::string name;
  std::string value;

  HeaderValuePair(std::string name, std::string value);
  std::string ToString() const;
};

using Headers = std::vector<HeaderValuePair>;

}  // namespace grpclib::http2
