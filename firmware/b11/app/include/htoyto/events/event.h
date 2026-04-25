#pragma once

#include <zmk/event_manager.h>

enum htoyto_event_type {
    HTOYTO_EVENT_NODE_ADDED,               // Node added to the network
    HTOYTO_EVENT_NODE_ADDED_FAILED,        // Node addition failed
    HTOYTO_EVENT_NODE_REMOVED,             // Node removed from the network
    HTOYTO_EVENT_TLK_RECEIVED,             // TLK received from the network
    HTOYTO_EVENT_ACK_RECEIVED,             // Acknowledgment received from the network
    HTOYTO_EVENT_ACK_TIMEOUT,              // Acknowledgment timeout
};

struct htoyto_event {
    zmk_event_t header;
    enum htoyto_event_type type;
    const char *source_node;
    const char *target_node;
    const char *payload; // optional command data or reason string
};

ZMK_EVENT_DECLARE(htoyto_event);
