// R2 stub (T21c): logging is disabled.  tsne.h needs rapids_logger::level_enum; utils.cuh timer macros call ML::default_logger().should_log(...).
#pragma once
#include <cuml/common/export.hpp>
namespace rapids_logger {
enum class level_enum : int { trace = 0, debug = 1, info = 2, warn = 3, error = 4, critical = 5, off = 6 };
}
namespace ML {
struct stub_logger {
  bool should_log(rapids_logger::level_enum) const { return false; }
};
inline stub_logger& default_logger()
{
  static stub_logger l;
  return l;
}
}  // namespace ML
#define CUML_LOG_DEBUG(...) ((void)0)
#define CUML_LOG_INFO(...) ((void)0)
#define CUML_LOG_WARN(...) ((void)0)
