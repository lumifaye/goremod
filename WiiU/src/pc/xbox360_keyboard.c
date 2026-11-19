#ifdef TARGET_XBOX360
#include "console_keyboard.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <SDL2/SDL_stdinc.h>
#include <xsdk/xam.h>

/* Even if focus disappears, XAM owns both strings until the overlapped
 * completes. Never let a late reply write into the next field. */
static XAM_OVERLAPPED dialog;
static uint16_t *initial_text, *reply;
static size_t chars;
static uint32_t status;
static bool abandoned;
static const uint16_t title[] = { 'R','e','a','l','i','s','m','6','4',0 };
static const uint16_t empty[] = { 0 };

static void release_dialog(void) {
    if (reply) memset(reply, 0, chars * sizeof(*reply));
    free(reply);
    SDL_free(initial_text);
    reply = initial_text = NULL;
}

static bool completed(void) {
    if (status != ERROR_IO_PENDING) return true;
    uint32_t rc = xsdk_xam_wait(&dialog, 0, NULL);
    if (rc == ERROR_IO_INCOMPLETE) return false;
    status = rc;
    return true;
}

bool console_keyboard_active(void) { return reply != NULL; }

void console_keyboard_cancel(void) {
    abandoned = true;
    if (reply && completed()) release_dialog();
}

bool console_keyboard_open(const char *initial, size_t capacity, bool password) {
    if (reply && abandoned && completed()) release_dialog();
    if (reply || capacity < 2 || capacity > UINT16_MAX) return false;
    chars = capacity;
    initial_text = (uint16_t *)SDL_iconv_string("UTF-16BE", "UTF-8", initial, strlen(initial)+1);
    reply = calloc(chars, sizeof(*reply));
    if (!initial_text || !reply) { release_dialog(); return false; }
    uint32_t user;
    char tag[XSDK_XAM_GAMERTAG_BYTES];
    if (xsdk_xam_signed_in_user(&user, tag) != ERROR_SUCCESS) user = 0;
    abandoned = false;
    (void)xsdk_system_ui_open();
    xsdk_xam_prepare(&dialog);
    /* XAM keyboard option 1 is password entry. */
    status = xsdk_xam_returned(&dialog, XamShowKeyboardUI(user, password ? 1 : 0,
        initial_text, title, empty, reply, chars, &dialog));
    return true;
}

int console_keyboard_take_result(char *out, size_t capacity) {
    if (!reply || !completed()) return 0;
    int result = -1;
    if (!abandoned && status == ERROR_SUCCESS && !dialog.extended_error && capacity) {
        size_t n = 0;
        while (n+1 < chars && reply[n]) ++n;
        reply[n] = 0;
        char *utf8 = SDL_iconv_string("UTF-8", "UTF-16BE", (char *)reply, (n+1)*2);
        if (utf8) {
            size_t bytes = strlen(utf8);
            if (bytes >= capacity) {
                bytes = capacity-1;
                while (bytes && ((unsigned char)utf8[bytes] & 0xc0) == 0x80) --bytes;
            }
            memcpy(out, utf8, bytes); out[bytes] = 0;
            SDL_free(utf8); result = 1;
        }
    }
    release_dialog();
    return result;
}
#endif
