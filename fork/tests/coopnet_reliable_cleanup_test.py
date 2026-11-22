"""Exercise the real reliable-list cleanup with retained shutdown packets."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android', 'VR', 'WiiU'):
    text = (ROOT / platform / 'src/pc/network/packets/packet_reliable.c').read_text()
    start = text.index('struct PacketLinkedList {')
    end = text.index('\nvoid network_forget_all_reliable_from', start)
    code = '''#include <stdlib.h>
#include <stdbool.h>
#include <assert.h>
#define LOG_INFO(...) ((void)0)
typedef float f32;
struct Packet { bool keepSendingAfterDisconnect; void *addr; };
''' + text[start:end] + '''
static struct PacketLinkedList *add(bool keep) {
    struct PacketLinkedList *n = calloc(1, sizeof(*n));
    n->p.keepSendingAfterDisconnect = keep; n->prev = tail;
    if (tail) tail->next = n; else head = n;
    tail = n; return n;
}
int main(void) {
    struct PacketLinkedList *a = add(true); add(false);
    struct PacketLinkedList *b = add(true); add(false);
    network_forget_all_reliable();
    assert(head == a && tail == b && a->prev == NULL && a->next == b && b->prev == a && b->next == NULL);
    a->p.keepSendingAfterDisconnect = false; b->p.keepSendingAfterDisconnect = false;
    network_forget_all_reliable(); assert(head == NULL && tail == NULL);
}'''
    with tempfile.TemporaryDirectory() as folder:
        exe = str(Path(folder) / 'test')
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-fsanitize=address,undefined', '-x', 'c', '-', '-o', exe], input=code.encode(), check=True)
        subprocess.run([exe], check=True, stdout=subprocess.DEVNULL)
    print(platform, 'reliable cleanup ok')
