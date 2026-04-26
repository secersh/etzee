#!/usr/bin/env bash
# Interactive deployment script for etzee b11 firmware (macOS, Nice!Nano v2)
set -euo pipefail

REPO="secersh/etzee"
WORKFLOW_NAME="firmware.yaml"
ARTIFACT_LEFT="etzee_b11_left"
ARTIFACT_RIGHT="etzee_b11_right"
BOOTLOADER_VOLUME="NICENANO"
BAUD=115200
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIRMWARE_DIR="$SCRIPT_DIR/.firmware-cache"

# ── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}${BOLD}→${RESET} $*"; }
success() { echo -e "${GREEN}${BOLD}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}${BOLD}!${RESET} $*"; }
error()   { echo -e "${RED}${BOLD}✗${RESET} $*" >&2; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }
hr()      { echo -e "${CYAN}────────────────────────────────────────────────${RESET}"; }

# ── helpers ───────────────────────────────────────────────────────────────────
require() {
    if ! command -v "$1" &>/dev/null; then
        error "Required tool not found: $1"
        [[ -n "${2:-}" ]] && echo "  Install with: $2"
        exit 1
    fi
}

prompt_enter() {
    echo -ne "\n${BOLD}Press Enter to continue…${RESET} "
    read -r
}

# Wait for /Volumes/NICENANO to appear.
# Pass "fresh" as second arg to first wait for it to unmount (used between flashes).
wait_for_bootloader() {
    local label="$1"
    local mode="${2:-}"   # "fresh" = wait for unmount first
    local mount="/Volumes/$BOOTLOADER_VOLUME"
    local timeout=60
    local elapsed=0

    if [[ "$mode" == "fresh" && -d "$mount" ]]; then
        info "Waiting for $BOOTLOADER_VOLUME to unmount…"
        local unmount_timeout=15
        while [[ -d "$mount" ]] && (( elapsed < unmount_timeout )); do
            sleep 1; (( elapsed++ ))
        done
        elapsed=0
    fi

    if [[ -d "$mount" ]]; then
        success "Detected $BOOTLOADER_VOLUME at $mount"
        return
    fi

    info "Waiting for $BOOTLOADER_VOLUME to appear (${label} half)…"
    while [[ ! -d "$mount" ]] && (( elapsed < timeout )); do
        sleep 1; (( elapsed++ ))
    done

    if [[ ! -d "$mount" ]]; then
        error "Timed out waiting for $BOOTLOADER_VOLUME (${timeout}s)."
        error "Make sure the Nice!Nano v2 is in bootloader mode and try again."
        exit 1
    fi

    success "Detected $BOOTLOADER_VOLUME at $mount"
}

flash_half() {
    local label="$1"    # "left" or "right"
    local uf2="$2"      # path to .uf2 file
    local fresh="${3:-}"  # "fresh" = wait for previous mount to clear first
    local mount="/Volumes/$BOOTLOADER_VOLUME"

    header "Flashing ${BOLD}${label}${RESET} half"
    hr
    echo -e "  1. Plug the ${BOLD}${label}${RESET} half into USB."
    echo -e "  2. ${BOLD}Double-press${RESET} the reset button on the Nice!Nano v2."
    echo -e "     The board should appear as ${CYAN}NICENANO${RESET} in Finder."
    hr
    prompt_enter

    wait_for_bootloader "$label" "$fresh"

    info "Copying $(basename "$uf2") → $mount …"
    # The bootloader reboots mid-copy and unmounts the drive — cp will error even on success.
    cp -X "$uf2" "$mount/" 2>&1 || true
    sleep 3   # give macOS time to reflect the reboot/unmount

    success "${label^} half flashed."
}

# ── firmware fetch ────────────────────────────────────────────────────────────
fetch_firmware() {
    header "Fetching firmware artifacts"
    mkdir -p "$FIRMWARE_DIR"

    # Try a tagged firmware release first (future-proof)
    local release_tag
    release_tag=$(gh release list -R "$REPO" --limit 20 --json tagName,name \
        | grep -i '"firmware' | head -1 | grep -o '"tagName":"[^"]*"' \
        | cut -d'"' -f4 || true)

    if [[ -n "$release_tag" ]]; then
        info "Downloading firmware from release: $release_tag"
        gh release download "$release_tag" -R "$REPO" \
            --pattern "*.uf2" --dir "$FIRMWARE_DIR" --clobber
    else
        # Fall back to latest successful firmware workflow run
        info "No firmware release found — fetching latest CI artifacts…"
        local run_id
        run_id=$(gh run list -R "$REPO" --workflow "$WORKFLOW_NAME" \
            --status success --limit 1 --json databaseId \
            | grep -o '[0-9]\{8,\}' | head -1)

        if [[ -z "$run_id" ]]; then
            error "No successful firmware workflow run found on $REPO."
            error "Push a commit under firmware/ to trigger a build, then retry."
            exit 1
        fi

        info "Run ID: $run_id"
        rm -rf "$FIRMWARE_DIR/$ARTIFACT_LEFT" "$FIRMWARE_DIR/$ARTIFACT_RIGHT"
        gh run download "$run_id" -R "$REPO" \
            -n "$ARTIFACT_LEFT"  --dir "$FIRMWARE_DIR/$ARTIFACT_LEFT"
        gh run download "$run_id" -R "$REPO" \
            -n "$ARTIFACT_RIGHT" --dir "$FIRMWARE_DIR/$ARTIFACT_RIGHT"
    fi

    # Resolve .uf2 paths
    UF2_LEFT=$(find "$FIRMWARE_DIR" -name "*.uf2" | grep -i left  | head -1)
    UF2_RIGHT=$(find "$FIRMWARE_DIR" -name "*.uf2" | grep -i right | head -1)

    # Fallback: if artifact dirs have no left/right in the name, grab by dir
    [[ -z "$UF2_LEFT"  ]] && UF2_LEFT=$(find  "$FIRMWARE_DIR/$ARTIFACT_LEFT"  -name "*.uf2" 2>/dev/null | head -1 || true)
    [[ -z "$UF2_RIGHT" ]] && UF2_RIGHT=$(find "$FIRMWARE_DIR/$ARTIFACT_RIGHT" -name "*.uf2" 2>/dev/null | head -1 || true)

    if [[ -z "$UF2_LEFT" || -z "$UF2_RIGHT" ]]; then
        error "Could not locate left/right .uf2 files in $FIRMWARE_DIR"
        error "Contents:"
        find "$FIRMWARE_DIR" -name "*.uf2" >&2 || true
        exit 1
    fi

    success "Left:  $UF2_LEFT"
    success "Right: $UF2_RIGHT"
}

# ── serial terminal ───────────────────────────────────────────────────────────
open_serial() {
    header "Serial terminal"
    hr
    echo "  Plug in either half (or both) and look for a tty device."
    hr

    # Wait up to 20 s for a usbmodem/usbserial tty to appear
    local ttys elapsed=0 timeout=20
    ttys=$(ls /dev/tty.usbmodem* /dev/tty.usbserial* 2>/dev/null || true)
    while [[ -z "$ttys" ]] && (( elapsed < timeout )); do
        sleep 1; (( elapsed++ ))
        ttys=$(ls /dev/tty.usbmodem* /dev/tty.usbserial* 2>/dev/null || true)
    done

    if [[ -z "$ttys" ]]; then
        warn "No USB serial device found after ${timeout}s — skipping serial terminal."
        return
    fi

    local tty_count device
    tty_count=$(echo "$ttys" | wc -l | tr -d ' ')

    if (( tty_count == 1 )); then
        device="$ttys"
        info "Found: $device"
    else
        echo -e "\n  Multiple devices found:"
        local i=1
        while IFS= read -r t; do
            echo "    [$i] $t"; (( i++ ))
        done <<< "$ttys"
        echo -ne "\n  ${BOLD}Choose [1-${tty_count}]:${RESET} "; read -r choice
        device=$(echo "$ttys" | sed -n "${choice}p")
    fi

    echo ""
    info "Opening screen session on $device at ${BAUD} baud."
    echo -e "  ${YELLOW}To exit: Ctrl-A then Ctrl-\\${RESET}"
    echo -e "  ZMK shell commands: ${CYAN}kernel version${RESET}, ${CYAN}zmk info${RESET}"
    hr
    prompt_enter

    screen "$device" "$BAUD"
}

# ── main ──────────────────────────────────────────────────────────────────────
main() {
    clear
    echo -e "${BOLD}"
    echo "  ███████╗████████╗███████╗███████╗███████╗"
    echo "  ██╔════╝╚══██╔══╝╚══███╔╝██╔════╝██╔════╝"
    echo "  █████╗     ██║     ███╔╝ █████╗  █████╗  "
    echo "  ██╔══╝     ██║    ███╔╝  ██╔══╝  ██╔══╝  "
    echo "  ███████╗   ██║   ███████╗███████╗███████╗"
    echo "  ╚══════╝   ╚═╝   ╚══════╝╚══════╝╚══════╝"
    echo -e "${RESET}"
    echo -e "  ${CYAN}b11 firmware deployment${RESET} · macOS · Nice!Nano v2"
    hr

    require gh  "brew install gh  (then: gh auth login)"
    require screen "already included in macOS"

    # Parse flags
    local do_left=true do_right=true do_serial=true skip_fetch=false

    for arg in "$@"; do
        case "$arg" in
            --left)        do_right=false ;;
            --right)       do_left=false ;;
            --no-serial)   do_serial=false ;;
            --skip-fetch)  skip_fetch=true ;;
            --help|-h)
                echo "Usage: $(basename "$0") [--left|--right] [--no-serial] [--skip-fetch]"
                echo ""
                echo "  --left        Flash only the left half"
                echo "  --right       Flash only the right half"
                echo "  --no-serial   Skip the serial terminal step"
                echo "  --skip-fetch  Reuse previously downloaded firmware"
                exit 0
                ;;
            *) error "Unknown option: $arg"; exit 1 ;;
        esac
    done

    if $skip_fetch && [[ -d "$FIRMWARE_DIR" ]]; then
        info "Skipping fetch — using cached firmware in $FIRMWARE_DIR"
        UF2_LEFT=$(find  "$FIRMWARE_DIR" -name "*.uf2" | grep -i left  | head -1 || true)
        UF2_RIGHT=$(find "$FIRMWARE_DIR" -name "*.uf2" | grep -i right | head -1 || true)
        [[ -z "$UF2_LEFT"  ]] && UF2_LEFT=$(find  "$FIRMWARE_DIR/$ARTIFACT_LEFT"  -name "*.uf2" 2>/dev/null | head -1 || true)
        [[ -z "$UF2_RIGHT" ]] && UF2_RIGHT=$(find "$FIRMWARE_DIR/$ARTIFACT_RIGHT" -name "*.uf2" 2>/dev/null | head -1 || true)
        if [[ -z "$UF2_LEFT" || -z "$UF2_RIGHT" ]]; then
            warn "Cache incomplete — fetching fresh."
            fetch_firmware
        fi
    else
        fetch_firmware
    fi

    $do_left  && flash_half "left"  "$UF2_LEFT"
    # "fresh" tells the right flash to wait for the left's NICENANO to unmount first
    if $do_right; then
        if $do_left; then
            flash_half "right" "$UF2_RIGHT" "fresh"
        else
            flash_half "right" "$UF2_RIGHT"
        fi
    fi

    echo ""
    success "Both halves flashed."

    if $do_serial; then
        open_serial
    fi

    echo ""
    success "Done. Happy typing."
    echo ""
}

main "$@"
