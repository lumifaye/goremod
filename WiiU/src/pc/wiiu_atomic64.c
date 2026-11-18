#ifdef TARGET_WII_U

#include <stdbool.h>
#include <stdint.h>
#include <coreinit/interrupts.h>

// The Wii U's processor is 32-bit: it can change a 32-bit number in one step that nothing can get
// in between, and a 64-bit number it cannot. Where a program asks for that all the same (miniaudio
// does, for the position in a sound), the compiler calls the functions below instead of making the
// step itself, and expects somebody to provide them. On a PC that is a library called libatomic,
// which the Wii U compiler does not come with. So here they are: each one keeps the others out
// (interrupts off on this core, a lock against the other cores), does its work, and lets them in.
//
// The names the compiler calls are given with __asm__, since C does not let a function with one of
// those names be written directly.

static volatile unsigned char sAtomic64Lock = 0;

static inline BOOL atomic64_enter(void) {
    BOOL interrupts = OSDisableInterrupts();
    while (__atomic_test_and_set(&sAtomic64Lock, __ATOMIC_SEQ_CST)) { }
    return interrupts;
}

static inline void atomic64_leave(BOOL interrupts) {
    __atomic_clear(&sAtomic64Lock, __ATOMIC_SEQ_CST);
    OSRestoreInterrupts(interrupts);
}

uint64_t wiiu_atomic_load_8(const volatile void* ptr, int order) __asm__("__atomic_load_8");
void wiiu_atomic_store_8(volatile void* ptr, uint64_t value, int order) __asm__("__atomic_store_8");
uint64_t wiiu_atomic_exchange_8(volatile void* ptr, uint64_t value, int order) __asm__("__atomic_exchange_8");
bool wiiu_atomic_compare_exchange_8(volatile void* ptr, void* expected, uint64_t desired, int success, int failure) __asm__("__atomic_compare_exchange_8");
uint64_t wiiu_atomic_fetch_add_8(volatile void* ptr, uint64_t value, int order) __asm__("__atomic_fetch_add_8");
uint64_t wiiu_atomic_fetch_sub_8(volatile void* ptr, uint64_t value, int order) __asm__("__atomic_fetch_sub_8");
uint64_t wiiu_atomic_fetch_and_8(volatile void* ptr, uint64_t value, int order) __asm__("__atomic_fetch_and_8");
uint64_t wiiu_atomic_fetch_or_8(volatile void* ptr, uint64_t value, int order) __asm__("__atomic_fetch_or_8");
uint64_t wiiu_atomic_fetch_xor_8(volatile void* ptr, uint64_t value, int order) __asm__("__atomic_fetch_xor_8");

uint64_t wiiu_atomic_load_8(const volatile void* ptr, int order) {
    (void) order;
    BOOL interrupts = atomic64_enter();
    uint64_t value = *(const volatile uint64_t*) ptr;
    atomic64_leave(interrupts);
    return value;
}

void wiiu_atomic_store_8(volatile void* ptr, uint64_t value, int order) {
    (void) order;
    BOOL interrupts = atomic64_enter();
    *(volatile uint64_t*) ptr = value;
    atomic64_leave(interrupts);
}

uint64_t wiiu_atomic_exchange_8(volatile void* ptr, uint64_t value, int order) {
    (void) order;
    BOOL interrupts = atomic64_enter();
    uint64_t old = *(volatile uint64_t*) ptr;
    *(volatile uint64_t*) ptr = value;
    atomic64_leave(interrupts);
    return old;
}

bool wiiu_atomic_compare_exchange_8(volatile void* ptr, void* expected, uint64_t desired, int success, int failure) {
    (void) success;
    (void) failure;
    BOOL interrupts = atomic64_enter();
    uint64_t old = *(volatile uint64_t*) ptr;
    bool same = (old == *(uint64_t*) expected);
    if (same) {
        *(volatile uint64_t*) ptr = desired;
    } else {
        *(uint64_t*) expected = old;
    }
    atomic64_leave(interrupts);
    return same;
}

#define WIIU_ATOMIC_FETCH(name, operation)                                        \
    uint64_t wiiu_atomic_fetch_##name##_8(volatile void* ptr, uint64_t value, int order) { \
        (void) order;                                                             \
        BOOL interrupts = atomic64_enter();                                       \
        uint64_t old = *(volatile uint64_t*) ptr;                                 \
        *(volatile uint64_t*) ptr = old operation value;                          \
        atomic64_leave(interrupts);                                               \
        return old;                                                               \
    }

WIIU_ATOMIC_FETCH(add, +)
WIIU_ATOMIC_FETCH(sub, -)
WIIU_ATOMIC_FETCH(and, &)
WIIU_ATOMIC_FETCH(or, |)
WIIU_ATOMIC_FETCH(xor, ^)

#endif // TARGET_WII_U
