#define _GNU_SOURCE
#include <assert.h>
#include <sched.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#include "../host/volume_state.h"

static struct apo_volume_state sample(uint32_t value) {
    struct apo_volume_state state = {0};
    state.magic = APO_VOLUME_MAGIC;
    state.timestamp_100ns = value;
    state.valid = 1; state.channels = 2; state.muted = value & 1;
    state.master_db = -(float)(value % 30);
    state.channel_db[0] = state.master_db - 1;
    state.channel_db[1] = state.master_db - 2;
    memset(state.target, 'A' + value % 26, 255);
    return state;
}

int main(void) {
    struct apo_volume_shared *shared = mmap(NULL, sizeof(*shared), PROT_READ | PROT_WRITE,
                                            MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    assert(shared != MAP_FAILED);
    struct apo_volume_state old = sample(1), next = sample(2), observed;
    apo_volume_publish(shared, &old);
    /* Hold the writer halfway through its inactive slot: readers must still
     * obtain the complete last publication without spinning on a held lock. */
    unsigned inactive = (shared->sequence + 1) & 1;
    memcpy(&shared->slots[inactive], &next, sizeof(next)/2);
    for (unsigned i = 0; i < 10000; ++i) {
        assert(apo_volume_snapshot(shared, &observed));
        assert(memcmp(&observed, &old, sizeof(old)) == 0);
    }
    apo_volume_publish(shared, &next);
    assert(apo_volume_snapshot(shared, &observed));
    assert(memcmp(&observed, &next, sizeof(next)) == 0);
    /* A real invalidation must become visible, never replaced with cached data. */
    next.valid = 0; apo_volume_publish(shared, &next);
    assert(apo_volume_snapshot(shared, &observed) && observed.valid == 0);
    old = sample(3); apo_volume_publish(shared, &old);
    __atomic_store_n(&shared->sequence, UINT32_MAX, __ATOMIC_RELEASE);
    next = sample(4); apo_volume_publish(shared, &next);
    assert(shared->sequence == 0);
    assert(apo_volume_snapshot(shared, &observed));
    assert(memcmp(&observed, &next, sizeof(next)) == 0);

    pid_t writer = fork(); assert(writer >= 0);
    if (writer == 0) {
        for (uint32_t i = 5; i < 500005; ++i) {
            struct apo_volume_state state = sample(i);
            apo_volume_publish(shared, &state);
            if ((i & 31) == 0) sched_yield();
        }
        _exit(0);
    }
    unsigned accepted = 0;
    for (unsigned i = 0; i < 500000; ++i) {
        if (!apo_volume_snapshot(shared, &observed)) continue;
        struct apo_volume_state expected = sample((uint32_t)observed.timestamp_100ns);
        assert(memcmp(&observed, &expected, sizeof(expected)) == 0);
        ++accepted;
    }
    int status; assert(waitpid(writer, &status, 0) == writer);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 0 && accepted > 1000);
    munmap(shared, sizeof(*shared));
    printf("paused publisher, invalidation, wraparound and %u coherent concurrent reads: passed\n", accepted);
    return 0;
}
