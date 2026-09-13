#pragma once
#include <stdint.h>

/* Little-endian x86-64 shared-memory ABI. The native Pulse reader is the sole
 * writer; the sequence selects the last completely published slot. */
#include <string.h>
#define APO_VOLUME_MAGIC 0x41564f31u
struct apo_volume_state {
    uint32_t sequence, magic;
    uint64_t timestamp_100ns;
    uint32_t valid, channels, muted;
    float master_db, channel_db[2];
    char target[256];
};

struct apo_volume_shared {
    uint32_t sequence, reserved;
    struct apo_volume_state slots[2];
};

/* Write only the inactive slot. A preempted publisher leaves the previous
 * complete snapshot available, instead of exposing a writer-held sequence. */
static inline void apo_volume_publish(struct apo_volume_shared *shared,
                                      const struct apo_volume_state *state) {
    uint32_t sequence = __atomic_load_n(&shared->sequence, __ATOMIC_RELAXED);
    memcpy(&shared->slots[(sequence + 1u) & 1u], state, sizeof(*state));
    __atomic_store_n(&shared->sequence, sequence + 1u, __ATOMIC_RELEASE);
}

static inline int apo_volume_snapshot(const struct apo_volume_shared *shared,
                                     struct apo_volume_state *state) {
    for (unsigned attempt = 0; attempt < 8; ++attempt) {
        uint32_t before = __atomic_load_n(&shared->sequence, __ATOMIC_ACQUIRE);
        memcpy(state, &shared->slots[before & 1u], sizeof(*state));
        __atomic_thread_fence(__ATOMIC_SEQ_CST);
        if (before == __atomic_load_n(&shared->sequence, __ATOMIC_ACQUIRE))
            return 1;
    }
    return 0;
}
