cmake_minimum_required(VERSION 3.21)
project(matching_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(PROJECT_IS_TOP_LEVEL)
  set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
  if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
  endif()
endif()

option(ME_SANITIZE "Build with AddressSanitizer + UndefinedBehaviorSanitizer" OFF)
option(ME_BUILD_BENCH "Build the benchmark" ${PROJECT_IS_TOP_LEVEL})

add_library(me_warnings INTERFACE)
target_compile_options(me_warnings INTERFACE -Wall -Wextra -Wpedantic -Wshadow -Wconversion)

if(ME_SANITIZE)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()

add_library(me src/book_v1.cpp src/book.cpp)
target_include_directories(me PUBLIC include)
target_link_libraries(me PRIVATE me_warnings)

# Deterministic order-flow regimes, shared with projects that replay them.
add_library(me_workloads bench/workloads.cpp)
target_include_directories(me_workloads PUBLIC bench)
target_link_libraries(me_workloads PUBLIC me PRIVATE me_warnings)

if(ME_BUILD_BENCH)
  add_executable(me_bench bench/main.cpp)
  target_link_libraries(me_bench PRIVATE me_workloads me_warnings)
endif()
