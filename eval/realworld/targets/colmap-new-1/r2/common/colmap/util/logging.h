// T21c include shim (not an upstream file) standing in for colmap/util/logging.h, which needs glog and Boost-free-but-glog-internal macros.
// Only the macros the copied colmap headers and patch_match_cuda.cu use are provided: LOG(severity), THROW_CHECK*, CHECK*; messages go to stderr.
#pragma once

#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace colmap_stub {
struct LogMsg {
  std::ostringstream os;
  bool fatal;
  explicit LogMsg(bool f = false) : fatal(f) {}
  template <typename T> LogMsg& operator<<(const T& v) { os << v; return *this; }
  ~LogMsg() noexcept(false) {
    std::cerr << os.str() << std::endl;
    if (fatal) throw std::runtime_error(os.str());
  }
};
}  // namespace colmap_stub

#define LOG(severity) ::colmap_stub::LogMsg(#severity[0] == 'F')
#define VLOG(n) ::colmap_stub::LogMsg(false)

#define THROW_CHECK(cond) \
  if (cond) {} else ::colmap_stub::LogMsg(true) << "Check failed: " #cond " "
#define THROW_CHECK_OP(op, a, b) THROW_CHECK((a)op(b))
#define THROW_CHECK_EQ(a, b) THROW_CHECK_OP(==, a, b)
#define THROW_CHECK_NE(a, b) THROW_CHECK_OP(!=, a, b)
#define THROW_CHECK_LE(a, b) THROW_CHECK_OP(<=, a, b)
#define THROW_CHECK_LT(a, b) THROW_CHECK_OP(<, a, b)
#define THROW_CHECK_GE(a, b) THROW_CHECK_OP(>=, a, b)
#define THROW_CHECK_GT(a, b) THROW_CHECK_OP(>, a, b)

#define CHECK(cond) THROW_CHECK(cond)
#define CHECK_EQ(a, b) THROW_CHECK_EQ(a, b)
#define CHECK_NE(a, b) THROW_CHECK_NE(a, b)
#define CHECK_LE(a, b) THROW_CHECK_LE(a, b)
#define CHECK_LT(a, b) THROW_CHECK_LT(a, b)
#define CHECK_GE(a, b) THROW_CHECK_GE(a, b)
#define CHECK_GT(a, b) THROW_CHECK_GT(a, b)
