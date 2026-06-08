zephyr_library()
zephyr_library_sources(htoyto.c)
zephyr_library_sources(events/events.c)
zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)
