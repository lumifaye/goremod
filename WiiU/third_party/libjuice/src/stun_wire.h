/* Network byte order helpers for STUN values.
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy was not distributed with this file, You can
 * obtain one at https://mozilla.org/MPL/2.0/. */
#ifndef JUICE_STUN_WIRE_H
#define JUICE_STUN_WIRE_H
#include <stdint.h>
static inline void stun_store_u64(uint8_t out[8], uint64_t value) {
    for (int i = 0; i < 8; ++i) out[i] = (uint8_t)(value >> (56 - 8 * i));
}
#endif
