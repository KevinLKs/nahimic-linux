#pragma once
#include <stdint.h>

/* Little-endian x86-64 shared-memory ABI. The native Pulse reader is the sole
 * writer. An even, unchanged sequence identifies a complete snapshot. */
#define APO_VOLUME_MAGIC 0x41564f31u
struct apo_volume_state {
    uint32_t sequence, magic;
    uint64_t timestamp_100ns;
    uint32_t valid, channels, muted;
    float master_db, channel_db[2];
    char target[256];
};
