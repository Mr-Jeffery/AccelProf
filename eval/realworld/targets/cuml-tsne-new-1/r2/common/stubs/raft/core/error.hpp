// R2 stub (T21c): RAFT_FAIL / RAFT_EXPECTS as printf-style exceptions (used by checked_arithmetic.hpp and barnes_hut_tsne.cuh).
#pragma once
#include <cstdio>
#include <stdexcept>
#include <string>
namespace raft {
struct exception : std::runtime_error {
  using std::runtime_error::runtime_error;
};
}  // namespace raft
#define RAFT_FAIL(fmt, ...)                                                 \
  do {                                                                      \
    char _buf[512];                                                         \
    std::snprintf(_buf, sizeof(_buf), "RAFT failure: " fmt, ##__VA_ARGS__); \
    throw raft::exception(_buf);                                            \
  } while (0)
#define RAFT_EXPECTS(cond, fmt, ...)                \
  do {                                              \
    if (!(cond)) RAFT_FAIL(fmt, ##__VA_ARGS__);     \
  } while (0)
