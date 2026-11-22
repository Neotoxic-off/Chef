cmake_minimum_required(VERSION 3.25)
project(token_bucket LANGUAGES CXX)

set(WARNINGS
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow>
  $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->)

add_library(token_bucket src/token_bucket.cpp)
target_include_directories(token_bucket PUBLIC include)
target_compile_features(token_bucket PUBLIC cxx_std_20)
set_target_properties(token_bucket PROPERTIES CXX_EXTENSIONS OFF)
target_compile_options(token_bucket PRIVATE ${WARNINGS})

include(CTest)
if(BUILD_TESTING)
  add_executable(token_bucket_test tests/token_bucket_test.cpp)
  target_link_libraries(token_bucket_test PRIVATE token_bucket)
  set_target_properties(token_bucket_test PROPERTIES CXX_EXTENSIONS OFF)
  target_compile_options(token_bucket_test PRIVATE ${WARNINGS})
  add_test(NAME token_bucket_test COMMAND token_bucket_test)
endif()
