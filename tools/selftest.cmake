# Included by the generated build with -DWIIKIT_EXTRA=<this file>.
add_executable(selftest ${CMAKE_CURRENT_LIST_DIR}/selftest.cpp)
target_link_libraries(selftest recomp)
