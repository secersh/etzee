#pragma once

#include <stdbool.h>

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

/* Returns the role of this node as configured in the device tree. */
htoyto_role_t htoyto_get_role(void);

/* Returns true if a remote node is currently established (post-EST). */
bool htoyto_is_connected(void);

/* Send a TLK frame. target_node NULL broadcasts to all. Returns UNSUPPORTED if
   the remote replies with DKW, TIMEOUT if ACK not received within the timeout. */
htoyto_status_t htoyto_send_tlk(const char *target_node, const char *payload);
