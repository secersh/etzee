#pragma once

#include <device.h>

typedef enum {
    HTOYTO_ROLE_ORIGIN,
    HTOYTO_ROLE_BRIDGE,
    HTOYTO_ROLE_TERMINAL,
} htoyto_role_t;

typedef enum {
    HTOYTO_STATUS_OK = 0,
    HTOYTO_STATUS_ERROR,
    HTOYTO_STATUS_TIMEOUT,
    HTOYTO_STATUS_UNSUPPORTED,
} htoyto_status_t;

/**
 * Initialize htoyto protocol instance.
 *
 * @param dev UART device used for communication.
 * @return 0 on success or negative errno on failure.
 */
int htoyto_init(const struct device *dev);

/**
 * Process UART data received from the device.
 * Intended to be called from UART callback or polling loop.
 *
 * @param dev UART device that triggered the read.
 */
void htoyto_on_uart_data(const struct device *dev);

/**
 * Send a TLK (Talk) frame over UART to a given node or broadcast.
 *
 * @param target_node Target node-id string (NULL for broadcast).
 * @param payload Null-terminated message payload.
 * @return htoyto_status_t value indicating result.
 */
htoyto_status_t htoyto_send_tlk(const char *target_node, const char *payload);
