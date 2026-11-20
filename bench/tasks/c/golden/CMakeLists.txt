cmake_minimum_required(VERSION 3.25)
project(ringbuf LANGUAGES C)

add_library(ringbuf src/ringbuf.c)
target_include_directories(ringbuf PUBLIC include)
target_compile_features(ringbuf PUBLIC c_std_17)
set_target_properties(ringbuf PROPERTIES C_EXTENSIONS OFF)
target_compile_options(ringbuf PRIVATE
  $<$<C_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic -Wconversion -Wshadow
    -Wstrict-prototypes -Wmissing-prototypes -Wformat=2 -Wnull-dereference>
  $<$<C_COMPILER_ID:MSVC>:/W4>)

include(CTest)
if(BUILD_TESTING)
  add_executable(ringbuf_test tests/ringbuf_test.c)
  target_link_libraries(ringbuf_test PRIVATE ringbuf)
  add_test(NAME ringbuf_test COMMAND ringbuf_test)
endif()
