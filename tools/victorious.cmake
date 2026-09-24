# The port's targets, included by the generated build with
# -DWIIKIT_EXTRA=<this file>: the native self-test, and the game's own layer
# linked into wiiboot.
include(${CMAKE_CURRENT_LIST_DIR}/selftest.cmake)
target_sources(wiiboot PRIVATE ${CMAKE_CURRENT_LIST_DIR}/victorious.cpp)
