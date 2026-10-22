cmake_minimum_required(VERSION 3.20)
project(matching_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(ME_SANITIZE "Build with AddressSanitizer + UndefinedBehaviorSanitizer" OFF)

add_library(me_warnings INTERFACE)
target_compile_options(me_warnings INTERFACE -Wall -Wextra -Wpedantic -Wshadow -Wconversion)

if(ME_SANITIZE)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()

add_library(me src/book_v1.cpp src/book.cpp)
target_include_directories(me PUBLIC include)
target_link_libraries(me PRIVATE me_warnings)

add_executable(me_bench bench/main.cpp bench/workloads.cpp)
target_link_libraries(me_bench PRIVATE me me_warnings)
