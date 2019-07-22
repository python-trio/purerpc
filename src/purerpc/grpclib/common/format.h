//
// Created by Andrew Stepanov on 2019-03-25.
//

#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <array>

#include <nghttp2/nghttp2.h>
#include <fmt/format.h>

namespace fmt {

template<class T>
class has_to_string {
 private:
  template<class U> static decltype(std::declval<U>().ToString(), std::true_type()) test(int);
  template<class> static std::false_type test(...);
  using result = decltype(test<T>(0));

 public:
  static constexpr bool value = result::value;
};

template<class T>
class has_begin {
 private:
  template<class U> static decltype(std::begin(std::declval<U>()), std::true_type()) test(int);
  template<class> static std::false_type test(...);
  using result = decltype(test<T>(0));

 public:
  static constexpr bool value = result::value;
};

template<class T>
class has_end {
 private:
  template<class U> static decltype(std::end(std::declval<U>()), std::true_type()) test(int);
  template<class> static std::false_type test(...);
  using result = decltype(test<T>(0));

 public:
  static constexpr bool value = result::value;
};


template<class T>
class has_begin_and_end {
 public:
  static constexpr bool value = has_begin<T>::value && has_end<T>::value;
};


template<class T, class Char>
struct formatter<T, Char, typename std::enable_if<has_to_string<T>::value>::type>
                                  : formatter<basic_string_view<Char>, Char> {
  template<class Context>
  auto format(const T& value, Context& ctx) {
    return formatter<basic_string_view<Char>, Char>::format(value.ToString(), ctx);
  }
};

template<class T, char prefix, char suffix, class Char = char>
struct iterable_formatter : formatter<basic_string_view<Char>, Char> {
  template<class Context>
  auto format(const T& value, Context& ctx) {
    std::string prefix_str, suffix_str;
    if constexpr (prefix == '{') {
      prefix_str = "{{";
    } else {
      prefix_str += prefix;
    }
    if constexpr (suffix == '}') {
      suffix_str = "}}";
    } else {
      suffix_str += suffix;
    }
    std::string format_string = prefix_str + "{}" + suffix_str;
    return formatter<basic_string_view<Char>, Char>::format(fmt::format(format_string,
      fmt::join(std::begin(value), std::end(value), ", ")), ctx);
  }
};

template<class T, class Char>
struct formatter<std::vector<T>, Char>: iterable_formatter<std::vector<T>, '[', ']', Char> {};

template<class T, size_t N, class Char>
struct formatter<std::array<T, N>, Char>: iterable_formatter<std::array<T, N>, '[', ']', Char> {};

template<class K, class V, class Char>
struct formatter<std::unordered_map<K, V>, Char>: iterable_formatter<std::unordered_map<K, V>, '{', '}', Char> {};

template<class T, class Char>
struct formatter<std::unordered_set<T>, Char>: iterable_formatter<std::unordered_set<T>, '{', '}', Char> {};


template<class U, class V, class Char>
struct formatter<std::pair<U, V>, Char>: formatter<basic_string_view<Char>, Char> {
  template<class Context>
  auto format(const std::pair<U, V>& value, Context& ctx) {
    return formatter<basic_string_view<Char>, Char>::format(fmt::format("{} : {}", value.first, value.second), ctx);
  }
};


template<class... Args, class Char>
struct formatter<std::tuple<Args...>, Char>: formatter<basic_string_view<Char>, Char> {
  template<size_t... Is>
  auto call(const std::string& format, const std::tuple<Args...>& args, std::index_sequence<Is...>) {
    return fmt::format(format, std::get<Is>(args)...);
  }

  template<class Context>
  auto format(const std::tuple<Args...>& value, Context& ctx) {
    std::string format = fmt::format("({})", fmt::join(std::vector<std::string>(sizeof...(Args), "{}"), ", "));
    return formatter<basic_string_view<Char>, Char>::format(call(format, value, std::index_sequence_for<Args...>()),
      ctx);
  }
};

template<class FormatContext>
auto format(const nghttp2_settings_entry& entry, FormatContext& ctx) {
  return format_to(ctx.out(), "<nghttp2_settings_entry settings_id: {} value: {}>", entry.settings_id, entry.value);
}

template<class Char>
struct formatter<nghttp2_settings_entry, Char>: formatter<basic_string_view<Char>, Char> {
  template<class Context>
  auto format(const nghttp2_settings_entry& value, Context& ctx) {
    return formatter<basic_string_view<Char>, Char>::format(fmt::format("{} : {}", value.settings_id, value.value), ctx);
  }
};

}
