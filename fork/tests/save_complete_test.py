"""Run the real completion function against isolated save buffers."""
from pathlib import Path
import subprocess, tempfile
root = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android', 'VR'):
    source = (root/platform/'src/game/save_file.c').read_text()
    block = source[source.index('bool save_file_complete_vanilla('):source.index('\nvoid save_file_erase(', source.index('bool save_file_complete_vanilla('))]
    header = (root/platform/'src/game/save_file.h').read_text()
    definitions = '\n'.join(line for line in header.splitlines() if line.startswith('#define SAVE_FLAG_') or line.startswith('#define STAR_FLAG_TO_SAVE_FLAG'))
    program = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
typedef int32_t s32;
#define NUM_SAVE_FILES 4
#define COURSE_STAGES_COUNT 15
#define COURSE_BITDW 16
#define COURSE_PSS 19
#define COURSE_SA 24
#define INVALID_FILE_INDEX(i) ((uint32_t)(i) >= NUM_SAVE_FILES)
#define TRUE 1
DEFINITIONS
struct SaveFile { unsigned flags; unsigned char courseStars[25], courseCoinScores[15]; };
struct { struct SaveFile files[4][2]; } gSaveBuffer;
int gNetworkType, gSaveFileModified, saved;
enum { NT_NONE, NT_SERVER, NT_CLIENT };
void save_file_do_save(s32 i, int force) { assert(i==2 && force && gSaveFileModified); saved++; }
BLOCK
int main(void) {
    gSaveBuffer.files[2][0].courseCoinScores[1]=200;
    gSaveBuffer.files[2][0].courseStars[24]=8;
    gSaveBuffer.files[2][1].flags=42;
    assert(!save_file_complete_vanilla(-1));
    gNetworkType=NT_CLIENT; assert(!save_file_complete_vanilla(2)); assert(!saved);
    gNetworkType=NT_NONE; assert(save_file_complete_vanilla(2)); assert(saved==1);
    int count=0; for(int i=0;i<24;i++) for(int b=0;b<7;b++) count += !!(gSaveBuffer.files[2][0].courseStars[i] & (1<<b));
    for(int b=24;b<29;b++) count += !!(gSaveBuffer.files[2][0].flags & (1u<<b));
    assert(count==120);
    assert(gSaveBuffer.files[2][0].courseCoinScores[1]==200 && gSaveBuffer.files[2][0].courseStars[24]==8);
    assert(gSaveBuffer.files[2][1].flags==42 && gSaveBuffer.files[1][0].flags==0);
    assert(gSaveBuffer.files[2][0].flags & SAVE_FLAG_UNLOCKED_50_STAR_DOOR);
}
'''.replace('DEFINITIONS', definitions).replace('BLOCK', block)
    with tempfile.TemporaryDirectory() as tmp:
        exe = str(Path(tmp)/'save-test')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-x','c','-','-o',exe],input=program.encode(),check=True)
        subprocess.run([exe],check=True)
    print(platform, '120 stars, persistence call, existing data and offline guard: ok')
