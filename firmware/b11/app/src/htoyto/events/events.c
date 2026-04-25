#include <htoyto/events/event.h>
#include <zmk/event_manager.h>

ZMK_EVENT_IMPL(htoyto_event);

static void emit(enum htoyto_event_type type, const char *source,
                 const char *target, const char *payload) {
    raise_htoyto_event((struct htoyto_event){
        .type = type,
        .source_node = source,
        .target_node = target,
        .payload = payload,
    });
}

void htoyto_emit_node_added(const char *source) {
    emit(HTOYTO_EVENT_NODE_ADDED, source, NULL, NULL);
}

void htoyto_emit_node_rejected(const char *source, const char *reason) {
    emit(HTOYTO_EVENT_NODE_REJECTED, source, NULL, reason);
}

void htoyto_emit_node_removed(const char *source) {
    emit(HTOYTO_EVENT_NODE_REMOVED, source, NULL, NULL);
}

void htoyto_emit_tlk_received(const char *source, const char *target, const char *payload) {
    emit(HTOYTO_EVENT_TLK_RECEIVED, source, target, payload);
}

void htoyto_emit_ack_received(const char *source) {
    emit(HTOYTO_EVENT_ACK_RECEIVED, source, NULL, NULL);
}

void htoyto_emit_ack_timed_out(const char *target) {
    emit(HTOYTO_EVENT_ACK_TIMED_OUT, NULL, target, NULL);
}
