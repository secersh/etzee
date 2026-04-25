#include <stdbool.h>
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>

#include <htoyto/htoyto.h>
#include <htoyto/events/event.h>

LOG_MODULE_REGISTER(htoyto, CONFIG_ZMK_LOG_LEVEL);

#define HTY_NODE DT_NODELABEL(htoyto0)

typedef enum {
    HTOYTO_STATE_IDLE,
    HTOYTO_STATE_HLO_SENT,      // origin: waiting for IAM
    HTOYTO_STATE_IAM_RECEIVED,  // origin: received IAM, sent EST, waiting for EST echo
    HTOYTO_STATE_EST_SENT,      // terminal: sent IAM, waiting for EST from origin
    HTOYTO_STATE_CONNECTED,
} htoyto_state_t;

static const struct device *uart_dev;
static const struct device *dr_gpio_dev;
static struct gpio_callback   dr_cb_data;
static struct k_work_delayable dr_debounce_work;
static struct k_work_delayable handshake_timeout_work;
static htoyto_state_t state    = HTOYTO_STATE_IDLE;
static bool node_connected     = false;

static void uart_send(const char *str) {
    while (*str) {
        uart_poll_out(uart_dev, *str++);
    }
}

static void handshake_timeout_handler(struct k_work *work) {
    LOG_WRN("handshake timed out in state %d", state);
    state = HTOYTO_STATE_IDLE;
    htoyto_emit_node_rejected(DT_PROP(HTY_NODE, node_id), "timeout");
}

static void dr_debounce_handler(struct k_work *work) {
    int val = gpio_pin_get(dr_gpio_dev, DT_GPIO_PIN(HTY_NODE, dr_gpios));

    if (val > 0 && !node_connected) {
        LOG_INF("dR rising — sending HLO");
        // TODO: build framed HLO packet
        uart_send("HLO " DT_PROP(HTY_NODE, node_id) "\n");
        state = HTOYTO_STATE_HLO_SENT;
        k_work_reschedule(&handshake_timeout_work,
                          K_MSEC(CONFIG_HTOYTO_HANDSHAKE_TIMEOUT_MS));
    } else if (val == 0 && node_connected) {
        LOG_INF("dR falling — node disconnected");
        node_connected = false;
        state = HTOYTO_STATE_IDLE;
        k_work_cancel_delayable(&handshake_timeout_work);
        htoyto_emit_node_removed(DT_PROP(HTY_NODE, node_id));
    }
}

static void dr_line_callback(const struct device *dev, struct gpio_callback *cb,
                              uint32_t pins) {
    k_work_reschedule(&dr_debounce_work, K_MSEC(CONFIG_HTOYTO_DEBOUNCE_MS));
}

static void uart_rx_handler(const struct device *dev, void *user_data) {
    // TODO: read incoming bytes into a line buffer, parse frame type (IAM/EST/DKW/TLK/ACK)
    // and advance the state machine or dispatch to htoyto_emit_* accordingly
}

// Public API

htoyto_role_t htoyto_get_role(void) {
    if (strcmp(DT_PROP(HTY_NODE, role), "origin") == 0) return HTOYTO_ROLE_ORIGIN;
    if (strcmp(DT_PROP(HTY_NODE, role), "bridge") == 0)  return HTOYTO_ROLE_BRIDGE;
    return HTOYTO_ROLE_TERMINAL;
}

bool htoyto_is_connected(void) {
    return node_connected;
}

htoyto_status_t htoyto_send_tlk(const char *target_node, const char *payload) {
    if (!node_connected) {
        return HTOYTO_STATUS_ERROR;
    }
    // TODO: frame TLK packet, write to UART, arm ACK timeout, return result
    return HTOYTO_STATUS_ERROR;
}

// Init

int htoyto_init(void) {
    uart_dev = DEVICE_DT_GET(DT_PHANDLE(HTY_NODE, uart));
    if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART device not ready");
        return -ENODEV;
    }

    k_work_init_delayable(&dr_debounce_work, dr_debounce_handler);
    k_work_init_delayable(&handshake_timeout_work, handshake_timeout_handler);

    // TODO: register uart_rx_handler via uart_irq_callback_set + uart_irq_rx_enable

#if DT_NODE_HAS_PROP(HTY_NODE, dr_gpios)
    dr_gpio_dev = DEVICE_DT_GET(DT_GPIO_CTLR(HTY_NODE, dr_gpios));
    gpio_pin_configure(dr_gpio_dev, DT_GPIO_PIN(HTY_NODE, dr_gpios),
                       GPIO_INPUT | DT_GPIO_FLAGS(HTY_NODE, dr_gpios));
    gpio_pin_interrupt_configure(dr_gpio_dev,
                                 DT_GPIO_PIN(HTY_NODE, dr_gpios),
                                 GPIO_INT_EDGE_BOTH);
    gpio_init_callback(&dr_cb_data, dr_line_callback,
                       BIT(DT_GPIO_PIN(HTY_NODE, dr_gpios)));
    gpio_add_callback(dr_gpio_dev, &dr_cb_data);
    LOG_INF("dR line interrupt configured");
#endif

    LOG_INF("htoyto initialized, role=%s node-id=%s",
            DT_PROP(HTY_NODE, role), DT_PROP(HTY_NODE, node_id));
    return 0;
}

SYS_INIT(htoyto_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
