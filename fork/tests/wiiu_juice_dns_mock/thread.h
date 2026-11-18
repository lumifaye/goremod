#pragma once
typedef int mutex_t;
#define MUTEX_INITIALIZER 0
static inline void mutex_lock(mutex_t *m) { (void)m; }
static inline void mutex_unlock(mutex_t *m) { (void)m; }
