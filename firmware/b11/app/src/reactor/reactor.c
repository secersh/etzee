#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>

#include <zmk/event_manager.h>
#include <htoyto/events/event.h>

LOG_MODULE_REGISTER(reactor, CONFIG_ZMK_LOG_LEVEL);

static int handle_htoyto_event(const zmk_event_t *eh) {
    const struct htoyto_event *ev = as_htoyto_event(eh);

    switch (ev->type) {
    case HTOYTO_EVENT_NODE_ADDED:
        LOG_INF("node added: %s", ev->source_node);
        break;

    case HTOYTO_EVENT_NODE_REMOVED:
        LOG_INF("node removed: %s", ev->source_node);
        break;

    case HTOYTO_EVENT_NODE_ADD_FAILED:
        LOG_WRN("node add failed: %s (%s)", ev->source_node, ev->payload);
        break;

    case HTOYTO_EVENT_TLK_RECEIVED:
        LOG_INF("TLK %s -> %s: %s",
                ev->source_node,
                ev->target_node ? ev->target_node : "ALL",
                ev->payload);
        break;

    case HTOYTO_EVENT_ACK_RECEIVED:
        LOG_DBG("ACK from %s", ev->source_node);
        break;

    case HTOYTO_EVENT_ACK_TIMEOUT:
        LOG_WRN("ACK timeout from %s", ev->target_node);
        break;

    default:
        LOG_WRN("unknown event type: %d", ev->type);
        break;
    }

    return 0;
}

ZMK_LISTENER(reactor, handle_htoyto_event);
ZMK_SUBSCRIPTION(reactor, htoyto_event);
