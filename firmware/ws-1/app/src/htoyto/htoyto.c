#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>

#include <htoyto/htoyto.h>
#include <htoyto/events/event.h>

LOG_MODULE_REGISTER(htoyto, CONFIG_ZMK_LOG_LEVEL);

static const struct device *uart_dev;
static const struct device *dr_gpio_dev;
static struct gpio_callback dr_cb_data;
static bool node_connected = false;

static void htoyto_emit_event(enum htoyto_event_type type, const char *source, const char *target, const char *payload) {
    struct htoyto_event event = {
        .type = type,
        .source_node = source,
        .target_node = target,
        .payload = payload,
    };
    ZMK_EVENT_RAISE(new_htoyto_event(&event));
}

static void dr_line_callback(const struct device *dev, struct gpio_callback *cb, uint32_t pins) {
    if (!node_connected) {
        LOG_INF("dR line rising edge detected, starting handshake");
        uart_poll_out(uart_dev, 'H'); // TODO: replace with HLO frame
        // begin handshake timer
    } else {
        LOG_INF("dR line falling edge detected, node disconnected");
        node_connected = false;
        htoyto_emit_event(HTOYTO_EVENT_NODE_REMOVED, "self", NULL, NULL);
    }
}

int htoyto_init(const struct device *dev) {
    uart_dev = DEVICE_DT_GET(DT_PROP(dev, uart));
    if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART device not ready");
        return -ENODEV;
    }

#if DT_NODE_HAS_PROP(DT_DRV_INST(0), dr_gpios)
    dr_gpio_dev = DEVICE_DT_GET(DT_GPIO_CTLR(DT_DRV_INST(0), dr_gpios));
    gpio_pin_configure(dr_gpio_dev, DT_GPIO_PIN(DT_DRV_INST(0), dr_gpios),
                       GPIO_INPUT | DT_GPIO_FLAGS(DT_DRV_INST(0), dr_gpios));

    gpio_pin_interrupt_configure(dr_gpio_dev,
                                 DT_GPIO_PIN(DT_DRV_INST(0), dr_gpios),
                                 GPIO_INT_EDGE_BOTH);

    gpio_init_callback(&dr_cb_data, dr_line_callback,
                       BIT(DT_GPIO_PIN(DT_DRV_INST(0), dr_gpios)));

    gpio_add_callback(dr_gpio_dev, &dr_cb_data);
    LOG_INF("dR line interrupt configured");
#endif

    LOG_INF("htoyto initialized on %s", dev->name);
    return 0;
}

SYS_INIT(htoyto_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);

