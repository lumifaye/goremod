#include <assert.h>
#include "ice.h"
int main(void) {
    ice_candidate_t c;
    assert(ice_parse_candidate_sdp("a=candidate:1 1 UDP 100 2001:db8::1 30000 typ host", &c) == ICE_PARSE_IGNORED);
    assert(ice_parse_candidate_sdp("a=candidate:2 1 UDP 99 192.0.2.1 30000 typ relay", &c) == 0);
    assert(c.resolved.len && c.resolved.addr.ss_family == AF_INET);
}
