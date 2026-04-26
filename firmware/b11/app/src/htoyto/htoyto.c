#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>

#include <htoyto/htoyto.h>
#include <htoyto/events/event.h>

LOG_MODULE_REGISTER(htoyto, CONFIG_ZMK_LOG_LEVEL);

#define HTY_NODE     DT_NODELABEL(htoyto0)
#define HTY_ROLE_IDX DT_ENUM_IDX(HTY_NODE, role)
#define HTY_BUF_SIZE (CONFIG_HTOYTO_MAX_NODE_ID_LENGTH * 3 + 16)

typedef enum {
    HTOYTO_STATE_IDLE,
    HTOYTO_STATE_HLO_SENT,      // origin: sent HLO, waiting for IAM
    HTOYTO_STATE_IAM_RECEIVED,  // origin: received IAM, sent EST, waiting for EST echo
    HTOYTO_STATE_EST_SENT,      // terminal: sent IAM, waiting for EST from origin
    HTOYTO_STATE_CONNECTED,
} htoyto_state_t;

static const struct device    *uart_dev;
static struct k_work_delayable handshake_timeout_work;
static struct k_work           rx_process_work;
static htoyto_state_t          state         = HTOYTO_STATE_IDLE;
static bool                    node_connected = false;

static uint8_t tx_buf[HTY_BUF_SIZE];
static int     tx_pos;
static int     tx_len;

// RX accumulation (ISR) → frame_buf (workqueue)
// TODO: replace frame_buf with a ring buffer to handle back-to-back frames
static char rx_buf[HTY_BUF_SIZE];
static int  rx_pos;
static char frame_buf[HTY_BUF_SIZE];

static void uart_send(const char *str) {
    int len = strlen(str);
    if (len >= HTY_BUF_SIZE) {
        LOG_WRN("TX frame too long, dropping");
        return;
    }
    memcpy(tx_buf, str, len);
    tx_pos = 0;
    tx_len = len;
    uart_irq_tx_enable(uart_dev);
}

static void process_frame(const char *line) {
    if (strncmp(line, "HLO ", 4) == 0) {
        if (state != HTOYTO_STATE_IDLE) {
            LOG_WRN("HLO unexpected in state %d", state);
            return;
        }
        LOG_INF("HLO from %s, sending IAM", line + 4);
        uart_send("IAM " DT_PROP(HTY_NODE, node_id) "\n");
        state = HTOYTO_STATE_EST_SENT;
        k_work_reschedule(&handshake_timeout_work,
                          K_MSEC(CONFIG_HTOYTO_HANDSHAKE_TIMEOUT_MS));

    } else if (strncmp(line, "IAM ", 4) == 0) {
        if (state != HTOYTO_STATE_HLO_SENT) {
            LOG_WRN("IAM unexpected in state %d", state);
            return;
        }
        LOG_INF("IAM from %s, sending EST", line + 4);
        uart_send("EST " DT_PROP(HTY_NODE, node_id) "\n");
        state = HTOYTO_STATE_IAM_RECEIVED;
        k_work_reschedule(&handshake_timeout_work,
                          K_MSEC(CONFIG_HTOYTO_HANDSHAKE_TIMEOUT_MS));

    } else if (strncmp(line, "EST ", 4) == 0) {
        if (state == HTOYTO_STATE_IAM_RECEIVED) {
            LOG_INF("EST from %s — connected (origin)", line + 4);
            k_work_cancel_delayable(&handshake_timeout_work);
            node_connected = true;
            state = HTOYTO_STATE_CONNECTED;
            htoyto_emit_node_added(DT_PROP(HTY_NODE, node_id));
        } else if (state == HTOYTO_STATE_EST_SENT) {
            LOG_INF("EST from %s — echoing EST, connected (terminal)", line + 4);
            uart_send("EST " DT_PROP(HTY_NODE, node_id) "\n");
            k_work_cancel_delayable(&handshake_timeout_work);
            node_connected = true;
            state = HTOYTO_STATE_CONNECTED;
            htoyto_emit_node_added(DT_PROP(HTY_NODE, node_id));
        } else {
            LOG_WRN("EST unexpected in state %d", state);
        }

    } else if (strncmp(line, "DKW ", 4) == 0) {
        LOG_WRN("DKW (rejected): %s", line + 4);
        k_work_cancel_delayable(&handshake_timeout_work);
        state = HTOYTO_STATE_IDLE;
        htoyto_emit_node_rejected(DT_PROP(HTY_NODE, node_id), line + 4);

    } else if (strncmp(line, "TLK ", 4) == 0) {
        if (state != HTOYTO_STATE_CONNECTED) {
            LOG_WRN("TLK while not connected");
            return;
        }
        char *src = (char *)(line + 4);
        char *tgt = strchr(src, ',');
        char *pay = tgt ? strchr(tgt + 1, ',') : NULL;
        if (!tgt || !pay) {
            LOG_WRN("malformed TLK: %s", line);
            return;
        }
        *tgt++ = '\0';
        *pay++ = '\0';
        htoyto_emit_tlk_received(src, tgt, pay);

    } else if (strncmp(line, "ACK ", 4) == 0) {
        if (state == HTOYTO_STATE_CONNECTED) {
            LOG_DBG("ACK: %s", line + 4);
            htoyto_emit_ack_received(DT_PROP(HTY_NODE, node_id));
        }

    } else {
        LOG_WRN("unknown frame: %s", line);
    }
}

static void rx_process_handler(struct k_work *work) {
    process_frame(frame_buf);
}

static void uart_irq_handler(const struct device *dev, void *user_data) {
    if (!uart_irq_update(dev)) return;

    if (uart_irq_tx_ready(dev)) {
        if (tx_pos < tx_len) {
            int sent = uart_fifo_fill(dev, tx_buf + tx_pos, tx_len - tx_pos);
            tx_pos += sent;
        }
        if (tx_pos >= tx_len) {
            uart_irq_tx_disable(dev);
        }
    }

    if (uart_irq_rx_ready(dev)) {
        uint8_t c;
        while (uart_fifo_read(dev, &c, 1) == 1) {
            if (c == '\n' || c == '\r') {
                if (rx_pos > 0) {
                    rx_buf[rx_pos] = '\0';
                    strncpy(frame_buf, rx_buf, HTY_BUF_SIZE - 1);
                    frame_buf[HTY_BUF_SIZE - 1] = '\0';
                    rx_pos = 0;
                    k_work_submit(&rx_process_work);
                }
            } else if (rx_pos < HTY_BUF_SIZE - 1) {
                rx_buf[rx_pos++] = c;
            } else {
                LOG_WRN("RX overflow, dropping frame");
                rx_pos = 0;
            }
        }
    }
}

static void handshake_timeout_handler(struct k_work *work) {
    LOG_WRN("handshake timed out in state %d", state);
    state = HTOYTO_STATE_IDLE;
    htoyto_emit_node_rejected(DT_PROP(HTY_NODE, node_id), "timeout");
}

#if HTY_ROLE_IDX == 0 || HTY_ROLE_IDX == 1 /* origin or bridge */

BUILD_ASSERT(DT_NODE_HAS_PROP(HTY_NODE, dr_gpios),
    "htoyto: origin and bridge nodes must define dr-gpios");

static const struct device    *dr_gpio_dev;
static struct gpio_callback    dr_cb_data;
static struct k_work_delayable dr_debounce_work;

static void dr_debounce_handler(struct k_work *work) {
    int val = gpio_pin_get(dr_gpio_dev, DT_GPIO_PIN(HTY_NODE, dr_gpios));

    if (val > 0 && !node_connected) {
        LOG_INF("dR rising — sending HLO");
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

#endif /* origin or bridge */

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
    char frame[HTY_BUF_SIZE];
    int n = snprintf(frame, sizeof(frame), "TLK %s,%s,%s\n",
                     DT_PROP(HTY_NODE, node_id),
                     target_node ? target_node : "*",
                     payload);
    if (n >= (int)sizeof(frame)) {
        return HTOYTO_STATUS_ERROR;
    }
    uart_send(frame);
    // TODO: arm ACK timeout, return TIMEOUT if no ACK received
    return HTOYTO_STATUS_OK;
}

// Init

int htoyto_init(void) {
    uart_dev = DEVICE_DT_GET(DT_PHANDLE(HTY_NODE, uart));
    if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART device not ready");
        return -ENODEV;
    }

    k_work_init(&rx_process_work, rx_process_handler);
    k_work_init_delayable(&handshake_timeout_work, handshake_timeout_handler);

    uart_irq_callback_set(uart_dev, uart_irq_handler);
    uart_irq_rx_enable(uart_dev);

#if HTY_ROLE_IDX == 0 || HTY_ROLE_IDX == 1 /* origin or bridge */
    k_work_init_delayable(&dr_debounce_work, dr_debounce_handler);
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
#endif /* origin or bridge */

    LOG_INF("htoyto initialized, role=%s node-id=%s",
            DT_PROP(HTY_NODE, role), DT_PROP(HTY_NODE, node_id));
    return 0;
}

SYS_INIT(htoyto_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
