#include <assert.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "juice.h"
#define MAX_CANDIDATES 32
struct endpoint { juice_agent_t *agent; pthread_mutex_t mutex; char cand[MAX_CANDIDATES][JUICE_MAX_CANDIDATE_SDP_STRING_LEN]; int count; bool done; atomic_int state; atomic_int received; };
static void candidate(juice_agent_t *a, const char *s, void *u) { (void)a; struct endpoint* e=u; pthread_mutex_lock(&e->mutex); assert(e->count<MAX_CANDIDATES); snprintf(e->cand[e->count++], sizeof(e->cand[0]), "%s", s); pthread_mutex_unlock(&e->mutex); }
static void done(juice_agent_t *a, void *u) { (void)a; struct endpoint* e=u; pthread_mutex_lock(&e->mutex); e->done=true; pthread_mutex_unlock(&e->mutex); }
static void state(juice_agent_t *a, juice_state_t s, void *u) { (void)a; struct endpoint* e=u; atomic_store(&e->state,s); }
static void recv_data(juice_agent_t *a, const char *data, size_t size, void *u) { (void)a; struct endpoint* e=u; if(size==4 && memcmp(data,"ping",4)==0) atomic_store(&e->received,1); }
static bool transfer(struct endpoint* from, struct endpoint* to) { char c[MAX_CANDIDATES][JUICE_MAX_CANDIDATE_SDP_STRING_LEN]; int n; bool finished; pthread_mutex_lock(&from->mutex); n=from->count; memcpy(c,from->cand,sizeof(c[0])*n);from->count=0; finished=from->done;from->done=false;pthread_mutex_unlock(&from->mutex); for(int i=0;i<n;i++) assert(juice_add_remote_candidate(to->agent,c[i])==0); if(finished) assert(juice_set_remote_gathering_done(to->agent)==0); return finished; }
static bool connected(struct endpoint* e) { int s=atomic_load(&e->state); return s==JUICE_STATE_CONNECTED || s==JUICE_STATE_COMPLETED; }
static void run_pair(bool legacy_controlled) {
 struct endpoint a={.mutex=PTHREAD_MUTEX_INITIALIZER},b={.mutex=PTHREAD_MUTEX_INITIALIZER};
 juice_config_t cfg={0};cfg.concurrency_mode=JUICE_CONCURRENCY_MODE_POLL;cfg.cb_candidate=candidate;cfg.cb_gathering_done=done;cfg.cb_state_changed=state;cfg.cb_recv=recv_data;cfg.user_ptr=&a;a.agent=juice_create(&cfg);cfg.user_ptr=&b;b.agent=juice_create(&cfg);assert(a.agent&&b.agent);
 char sdp[JUICE_MAX_SDP_STRING_LEN];
 assert(juice_get_local_description(a.agent,sdp,sizeof(sdp))==0);assert(juice_set_remote_description(b.agent,sdp)==0);
 assert(juice_get_local_description(b.agent,sdp,sizeof(sdp))==0);assert(juice_set_remote_description(a.agent,sdp)==0);
 if(!legacy_controlled) assert(juice_gather_candidates(b.agent)==0);assert(juice_gather_candidates(a.agent)==0);
 for(int i=0;i<500 && !(connected(&a)&&connected(&b));i++){ if(transfer(&a,&b) && legacy_controlled) { assert(juice_gather_candidates(b.agent)==0); legacy_controlled=false; } transfer(&b,&a);usleep(10000);}
 assert(connected(&a)&&connected(&b));assert(juice_send(a.agent,"ping",4)==0);assert(juice_send(b.agent,"ping",4)==0);
 for(int i=0;i<100 && !(atomic_load(&a.received)&&atomic_load(&b.received));i++)usleep(10000);
 assert(atomic_load(&a.received)&&atomic_load(&b.received));juice_destroy(a.agent);juice_destroy(b.agent);
}

int main(void) { run_pair(false); run_pair(true); puts("simultaneous and legacy-controlled ICE; bidirectional UDP: ok"); }
