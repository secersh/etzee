#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Display geometry: 7 panels stacked vertically, each 5x8 pixels.
 * Unified coordinate space: x in [0, 4], y in [0, 55].
 * Panel 0 occupies y=[0..7], panel 6 occupies y=[48..55]. */
#define DASH_PANELS      7
#define DASH_PANEL_COLS  5
#define DASH_PANEL_ROWS  8
#define DASH_COLS        DASH_PANEL_COLS
#define DASH_ROWS        (DASH_PANELS * DASH_PANEL_ROWS)

/* Bitmap for a single panel. rows[0] is the top row, rows[7] the bottom.
 * Within each row, bit 0 (LSB) is the leftmost pixel (x=0). */
typedef struct {
    uint8_t rows[DASH_PANEL_ROWS];
} dash_panel_bitmap_t;

/* Lifecycle */
int  dash_init(void);
void dash_sleep(void);
void dash_wake(void);

/* Pixel buffer — all writes are local until dash_flush / dash_flush_panel */
void dash_clear(void);
void dash_set_pixel(uint8_t x, uint8_t y, bool on);
bool dash_get_pixel(uint8_t x, uint8_t y);

/* Panel-level write — replaces an entire panel in the buffer at once.
 * Intended for the animation engine to push pre-built frames efficiently. */
void dash_set_panel(uint8_t panel_idx, const dash_panel_bitmap_t *bmp);

/* Global brightness, 0 (off) to 255 (full). Applied on next flush. */
void dash_set_brightness(uint8_t level);

/* Read ambient light from the half's sensor. Writes raw sensor value to *out.
 * Returns 0 on success, negative errno on failure. */
int dash_read_ambient(uint16_t *out);

/* Commit buffer to hardware over I2C.
 * dash_flush pushes all panels; dash_flush_panel pushes a single panel index. */
int dash_flush(void);
int dash_flush_panel(uint8_t panel_idx);
