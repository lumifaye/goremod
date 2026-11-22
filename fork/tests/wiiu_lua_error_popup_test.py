"""Check Wii U Lua error reporting without requiring the console SDK."""
from pathlib import Path
import subprocess
import tempfile

src = (Path(__file__).resolve().parents[2] / 'WiiU/src/pc/lua/smlua.c').read_text()
a = src.index('#ifdef TARGET_WII_U\n// Keep a few distinct errors')
b = src.index('\n#ifdef TARGET_WII_U\nstatic void smlua_wiiu_step', a)
code = '''#include <stdio.h>
#include <string.h>
#include <assert.h>
#define TARGET_WII_U
#define SMLUA_WIIU_LOG(...) ((void)0)
static void *gDjuiRoot;
static int count;
static char last[224];
static void djui_popup_create(const char *s, int lines) { assert(lines == 4); ++count; snprintf(last, sizeof(last), "%s", s); }
''' + src[a:b] + '''
int main(void) {
    smlua_platform_log_lua("not ready"); assert(count == 0);
    gDjuiRoot = &count;
    smlua_platform_log_lua(NULL); smlua_platform_log_lua(""); assert(count == 0);
    smlua_platform_log_lua("persist.lua:42: bad value"); assert(count == 1 && strstr(last, "persist.lua:42"));
    smlua_platform_log_lua("persist.lua:42: bad value"); assert(count == 1);
    smlua_platform_log_lua("two"); smlua_platform_log_lua("three"); smlua_platform_log_lua("four"); assert(count == 3);
    memset(sWiiULuaErrors, 0, sizeof(sWiiULuaErrors));
    smlua_platform_log_lua("four"); assert(count == 4);
}'''
with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / 'test'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-x', 'c', '-', '-o', str(exe)], input=code.encode(), check=True)
    subprocess.run([str(exe)], check=True)
print('Wii U Lua error popup: bounded, deduplicated, and resettable')
