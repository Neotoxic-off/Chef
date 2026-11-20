cmake_minimum_required(VERSION 3.25)
project(lru_cache LANGUAGES CXX)

add_library(lru_cache INTERFACE)
target_include_directories(lru_cache INTERFACE include)
target_compile_features(lru_cache INTERFACE cxx_std_20)

include(CTest)
if(BUILD_TESTING)
  add_executable(lru_cache_test tests/lru_cache_test.cpp)
  target_link_libraries(lru_cache_test PRIVATE lru_cache)
  set_target_properties(lru_cache_test PROPERTIES CXX_EXTENSIONS OFF)
  target_compile_options(lru_cache_test PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow>
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->)
  add_test(NAME lru_cache_test COMMAND lru_cache_test)
endif()
