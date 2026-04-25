#pragma once

#include <zmk/event_manager.h>

enum htoyto_event_type {
    HTOYTO_EVENT_NODE_ADDED,
    HTOYTO_EVENT_NODE_ADD_FAILED,
    HTOYTO_EVENT_NODE_REMOVED,
    HTOYTO_EVENT_TLK_RECEIVED,
    HTOYTO_EVENT_ACK_RECEIVED,
    HTOYTO_EVENT_ACK_TIMEOUT,
};

struct htoyto_event {
    enum htoyto_event_type type;
    const char *source_node;
    const char *target_node;
    const char *payload;
};

ZMK_EVENT_DECLARE(htoyto_event);
