"""Exercise the real adapters' callbacks without the coordinator or a console."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android', 'VR', 'WiiU'):
    source = (ROOT / platform / 'src/pc/network/coopnet/coopnet.c').read_text()
    test = '''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <inttypes.h>
#define NT_CLIENT 1
#define NT_SERVER 2
#define LOG_INFO(...) ((void)0)
#define MAX_CONFIG_STRING 128
static int gNetworkType = NT_CLIENT, requests;
static uint64_t sLocalLobbyOwnerId, sLocalLobbyId, gCoopNetDesiredLobby=10;
static bool gNetworkPlayerLocal, sHostHandshakeStarted, sJoinPending;
static unsigned sJoinPendingLobbyId,sJoinPendingStart,sJoinPendingLastSend,sJoinPendingAttempts,sJoinPendingLastProgressLog;
static char configDestId[128];
static void network_send_mod_list_request(void){ ++requests; }
static uint64_t coopnet_get_local_user_id(void){ return 2; }
static void coopnet_set_user_id(unsigned i,uint64_t n){}
static void coopnet_clear_dest_ids(void){}
static void coopnet_reserve_user_id(uint64_t n){}
static void coopnet_save_dest_id(uint64_t n,uint64_t d){}
'''
    for name in ('coopnet_start_join_once', 'coopnet_on_peer_connected', 'coopnet_on_lobby_joined'):
        start = source.index('static void ' + name + '(')
        test += source[start:source.index('\n}', start)+2] + '\n'
    test += '''int main(void){
        coopnet_on_peer_connected(1); assert(requests==0);
        coopnet_on_lobby_joined(9,2,1,3); assert(requests==0);
        coopnet_on_lobby_joined(10,2,1,3); assert(requests==1);
        coopnet_on_peer_connected(1); coopnet_on_lobby_joined(10,1,1,4); assert(requests==1);
        sHostHandshakeStarted=false; gNetworkType=NT_SERVER;
        coopnet_on_lobby_joined(10,3,2,5); coopnet_on_peer_connected(3); assert(requests==1);
    }'''
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / 'test'
        subprocess.run(['cc','-x','c','-','-o',exe],input=test.encode(),check=True)
        subprocess.run([exe],check=True)
    print(platform, 'handshake order OK')
