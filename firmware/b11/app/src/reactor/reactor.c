#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>

#include <zmk/event_manager.h>
#include <htoyto/events/event.h>

LOG_MODULE_REGISTER(reactor, CONFIG_ZMK_LOG_LEVEL);

static int handle_htoyto_event(const struct htoyto_event *ev) {
    switch (ev->type) {
    case HTOYTO_EVENT_NODE_ADDED:
        LOG_INF("🟢 Node added: %s", ev->source_node);
        // TODO: react to node connection, e.g., trigger storyboard
        break;

    case HTOYTO_EVENT_NODE_REMOVED:
        LOG_INF("🔴 Node removed: %s", ev->source_node);
        // TODO: stop animation or play disconnect effect
        break;

    case HTOYTO_EVENT_NODE_ADDED_FAILED:
        LOG_WRN("⚠️ Node add failed: %s (%s)", ev->source_node, ev->payload);
        // TODO: indicate error on display or buzzer
        break;

    case HTOYTO_EVENT_TLK_RECEIVED:
        LOG_INF("💬 TLK %s ➝ %s: %s",
                ev->source_node,
                ev->target_node ? ev->target_node : "ALL",
                ev->payload);
        // TODO: dispatch command or text to display, audio, etc.
        break;

    case HTOYTO_EVENT_ACK_RECEIVED:
        LOG_DBG("✅ ACK received from %s", ev->source_node);
        break;

    case HTOYTO_EVENT_ACK_TIMEOUT:
        LOG_WRN("⏱️ ACK timeout from %s", ev->target_node);
        break;

    default:
        LOG_WRN("❓ Unknown htoyto event type: %d", ev->type);
        break;
    }

    return 0;
}

ZMK_LISTENER(reactor, handle_htoyto_event);
ZMK_SUBSCRIPTION(reactor, htoyto_event);
