#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Display geometry: 7 panels stacked vertically, each 5x8 pixels.
 * Unified coordinate space: x in [0, 4], y in [0, 55].
 * Panel 0 occupies y=[0..7], panel 6 occupies y=[48..55]. */
#define DOTM_PANELS      7
#define DOTM_PANEL_COLS  5
#define DOTM_PANEL_ROWS  8
#define DOTM_COLS        DOTM_PANEL_COLS
#define DOTM_ROWS        (DOTM_PANELS * DOTM_PANEL_ROWS)

/* Bitmap for a single panel. rows[0] is the top row, rows[7] the bottom.
 * Within each row, bit 0 (LSB) is the leftmost pixel (x=0). */
typedef struct {
    uint8_t rows[DOTM_PANEL_ROWS];
} dotm_panel_bitmap_t;

/* Lifecycle */
int  dotm_init(void);
void dotm_sleep(void);
void dotm_wake(void);

/* Pixel buffer — all writes are local until dotm_flush / dotm_flush_panel */
void dotm_clear(void);
void dotm_set_pixel(uint8_t x, uint8_t y, bool on);
bool dotm_get_pixel(uint8_t x, uint8_t y);

/* Panel-level write — replaces an entire panel in the buffer at once.
 * Intended for the animation engine to push pre-built frames efficiently. */
void dotm_set_panel(uint8_t panel_idx, const dotm_panel_bitmap_t *bmp);

/* Global brightness, 0 (off) to 255 (full). Applied on next flush. */
void dotm_set_brightness(uint8_t level);

/* Read ambient light from the half's sensor. Writes raw sensor value to *out.
 * Returns 0 on success, negative errno on failure. */
int dotm_read_ambient(uint16_t *out);

/* Commit buffer to hardware over I2C.
 * dotm_flush pushes all panels; dotm_flush_panel pushes a single panel index. */
int dotm_flush(void);
int dotm_flush_panel(uint8_t panel_idx);
