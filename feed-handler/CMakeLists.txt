cmake_minimum_required(VERSION 3.21)
project(itch_feed_handler LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(ITCH_SANITIZE "Build with AddressSanitizer + UndefinedBehaviorSanitizer" OFF)
if(ITCH_SANITIZE)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()

# A complete build uses one reference-index layout. Propagate the definition to all
# consumers: the selected index is a member of the public L3Book class.
set(ITCH_REFERENCE_INDEX "open_addressed" CACHE STRING "L3 reference index implementation")
set_property(CACHE ITCH_REFERENCE_INDEX PROPERTY STRINGS open_addressed std_unordered)
if(ITCH_REFERENCE_INDEX STREQUAL "open_addressed")
  set(ITCH_STD_REFERENCE_INDEX 0)
elseif(ITCH_REFERENCE_INDEX STREQUAL "std_unordered")
  set(ITCH_STD_REFERENCE_INDEX 1)
else()
  message(FATAL_ERROR "ITCH_REFERENCE_INDEX must be open_addressed or std_unordered")
endif()

# One search policy per build; the vector and slab representation stays fixed.
set(ITCH_LEVEL_SEARCH "reverse_linear" CACHE STRING "L3 price-level search policy")
set_property(CACHE ITCH_LEVEL_SEARCH PROPERTY STRINGS reverse_linear binary)
if(ITCH_LEVEL_SEARCH STREQUAL "reverse_linear")
  set(ITCH_BINARY_LEVEL_SEARCH 0)
elseif(ITCH_LEVEL_SEARCH STREQUAL "binary")
  set(ITCH_BINARY_LEVEL_SEARCH 1)
else()
  message(FATAL_ERROR "ITCH_LEVEL_SEARCH must be reverse_linear or binary")
endif()

# Reuse the parent repository's targets, or fetch the pinned engine when built alone.
if(TARGET me AND TARGET me_workloads)
  # Both shared targets are already available from the parent build.
elseif(TARGET me OR TARGET me_workloads)
  message(FATAL_ERROR "The feed handler requires both me and me_workloads targets")
else()
  include(FetchContent)
  FetchContent_Declare(
    matching_engine
    GIT_REPOSITORY https://github.com/Manuelma4/matching-engine.git
    GIT_TAG 01656701c973036d88724fbe2d27fa5b98f55cd4  # matching-engine, stage 2
  )
  FetchContent_MakeAvailable(matching_engine)
endif()

add_library(itch_warnings INTERFACE)
target_compile_options(itch_warnings INTERFACE -Wall -Wextra -Wpedantic -Wshadow -Wconversion)

# Offline transport admission only. The generic parser/receiver has no order-book
# or matching-engine dependency; application validation is a separate header.
add_library(itch_mold src/mold.cpp)
target_include_directories(itch_mold PUBLIC include)
target_link_libraries(itch_mold PRIVATE itch_warnings)

add_library(itch src/framing.cpp src/book.cpp src/replay.cpp src/journal.cpp)
target_include_directories(itch PUBLIC include)
target_compile_definitions(itch PUBLIC ITCH_STD_REFERENCE_INDEX=${ITCH_STD_REFERENCE_INDEX})
target_compile_definitions(itch PUBLIC ITCH_BINARY_LEVEL_SEARCH=${ITCH_BINARY_LEVEL_SEARCH})
target_link_libraries(itch PUBLIC me PRIVATE itch_warnings)

# Synthetic causal queue model: deliberately independent of the wire decoder and
# reconstruction storage until a separately validated historical adapter exists.
add_library(itch_queue src/queue_sim.cpp)
target_include_directories(itch_queue PUBLIC include)
target_link_libraries(itch_queue PRIVATE itch_warnings)

add_executable(itch_queue_sim tools/queue_sim.cpp)
target_link_libraries(itch_queue_sim PRIVATE itch_queue itch_warnings)

add_executable(itch_queue_demo tools/queue_demo.cpp)
target_link_libraries(itch_queue_demo PRIVATE itch_queue itch_warnings)

add_library(itch_window src/queue_window.cpp)
target_include_directories(itch_window PUBLIC include)
target_link_libraries(itch_window PUBLIC itch itch_queue PRIVATE itch_warnings)

add_executable(itch_queue_window tools/queue_window.cpp)
target_link_libraries(itch_queue_window PRIVATE itch_window itch_warnings)

foreach(tool census replay bench snapshots journal_replay storage_bench)
  add_executable(itch_${tool} tools/${tool}.cpp)
  target_link_libraries(itch_${tool} PRIVATE itch itch_warnings)
endforeach()

add_executable(itch_loopback tools/loopback.cpp)
target_link_libraries(itch_loopback PRIVATE itch me_workloads itch_warnings)
