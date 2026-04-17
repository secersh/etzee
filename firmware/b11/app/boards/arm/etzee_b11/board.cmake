board_runner_args(nrfjprog "--nrf-family=NRF52" "--softreset")
include(${ZEPHYR_BASE}/boards/common/uf2.board.cmake)
include(${ZEPHYR_BASE}/boards/common/nrfjprog.board.cmake)

if(CONFIG_HTOYTO_ENABLED)
  message(STATUS "Including htoyto protocol")
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/src/htoyto)
endif()
