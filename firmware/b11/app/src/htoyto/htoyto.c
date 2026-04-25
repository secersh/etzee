#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>
#include "../../include/htoyto/htoyto.h"

#define RX_BUF_SIZE 64
#define HTY_NODE DT_NODELABEL(htoyto0)

LOG_MODULE_REGISTER(htoyto, CONFIG_ZMK_LOG_LEVEL);

static const char *hty_node_id;
static htoyto_role_t hty_role;

void log_thread(void) {
    while (1) {
        LOG_INF("htoyto heartbeat node-id: %s role: %d", hty_node_id, hty_role);
        k_sleep(K_SECONDS(1));
    }
}

K_THREAD_DEFINE(htoyto_log_thread, 1024, log_thread, NULL, NULL, NULL, 7, 0, 0);

static uint8_t rx_buf[RX_BUF_SIZE];

static const struct device *hty_uart_dev;
static const struct device *hty_dr_gpio_dev;
static gpio_pin_t hty_dr_pin;

static struct gpio_callback dr_gpio_cb;

static void htoyto_process_message(const char *msg);

static void hty_uart_cb(const struct device *dev, struct uart_event *evt, void *user_data) {
    switch (evt->type) {
    case UART_RX_RDY:
        rx_buf[evt->data.rx.len] = '\0'; // Ensure null-terminated
        htoyto_process_message((const char *)(evt->data.rx.buf + evt->data.rx.offset));
        break;

    case UART_RX_DISABLED:
        LOG_WRN("UART RX disabled; re-enabling");
        uart_rx_enable(dev, rx_buf, sizeof(rx_buf), 100);
        break;

    case UART_RX_BUF_REQUEST:
        uart_rx_buf_rsp(dev, rx_buf, sizeof(rx_buf));
        break;

    default:
        break;
    }
}

static void htoyto_process_message(const char *msg) {
    LOG_INF("Received: %s", msg);

    if (strcmp(msg, "hlo") == 0 && hty_role == HTOYTO_ROLE_TERMINAL) {
        uart_tx(hty_uart_dev, (const uint8_t *)"iam", 3, SYS_FOREVER_MS);
    } else if (strcmp(msg, "iam") == 0 && hty_role == HTOYTO_ROLE_ORIGIN) {
        uart_tx(hty_uart_dev, (const uint8_t *)"est", 3, SYS_FOREVER_MS);
    } else if (strcmp(msg, "est") == 0 && hty_role == HTOYTO_ROLE_TERMINAL) {
        uart_tx(hty_uart_dev, (const uint8_t *)"est", 3, SYS_FOREVER_MS);
    } else {
        LOG_WRN("Unexpected or unhandled message: %s", msg);
    }
}

static void dr_interrupt_cb(const struct device *dev, struct gpio_callback *cb, uint32_t pins) {
    int val = gpio_pin_get(dev, hty_dr_pin);

    LOG_INF("dR line changed: %s edge", val ? "rising" : "falling");

    if (val) {
        uart_tx(hty_uart_dev, (const uint8_t *)"hlo", 3, SYS_FOREVER_MS);
    }
}

int htoyto_init(const struct device *dev) {
    ARG_UNUSED(dev);

    hty_node_id = DT_PROP(HTY_NODE, node_id);
    hty_role = (htoyto_role_t)DT_ENUM_IDX(HTY_NODE, role);

    hty_uart_dev = DEVICE_DT_GET(DT_PHANDLE(HTY_NODE, uart));

    if (!device_is_ready(hty_uart_dev)) {
        LOG_ERR("UART device not ready");
        return -ENODEV;
    }

    if (hty_role == HTOYTO_ROLE_ORIGIN) {
        hty_dr_gpio_dev = DEVICE_DT_GET(DT_GPIO_CTLR(HTY_NODE, dr_gpios));
        hty_dr_pin = DT_GPIO_PIN(HTY_NODE, dr_gpios);
        // hty_dr_flags = DT_GPIO_FLAGS(HTY_NODE, dr_gpios);
        //
        //        if (!device_is_ready(hty_dr_gpio_dev)) {
        //            LOG_ERR("dR GPIO device not ready");
        //            return -ENODEV;
        //        }
        //
        int ret = gpio_pin_configure(hty_dr_gpio_dev, hty_dr_pin,
                                     GPIO_INPUT | GPIO_PULL_DOWN | GPIO_INT_EDGE_BOTH);
        //
        //        if (ret != 0) {
        //            LOG_ERR("Failed to configure dR pin: %d", ret);
        //            return ret;
        //        }
        //

        gpio_init_callback(&dr_gpio_cb, dr_interrupt_cb, BIT(hty_dr_pin));
        gpio_add_callback(hty_dr_gpio_dev, &dr_gpio_cb);
        gpio_pin_interrupt_configure(hty_dr_gpio_dev, hty_dr_pin, GPIO_INT_EDGE_BOTH);
    }

    return 0;
}

/* Bind the htoyto device node from DTS */
DEVICE_DT_DEFINE(HTY_NODE,                           /* node label from overlay */
                 htoyto_init,                        /* init function */
                 NULL,                               /* PM device control (not used) */
                 NULL,                               /* data (instance-specific state struct) */
                 NULL,                               /* config (constant config struct) */
                 POST_KERNEL,                        /* init level */
                 CONFIG_KERNEL_INIT_PRIORITY_DEVICE, /* init priority */
                 NULL);                              /* API (not exposing driver API yet) */
