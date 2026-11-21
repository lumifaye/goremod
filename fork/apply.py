"""Turns a checkout of SM64 Coop DX (or of one of two forks of it) into this project's build of the game.

    python3 fork/apply.py <base> <directory>

<base> is one of
    pc       the official game                        -> Windows / Linux, flat screen
    vr       the VR fork (one source for both)        -> Windows PC VR, and the Quest APK
    android  the Android port                         -> phone / tablet APK

If <directory> doesn't exist, the base is copied into it first: from this repository's own copy of it (the
folders PC, VR and Android), or, where that folder isn't there, from the original at the pinned commit. Then
the same set of changes is made to it, whichever base it is:

    1. The object limit goes from 1200 to OBJECT_POOL.
    2. This repository's mod is compiled into the program (EMBEDDED_MODS): its files are bytes inside it,
       it is in no mods folder and in no list of mods, and its switches are under their own button in the
       pause menu. Every mod in the repository MODS_REPO is copied into the game's mods folder: always on
       for whoever hosts, locked in the mods menu. Mods that the game can't run together (two romhacks)
       come with the game too, but are the host's choice.
    3. The build gets its own name, its own version string and its own lobby list on CoopNet, so that it
       only ever meets itself: the official game and this one would otherwise drift apart mid-game.
    4. The update checks are switched off (they would replace this build with the original).
    5. The Android apps get their own app id, name and signing key, so they install next to the originals.
    6. VR and flat players share one lobby list. What a VR player does with his hands and his VR-only
       power-ups is handed to the built-in mod, which shows it on every build (see vrsync.lua).
    7. The flat builds get voice chat that talks to the VR builds' own (fork_voice.c, written from here).
    8. The VR builds show a dead player from outside: third person while he is dead (the mod says when).
    9. Every build draws a VR player's Mario with his arms reaching for where his hands are, his own hands
       there, and his body turned the way his headset points (the mod says where; the VR builds tell it).
   10. A VR player's punch hits where his glove is: another player is as big as his Mario, and the fist
       no longer reaches below itself (the VR builds; PUNCH_BODY_RADIUS, PUNCH_COLLIDER_LENGTH).

Every change is a piece of text that has to be found exactly as written here, exactly as often as expected.
If a base has moved on and a piece isn't found, this stops with an error instead of building something
half-changed. Nothing here needs anything but Python 3 and git.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


GAME_TITLE = "Realism64!!- COOP NET SUPPORT!!!111"

VERSION_SUFFIX = "-gore1"

COOPNET_GAME = "lumi64"

OBJECT_POOL = 30000

PUNCH_BODY_RADIUS = 30
PUNCH_COLLIDER_LENGTH = 100

BUILT_IN_MODS = ["Gore-Hardmode"]

EMBEDDED_MODS = ["Gore-Hardmode"]
EMBEDDED_FOLDER = "realism64"
SETTINGS_LABEL = "Gore Settings"
EMBEDDED_COUNT = "fork-embedded-files.txt"
EMBEDDED_HEADING = "REALISM64-EMBEDDED-1\n"

CHOICE_MODS = []

MODS_REPO = "https://github.com/lumifaye/mbjmnmnmnmn.git"
MODS_REF = "main"
SHIPPED_LIST = "fork-built-in-mods.txt"

APP_ID_SUFFIX = ".gore"
MAC_BUNDLE_ID = "io.github.lumifaye.realism64"
KEYSTORE = "signing/gore-fork.p12"

BASES = {
    "pc": {
        "folder": "PC",
        "repo": "https://github.com/coop-deluxe/sm64coopdx.git",
        "commit": "8cd6e5977d9f920d51ca71f2c61801d019ed79c6",
        "tree": "eb26789dd1fe652435971abe1808c02682ec32ed",
    },
    "vr": {
        "folder": "VR",
        "repo": "https://github.com/fulldivegames/sm64coopdx-VR-Standalone-Physics-based.git",
        "commit": "8bf8dd27e8f217bf146a4bda9c4d8922fb0e2e1e",
        "tree": "3ac1d499a2a5375c1589b71e1548d7f90de62bf7",
    },
    "android": {
        "folder": "Android",
        "repo": "https://github.com/ManIsCat2/sm64coopdx.git",
        "commit": "99c8d21abe4d24649b508d0f216c4359ed5d2a7a",
        "tree": "5a1bcacaf4ad8c921721e7c48f0f107a10cb1851",
    },
}

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

NOT_THE_MOD = {"site", "fork", "release", "dist", "node_modules", "xbox360-port", "Untitled.png", "WiiU", "PC", "VR", "Android"}


class Problem(Exception):
    pass



class Tree:
    def __init__(self, root):
        self.root = root
        self.log = []

    def path(self, rel):
        return os.path.join(self.root, *rel.split("/"))

    def exists(self, rel):
        return os.path.exists(self.path(rel))

    def read(self, rel):
        with open(self.path(rel), "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
        crlf = "\r\n" in text
        return text.replace("\r\n", "\n"), crlf

    def write(self, rel, text, crlf):
        if crlf:
            text = text.replace("\n", "\r\n")
        with open(self.path(rel), "wb") as f:
            f.write(text.encode("utf-8"))

    def replace(self, rel, old, new, count=1):
        """`old` has to be in the file exactly `count` times; every one becomes `new`."""
        text, crlf = self.read(rel)
        found = text.count(old)
        if found != count:
            first = old.strip().split("\n")[0]
            raise Problem("%s: expected %d of %r, found %d" % (rel, count, first, found))
        self.write(rel, text.replace(old, new), crlf)
        self.log.append(rel)

    def after(self, rel, anchor, addition):
        self.replace(rel, anchor, anchor + addition)

    def before(self, rel, anchor, addition):
        self.replace(rel, anchor, addition + anchor)


def c_string_list(names):
    return ", ".join('"%s"' % n.replace("\\", "\\\\").replace('"', '\\"') for n in names)



def object_limit(t):
    if not 1200 <= OBJECT_POOL <= 32767:
        raise Problem("OBJECT_POOL has to be between 1200 and 32767")

    t.replace("src/game/object_list_processor.h",
              "#define OBJECT_POOL_CAPACITY 1200\n",
              "#define OBJECT_POOL_CAPACITY %d // [gore fork] the game has 1200\n" % OBJECT_POOL)

    t.replace("src/pc/lua/smlua_constants_autogen.c",
              '"OBJECT_POOL_CAPACITY=1200\\n"',
              '"OBJECT_POOL_CAPACITY=%d\\n"' % OBJECT_POOL)

    t.after("src/game/object_list_processor.h",
            "extern struct Object gObjectPool[];\n",
            "extern u32 gObjectPoolHighWater; // [gore fork] slots of the pool that have ever been in use\n")
    t.before("src/game/spawn_object.c",
             "struct Object *try_allocate_object(struct ObjectNode *destList, struct ObjectNode *freeList) {\n",
             "// [gore fork] How far into gObjectPool objects have ever been handed out (see clear_dynamic_surfaces).\n"
             "u32 gObjectPoolHighWater = 0;\n"
             "\n")
    t.after("src/game/spawn_object.c",
            "    if ((nextObj = freeList->next) != NULL) {\n"
            "        // Remove from free list\n"
            "        freeList->next = nextObj->next;\n",
            "\n"
            "        // [gore fork]\n"
            "        u32 poolSlots = (u32) ((struct Object *) nextObj - gObjectPool) + 1;\n"
            "        if (poolSlots > gObjectPoolHighWater) { gObjectPoolHighWater = poolSlots; }\n")
    t.replace("src/engine/surface_load.c",
              "    for (u16 i = 0; i < OBJECT_POOL_CAPACITY; i++) {\n"
              "        gObjectPool[i].numSurfaces = 0;\n",
              "    for (u32 i = 0; i < gObjectPoolHighWater; i++) { // [gore fork] was: every slot of the pool\n"
              "        gObjectPool[i].numSurfaces = 0;\n")

    # A crowded previous level should not inflate every later frame's surface reset.
    t.after("src/game/object_list_processor.c", "    init_free_object_list();\n",
            "    for (u32 slot = 0; slot < gObjectPoolHighWater; ++slot) { gObjectPool[slot].numSurfaces = 0; }\n"
            "    gObjectPoolHighWater = 0;\n")

    walk_guard = OBJECT_POOL + 5000
    t.replace("src/game/rendering_graph_node.c",
              "#define MAX_GRAPH_NODE_DEPTH 5000\n",
              "#define MAX_GRAPH_NODE_DEPTH %d // [gore fork] was 5000; every object may be in one ring\n"
              % walk_guard)
    t.replace("src/engine/graph_node.c",
              "    geo_add_child(&gObjParentGraphNode, &graphNode->node);\n"
              "    graphNode->node.flags &= ~GRAPH_RENDER_ACTIVE;\n",
              "    // [gore fork] was: geo_add_child(&gObjParentGraphNode, &graphNode->node);\n"
              "    // A free slot is not in the ring of drawn objects; try_allocate_object puts it there.\n"
              "    graphNode->node.flags &= ~GRAPH_RENDER_ACTIVE;\n")
    t.before("src/game/object_list_processor.c",
             "    for (i = 0; i < OBJECT_POOL_CAPACITY; i++) {\n"
             "        gObjectPool[i].activeFlags = ACTIVE_FLAG_DEACTIVATED;\n",
             "    // [gore fork] the ring of drawn objects starts empty (the slots are reset below)\n"
             "    extern struct GraphNode gObjParentGraphNode;\n"
             "    gObjParentGraphNode.children = NULL;\n"
             "\n")
    t.replace("src/game/spawn_object.c",
              "    geo_remove_child(&obj->header.gfx.node);\n"
              "    geo_add_child(&gObjParentGraphNode, &obj->header.gfx.node);\n",
              "    geo_remove_child(&obj->header.gfx.node);\n"
              "    // [gore fork] was: geo_add_child(&gObjParentGraphNode, &obj->header.gfx.node);\n"
              "    obj->header.gfx.node.parent = NULL;\n")
    t.after("src/game/area.c",
            "    struct Object *sp20 = (struct Object *) gObjParentGraphNode.children;\n",
            "    if (sp20 == NULL) { return; } // [gore fork] no objects\n")



MODS_EMBEDDED_C = """\
  ////////////////////////////
 // [gore fork] embedded   //
////////////////////////////

// Mods that are compiled into the program: fork_embedded.c puts their files into it as one block of bytes
// (a short heading, then for each file the length of its name, its name, its size and its bytes).
// They are part of the game. No list of mods shows them and they are in no mods folder.
//
// The game's loaders (Lua, models, sounds, levels) all want files to open, so at the start the block is
// written out, to "<where the saves are>/%(folder)s/<name>". That happens once: after it, every start
// only looks whether the files are still there and the scripts still say what the program has (if not, a
// file is missing, or what is there is from another version of the program, all of it is written again).

#define FORK_EMBEDDED_SIZE      %(size)du
#define FORK_EMBEDDED_FILES     %(count)d
#define FORK_EMBEDDED_HEADING   "%(heading)s"
#define FORK_EMBEDDED_DIRECTORY "%(folder)s"

extern const unsigned char gForkEmbeddedData[];

static const char* sForkEmbeddedMods[] = { %(embedded)s };
static char sForkEmbeddedPath[SYS_MAX_PATH] = { 0 };
static bool sForkEmbeddedReady = false;
static bool sForkEmbeddedLoading = false;

struct ForkEmbeddedFile {
    const char* name; // (not ended by a zero)
    u32 nameLength;
    const u8* data;
    u32 size;
};

static bool mods_fork_is_embedded(const char* modName) {
    if (modName == NULL) { return false; }
    for (size_t i = 0; i < sizeof(sForkEmbeddedMods) / sizeof(sForkEmbeddedMods[0]); i++) {
        if (!strcmp(modName, sForkEmbeddedMods[i])) { return true; }
    }
    return false;
}

bool mods_fork_is_hidden(struct Mod* mod) {
    return mod != NULL && mods_fork_is_embedded(mod->relativePath);
}

// The next file of the block. `at` starts behind the heading and ends at FORK_EMBEDDED_SIZE.
static bool fork_embedded_next(size_t* at, struct ForkEmbeddedFile* file) {
    const u8* d = gForkEmbeddedData;
    size_t i = *at;
    if (i + 2 > FORK_EMBEDDED_SIZE) { return false; }
    file->nameLength = (u32) d[i] | ((u32) d[i + 1] << 8);
    i += 2;
    if (file->nameLength == 0 || file->nameLength > 512 || i + file->nameLength + 4 > FORK_EMBEDDED_SIZE) { return false; }
    file->name = (const char*) &d[i];
    i += file->nameLength;
    file->size = (u32) d[i] | ((u32) d[i + 1] << 8) | ((u32) d[i + 2] << 16) | ((u32) d[i + 3] << 24);
    i += 4;
    if (file->size > FORK_EMBEDDED_SIZE - i) { return false; }
    file->data = &d[i];
    *at = i + file->size;
    return true;
}

static bool fork_embedded_path_of(char* path, const struct ForkEmbeddedFile* file) {
    return snprintf(path, SYS_MAX_PATH, "%%s/%%.*s", sForkEmbeddedPath, (int) file->nameLength, file->name) < SYS_MAX_PATH;
}

static bool fork_embedded_name_ends(const struct ForkEmbeddedFile* file, const char* ending) {
    size_t length = strlen(ending);
    return file->nameLength >= length && !memcmp(file->name + file->nameLength - length, ending, length);
}

// Is this file on the disk? Scripts (and the note that says which build the files are from, which is the
// last file written) have to be the program's, byte for byte; of the rest it is enough that it is there
// (the game may pack a model anew, and it weighs 28 MB to read through).
static bool fork_embedded_file_is_there(const char* path, const struct ForkEmbeddedFile* file) {
    FILE* f = fopen(path, "rb");
    if (f == NULL) { return false; }
    bool right = true;
    if (fork_embedded_name_ends(file, ".lua") || fork_embedded_name_ends(file, ".txt")) {
        u8* buffer = malloc(file->size + 1);
        right = buffer != NULL
            && fread(buffer, 1, file->size + 1, f) == file->size
            && !memcmp(buffer, file->data, file->size);
        free(buffer);
    }
    fclose(f);
    return right;
}

// Is there anything at the top of a mod's folder that the program doesn't have? (A script somebody put
// there would be run as part of the mod.)
static bool fork_embedded_has_strangers(const char* modName) {
    char path[SYS_MAX_PATH] = { 0 };
    if (snprintf(path, SYS_MAX_PATH, "%%s/%%s", sForkEmbeddedPath, modName) >= SYS_MAX_PATH) { return true; }
    DIR* d = opendir(path);
    if (d == NULL) { return true; }
    bool strangers = false;
    size_t modLength = strlen(modName);
    struct dirent* entry = NULL;
    while (!strangers && (entry = readdir(d)) != NULL) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) { continue; }
        size_t length = strlen(entry->d_name);
        bool known = false;
        size_t at = strlen(FORK_EMBEDDED_HEADING);
        struct ForkEmbeddedFile file = { 0 };
        while (!known && at < FORK_EMBEDDED_SIZE && fork_embedded_next(&at, &file)) {
            // "<mod>/<entry>" or "<mod>/<entry>/..."
            if (file.nameLength < modLength + 1 + length) { continue; }
            if (memcmp(file.name, modName, modLength) || file.name[modLength] != '/') { continue; }
            if (memcmp(file.name + modLength + 1, entry->d_name, length)) { continue; }
            known = file.nameLength == modLength + 1 + length || file.name[modLength + 1 + length] == '/';
        }
        strangers = !known;
    }
    closedir(d);
    return strangers;
}

static bool fork_embedded_is_written(void) {
    size_t at = strlen(FORK_EMBEDDED_HEADING);
    struct ForkEmbeddedFile file = { 0 };
    char path[SYS_MAX_PATH] = { 0 };
    while (at < FORK_EMBEDDED_SIZE) {
        if (!fork_embedded_next(&at, &file)) { return false; }
        if (!fork_embedded_path_of(path, &file)) { return false; }
        if (!fork_embedded_file_is_there(path, &file)) { return false; }
    }
    for (size_t i = 0; i < sizeof(sForkEmbeddedMods) / sizeof(sForkEmbeddedMods[0]); i++) {
        if (fork_embedded_has_strangers(sForkEmbeddedMods[i])) { return false; }
    }
    return true;
}

// (only ever called for "<where the saves are>/%(folder)s/<one of the names above>")
static void fork_embedded_remove_tree(const char* path) {
    DIR* d = opendir(path);
    if (d == NULL) {
        remove(path);
        return;
    }
    struct dirent* entry = NULL;
    while ((entry = readdir(d)) != NULL) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) { continue; }
        char child[SYS_MAX_PATH] = { 0 };
        if (snprintf(child, SYS_MAX_PATH, "%%s/%%s", path, entry->d_name) >= SYS_MAX_PATH) { continue; }
#if !defined(_WIN32) && !defined(TARGET_XBOX360) // xSDK title storage has no POSIX symlinks
        // (a link is taken away; what it points to is left alone)
        struct stat info = { 0 };
        if (lstat(child, &info) == 0 && S_ISLNK(info.st_mode)) {
            remove(child);
            continue;
        }
#endif
        if (fs_sys_dir_exists(child)) {
            fork_embedded_remove_tree(child);
        } else {
            remove(child);
        }
    }
    closedir(d);
    fs_sys_rmdir(path);
}

static bool fork_embedded_write_file(char* path, const struct ForkEmbeddedFile* file) {
    // the folders on the way, below the one all of it is in
    for (char* c = path + strlen(sForkEmbeddedPath) + 1; *c != '\\0'; c++) {
        if (*c != '/') { continue; }
        *c = '\\0';
        if (!fs_sys_dir_exists(path)) { fs_sys_mkdir(path); }
        *c = '/';
    }
    FILE* f = fopen(path, "wb");
    if (f == NULL) { return false; }
    bool written = file->size == 0 || fwrite(file->data, 1, file->size, f) == file->size;
    if (fclose(f) != 0) { written = false; }
    return written;
}

// Makes sure the files are on the disk. Called at the start of the program, and before the mods are
// looked for (whichever comes first does the work).
void mods_fork_embedded_unpack(void) {
    if (sForkEmbeddedReady) { return; }

    const char* base = fs_get_write_path(FORK_EMBEDDED_DIRECTORY);
    if (base == NULL || snprintf(sForkEmbeddedPath, SYS_MAX_PATH, "%%s", base) >= SYS_MAX_PATH) {
        sys_fatal("The folder for the game's own files has too long a name.");
    }
    if (memcmp(gForkEmbeddedData, FORK_EMBEDDED_HEADING, strlen(FORK_EMBEDDED_HEADING))) {
        sys_fatal("This copy of the game is damaged: its built-in files are not in it.");
    }

    if (!fork_embedded_is_written()) {
        LOG_INFO("Writing the game's built-in files to '%%s'", sForkEmbeddedPath);
        if (!fs_sys_dir_exists(sForkEmbeddedPath)) { fs_sys_mkdir(sForkEmbeddedPath); }
        char path[SYS_MAX_PATH] = { 0 };
        for (size_t i = 0; i < sizeof(sForkEmbeddedMods) / sizeof(sForkEmbeddedMods[0]); i++) {
            if (snprintf(path, SYS_MAX_PATH, "%%s/%%s", sForkEmbeddedPath, sForkEmbeddedMods[i]) < SYS_MAX_PATH) {
                fork_embedded_remove_tree(path);
            }
        }
        size_t at = strlen(FORK_EMBEDDED_HEADING);
        struct ForkEmbeddedFile file = { 0 };
        int count = 0;
        while (at < FORK_EMBEDDED_SIZE) {
            if (!fork_embedded_next(&at, &file) || !fork_embedded_path_of(path, &file)) {
                sys_fatal("This copy of the game is damaged: its built-in files can't be read.");
            }
            if (!fork_embedded_write_file(path, &file)) {
                sys_fatal("Could not write one of the game's own files:\\n%%s\\n\\nIs the disk full, or may the game not write there?", path);
            }
            count++;
        }
        if (count != FORK_EMBEDDED_FILES) {
            sys_fatal("This copy of the game is damaged: %%d of its %%d built-in files are in it.", count, FORK_EMBEDDED_FILES);
        }
    }
    sForkEmbeddedReady = true;
}

// The folder the embedded mods are loaded from.
const char* mods_fork_embedded_path(void) {
    mods_fork_embedded_unpack();
    return sForkEmbeddedPath;
}

// Loads them, by name: nothing else that may be in that folder. (They come with everything compiled, so
// there is nothing for DynOS to generate first, as it does for a folder of mods.)
void mods_fork_embedded_load(struct Mods* mods) {
    char base[SYS_MAX_PATH] = { 0 };
    if (snprintf(base, SYS_MAX_PATH, "%%s", mods_fork_embedded_path()) >= SYS_MAX_PATH) { return; }
    normalize_path(base);
    LOADING_SCREEN_MUTEX(snprintf(gCurrLoadingSegment.str, 256, "Loading The Game's Own Files"));
    sForkEmbeddedLoading = true;
    for (size_t i = 0; i < sizeof(sForkEmbeddedMods) / sizeof(sForkEmbeddedMods[0]); i++) {
        char name[SYS_MAX_PATH] = { 0 };
        snprintf(name, SYS_MAX_PATH, "%%s", sForkEmbeddedMods[i]);
        if (!mod_load(mods, base, name)) { break; }
    }
    sForkEmbeddedLoading = false;
}

"""

EMBEDDED_C_FILE = """\
// [gore fork] Made by fork/apply.py. Don't edit.
//
// The mods that are compiled into the program: the assembler puts the bytes of fork_embedded.bin, which is
// next to this file, into the program as they are, under the name gForkEmbeddedData. mods_utils.c reads
// them (see "embedded" there).
//
// The assembler looks for the file from where the compiler is run. The game's Makefile runs it in the top
// folder of the source, which is all that is known on Windows; the Android apps are compiled from
// elsewhere, so everywhere else the whole path is here, as it was when fork/apply.py ran. (Moved the
// source since? -DFORK_EMBEDDED_FILE='"<the path>"', or run fork/apply.py on a fresh copy.)

#define FORK_STR2(x) #x
#define FORK_STR(x) FORK_STR2(x)
#define FORK_SYMBOL FORK_STR(__USER_LABEL_PREFIX__) "gForkEmbeddedData"

#ifndef FORK_EMBEDDED_FILE
#if defined(_WIN32)
#define FORK_EMBEDDED_FILE "%(relative)s"
#else
#define FORK_EMBEDDED_FILE "%(absolute)s"
#endif
#endif

#if defined(__APPLE__)
#define FORK_SECTION ".section __DATA,__const\\n"
#define FORK_ELF ""
#define FORK_ELF_END ""
#elif defined(_WIN32)
#define FORK_SECTION ".section .rdata,\\"dr\\"\\n"
#define FORK_ELF ""
#define FORK_ELF_END ""
#else
#define FORK_SECTION ".section .rodata\\n"
#define FORK_ELF ".type " FORK_SYMBOL ", %%object\\n"
#define FORK_ELF_END ".size " FORK_SYMBOL ", .-" FORK_SYMBOL "\\n"
#endif

__asm__(
    FORK_SECTION
    ".p2align 4\\n"
    ".globl " FORK_SYMBOL "\\n"
    FORK_ELF
    FORK_SYMBOL ":\\n"
    ".incbin \\"" FORK_EMBEDDED_FILE "\\"\\n"
    ".byte 0\\n"
    FORK_ELF_END
    ".text\\n"
);

// (a file has to declare something)
typedef int ForkEmbeddedFileIsNotEmpty;
"""

MODS_UTILS_C = """\
  ////////////////////////////
 // [gore fork] built-in   //
////////////////////////////

// Mods that are part of this build of the game, and always on. Those that are compiled into the program
// are above ("embedded"). The others ship in the game's own mods folder, each with a file "built-in.txt"
// in it; the mods menu shows them ticked and locked. Whoever joins gets the host's mods as always.
// A folder of the same name that is not the one that came with the game (somebody's own copy, an old
// download, what an older build left in the mods folder) is not loaded at all.
//
// The second list is every mod that came with this build: the ones above, and the ones the host chooses
// from (mods the game can't run together). Those are ordinary mods in the menu; only "the copy that came
// with the game counts" goes for them too.

static const char* sForkBuiltInMods[] = { %(names)s };
static const char* sForkShippedMods[] = { %(shipped)s };

bool mods_fork_is_built_in(const char* modName) {
    if (modName == NULL) { return false; }
    for (size_t i = 0; i < sizeof(sForkBuiltInMods) / sizeof(sForkBuiltInMods[0]); i++) {
        if (!strcmp(modName, sForkBuiltInMods[i])) { return true; }
    }
    return false;
}

static bool mods_fork_is_shipped(const char* modName) {
    if (modName == NULL) { return false; }
    for (size_t i = 0; i < sizeof(sForkShippedMods) / sizeof(sForkShippedMods[0]); i++) {
        if (!strcmp(modName, sForkShippedMods[i])) { return true; }
    }
    return false;
}

bool mods_fork_is_foreign_copy(const char* fullPath, const char* modName) {
    // (compiled in: only what the program wrote out itself counts, and nothing else is loaded from there)
    if (mods_fork_is_embedded(modName)) { return !sForkEmbeddedLoading; }
    if (sForkEmbeddedLoading) { return true; }
    if (!mods_fork_is_shipped(modName)) { return false; }
    char stampPath[SYS_MAX_PATH] = { 0 };
    if (snprintf(stampPath, SYS_MAX_PATH, "%%s/built-in.txt", fullPath) >= SYS_MAX_PATH) { return true; }
    return !fs_sys_file_exists(stampPath);
}

void mods_fork_enable_built_in(void) {
    for (int i = 0; i < gLocalMods.entryCount; i++) {
        struct Mod* mod = gLocalMods.entries[i];
        if (mods_fork_is_built_in(mod->relativePath)) { mod->enabled = true; }
    }
}

"""


def shipped_mods():
    """The mods that are folders in the game's mods folder (the embedded ones are in the program)."""
    return [name for name in BUILT_IN_MODS + CHOICE_MODS if name not in EMBEDDED_MODS]


def built_in_mods_c(t, embedded):
    """`embedded`: what built_in_mods_files() says about the block of bytes it made."""
    f = "src/pc/mods/mods_utils.c"
    t.after(f, '#include "pc/debuglog.h"\n',
            '// [gore fork]\n'
            '#include <stdio.h>\n'
            '#include <stdlib.h>\n'
            '#include <string.h>\n'
            '#include <dirent.h>\n'
            '#include "pc/fs/fs.h"\n'
            '#include "pc/loading.h"\n')
    t.before(f, "void mods_update_selectable(void) {\n",
             MODS_EMBEDDED_C % {"size": embedded["size"], "count": embedded["count"],
                                "heading": EMBEDDED_HEADING.replace("\n", "\\n"),
                                "folder": EMBEDDED_FOLDER,
                                "embedded": c_string_list(EMBEDDED_MODS)} +
             MODS_UTILS_C % {"names": c_string_list(BUILT_IN_MODS),
                             "shipped": c_string_list(shipped_mods())})
    t.after("src/pc/mods/mods.h",
            "void mods_get_main_mod_name(char* destination, u32 maxSize);\n",
            "// [gore fork] the mods that are compiled into the program (mods_utils.c)\n"
            "#define FORK_SETTINGS_LABEL \"%s\"\n"
            "bool mods_fork_is_hidden(struct Mod* mod);\n"
            "void mods_fork_embedded_unpack(void);\n"
            "const char* mods_fork_embedded_path(void);\n"
            "void mods_fork_embedded_load(struct Mods* mods);\n" % SETTINGS_LABEL)

    t.before("src/pc/mods/mods.c",
             "    // sort\n"
             "    mods_sort(&gLocalMods);\n",
             "    // [gore fork] what is compiled into the program\n"
             "    mods_fork_embedded_load(&gLocalMods);\n"
             "\n")
    t.after("src/pc/pc_main.c",
            "    fs_init(gCLIOpts.savePath[0] ? gCLIOpts.savePath : sys_user_path());\n"
            "#endif\n",
            "    mods_fork_embedded_unpack(); // [gore fork]\n")

    t.after("src/pc/mods/mods.c",
            "        if (!mod->enabled) { continue; }\n"
            "        size_t size = mod_get_lua_size(mod);\n",
            "        if (mods_fork_is_built_in(mod->relativePath)) { continue; } // [gore fork] part of every lobby\n")
    built_in_mods_hidden(t)
    t.after(f,
            "void mods_update_selectable(void) {\n",
            "    mods_fork_enable_built_in(); // [gore fork]\n"
            "\n")
    t.after(f,
            "            if (mods_incompatible_match(mod, mod2)) {\n"
            "                mod->selectable = false;\n"
            "                break;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "\n"
            "    mods_size_enforce(&gLocalMods);\n",
            "\n"
            "    // [gore fork] part of the game: ticked, and not to be unticked\n"
            "    for (int i = 0; i < gLocalMods.entryCount; i++) {\n"
            "        struct Mod* mod = gLocalMods.entries[i];\n"
            "        if (mods_fork_is_built_in(mod->relativePath)) { mod->selectable = false; }\n"
            "    }\n")

    t.after("src/pc/mods/mods_utils.h",
            "void mods_update_selectable(void);\n",
            "// [gore fork]\n"
            "bool mods_fork_is_built_in(const char* modName);\n"
            "bool mods_fork_is_foreign_copy(const char* fullPath, const char* modName);\n"
            "void mods_fork_enable_built_in(void);\n")

    t.after("src/pc/mods/mods.c",
            "void mods_activate(struct Mods* mods) {\n"
            "    mods_clear(&gActiveMods);\n",
            "\n"
            "    if (mods == &gLocalMods) { mods_fork_enable_built_in(); } // [gore fork]\n")

    t.before("src/pc/mods/mod.c",
             "    // make sure mod is unique\n"
             "    for (int i = 0; i < mods->entryCount; i++) {\n",
             "    // [gore fork] a built-in mod is only ever loaded from the copy that came with the game\n"
             "    if (mods_fork_is_foreign_copy(fullPath, modName)) {\n"
             "        LOG_INFO(\"Skipping '%s': this mod is built in\", fullPath);\n"
             "        return true;\n"
             "    }\n"
             "\n")


def built_in_mods_hidden(t):
    """No list of mods shows what is compiled into the program, and its settings have their own button."""
    hidden = "mods_fork_is_hidden"

    t.after("src/pc/djui/djui_panel_host_mods.c",
            "    for (int i = 0; i < gLocalMods.entryCount; i++) {\n"
            "        struct Mod* mod = gLocalMods.entries[i];\n",
            "        if (%s(mod)) { continue; } // [gore fork] part of the game, nothing to choose\n" % hidden)

    f = "src/pc/djui/djui_panel_modlist.c"
    t.replace(f,
              "    if (gActiveMods.entryCount == 0) { return; }\n"
              "\n"
              "    f32 bodyHeight = (gActiveMods.entryCount * 32) + (gActiveMods.entryCount - 1) * 4;\n",
              "    // [gore fork] without what is part of the game\n"
              "    int forkShown = 0;\n"
              "    for (int i = 0; i < gActiveMods.entryCount; i++) {\n"
              "        if (!%s(gActiveMods.entries[i])) { forkShown++; }\n"
              "    }\n"
              "    if (forkShown == 0) { return; }\n"
              "\n"
              "    f32 bodyHeight = (forkShown * 32) + (forkShown - 1) * 4;\n" % hidden)
    t.replace(f,
              "    for (int i = 0; i < gActiveMods.entryCount; i++) {\n"
              "        struct Mod* mod = gActiveMods.entries[i];\n"
              "\n",
              "    int forkRow = 0;\n"
              "    for (int i = 0; i < gActiveMods.entryCount; i++) {\n"
              "        struct Mod* mod = gActiveMods.entries[i];\n"
              "        if (%s(mod)) { continue; } // [gore fork]\n"
              "\n" % hidden)
    t.replace(f, "        int v = (i % 2) ? 16 : 32;\n", "        int v = (forkRow++ % 2) ? 16 : 32; // [gore fork] was: i\n")

    for f, line in (("src/pc/network/coopnet/coopnet.c",
                     "        struct Mod* mod = gActiveMods.entries[i];\n"
                     "        strings[i] = mod->name;\n"),
                    ("src/pc/discord/discord_activity.c",
                     "        strings[i] = gActiveMods.entries[i]->name;\n")):
        t.replace(f,
                  "    char* strings[gActiveMods.entryCount];\n"
                  "    for (int i = 0; i < gActiveMods.entryCount; i++) {\n" + line +
                  "    }\n",
                  "    char* strings[gActiveMods.entryCount];\n"
                  "    int forkShown = 0; // [gore fork] without what is part of the game\n"
                  "    for (int i = 0; i < gActiveMods.entryCount; i++) {\n"
                  "        if (%s(gActiveMods.entries[i])) { continue; }\n"
                  "        strings[forkShown++] = gActiveMods.entries[i]->name;\n"
                  "    }\n"
                  "    if (forkShown <= 0) { return; }\n" % hidden)
        t.replace(f, "str_seperator_concat(buffer, bufferLength, strings, gActiveMods.entryCount, ",
                  "str_seperator_concat(buffer, bufferLength, strings, forkShown, ")

    f = "src/pc/djui/djui_panel_mod_menu.c"
    t.replace(f,
              "            struct LuaHookedModMenuElement* hooked = &gHookedModMenuElements[i];\n"
              "            bool shouldContinue = false;\n",
              "            struct LuaHookedModMenuElement* hooked = &gHookedModMenuElements[i];\n"
              "            bool shouldContinue = %s(hooked->mod); // [gore fork] was: false\n" % hidden)
    t.replace(f,
              "    char *modNameUppercase = to_uppercase(mod->name);\n",
              "    char *modNameUppercase = to_uppercase(%s(mod) ? FORK_SETTINGS_LABEL : mod->name); // [gore fork]\n"
              % hidden)

    f = "src/pc/djui/djui_panel_pause.c"
    t.after(f, '#include "djui_panel_mod_menu.h"\n', '#include "pc/mods/mods.h" // [gore fork]\n')
    t.replace(f,
              "        int modCount = 0;\n"
              "        for (int i = 0; i < gHookedModMenuElementsCount; i++) {\n"
              "            struct LuaHookedModMenuElement* hooked = &gHookedModMenuElements[i];\n"
              "            bool shouldContinue = false;\n",
              "        int modCount = 0;\n"
              "        // [gore fork] the mod that is the game is not one of the mods here\n"
              "        struct Mod* forkOwnMod = NULL;\n"
              "        int forkFirst = 0;  // the first setting that a mod added\n"
              "        int forkShown = 0;  // how many settings mods added\n"
              "        for (int i = 0; i < gHookedModMenuElementsCount; i++) {\n"
              "            struct LuaHookedModMenuElement* hooked = &gHookedModMenuElements[i];\n"
              "            if (%s(hooked->mod)) {\n"
              "                forkOwnMod = hooked->mod;\n"
              "                continue;\n"
              "            }\n"
              "            if (forkShown++ == 0) { forkFirst = i; }\n"
              "            bool shouldContinue = false;\n" % hidden)
    t.replace(f,
              "        if (modCount == 1) {\n"
              "            struct LuaHookedModMenuElement* hooked = &gHookedModMenuElements[0];\n"
              "            char buffer[256] = { 0 };\n"
              "            if (gHookedModMenuElementsCount == 1 && gHookedModMenuElements[0].element == MOD_MENU_ELEMENT_BUTTON) {\n"
              "                snprintf(buffer, 256, \"%s - %s\", hooked->mod->name, hooked->name);\n"
              "                struct DjuiButton* button = djui_button_create(body, buffer, DJUI_BUTTON_STYLE_NORMAL, djui_panel_mod_menu_mod_button);\n"
              "                button->base.tag = 0;\n",
              "        // [gore fork] The game's own settings have their own button. When mods have settings too,\n"
              "        // \"Mod Menu\" is next to it, in the same row (the VR builds have a full pause menu as it is).\n"
              "        if (forkOwnMod != NULL && modCount > 0) {\n"
              "            struct DjuiRect* forkRect = djui_rect_container_create(body, 64);\n"
              "            struct DjuiButton* button = djui_button_left_create(&forkRect->base, FORK_SETTINGS_LABEL, DJUI_BUTTON_STYLE_NORMAL, djui_panel_mod_menu_mod_create);\n"
              "            button->base.tag = forkOwnMod->index;\n"
              "            djui_button_right_create(&forkRect->base, DLANG(PAUSE, MOD_MENU), DJUI_BUTTON_STYLE_NORMAL, djui_panel_mod_menu_create);\n"
              "        } else if (forkOwnMod != NULL) {\n"
              "            struct DjuiButton* button = djui_button_create(body, FORK_SETTINGS_LABEL, DJUI_BUTTON_STYLE_NORMAL, djui_panel_mod_menu_mod_create);\n"
              "            button->base.tag = forkOwnMod->index;\n"
              "        } else if (modCount == 1) {\n"
              "            struct LuaHookedModMenuElement* hooked = &gHookedModMenuElements[forkFirst]; // [gore fork] was: 0\n"
              "            char buffer[256] = { 0 };\n"
              "            if (forkShown == 1 && hooked->element == MOD_MENU_ELEMENT_BUTTON) { // [gore fork] was: of all settings\n"
              "                snprintf(buffer, 256, \"%s - %s\", hooked->mod->name, hooked->name);\n"
              "                struct DjuiButton* button = djui_button_create(body, buffer, DJUI_BUTTON_STYLE_NORMAL, djui_panel_mod_menu_mod_button);\n"
              "                button->base.tag = forkFirst;\n")
    t.replace(f,
              "        } else if (gHookedModMenuElementsCount > 0) {\n"
              "            djui_button_create(body, DLANG(PAUSE, MOD_MENU), DJUI_BUTTON_STYLE_NORMAL, djui_panel_mod_menu_create);\n",
              "        } else if (modCount > 1) { // [gore fork] was: any setting at all\n"
              "            djui_button_create(body, DLANG(PAUSE, MOD_MENU), DJUI_BUTTON_STYLE_NORMAL, djui_panel_mod_menu_create);\n")


def mod_files(source, game=None, own=True):
    """The files of the mod in `source`, relative, sorted. `game` is the game's source being changed: a build
    puts it inside this repository (the workflow does: "game"), and it is not part of the mod. `own`: the mod
    is this repository, which has more in it than the mod (NOT_THE_MOD)."""
    game = os.path.realpath(game) if game else None

    def is_game(path):
        return game is not None and os.path.realpath(path) == game

    files = []
    for top in sorted(os.listdir(source)):
        if top.startswith(".") or (own and top in NOT_THE_MOD):
            continue
        full = os.path.join(source, top)
        if is_game(full):
            continue
        if os.path.isdir(full):
            for folder, dirs, names in os.walk(full):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not is_game(os.path.join(folder, d)))
                for name in sorted(names):
                    if not name.startswith("."):
                        files.append(os.path.relpath(os.path.join(folder, name), source))
        else:
            files.append(top)
    return files


def build_stamp():
    """The first line of "built-in.txt": which state of this repository the built-in mods were taken from."""
    def git(*args):
        try:
            return subprocess.run(["git", "-C", REPO] + list(args), check=True, capture_output=True,
                                  text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    commit = os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD") or "unknown"
    if not os.environ.get("GITHUB_SHA") and git("status", "--porcelain"):
        commit += "+changes"
    return "%s %s" % (VERSION_SUFFIX.lstrip("-"), commit)


MOD_SOURCES = {"Gore-Hardmode": REPO}
MODS_STATE = ""


def mod_header(folder):
    """The fields at the top of a mod's main.lua ("-- name: ..."), the way the game reads them."""
    fields = {}
    with open(os.path.join(folder, "main.lua"), "rb") as f:
        lines = f.read(65536).decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    for line in lines:
        if not line.startswith("--"):
            break
        key, colon, value = line[2:].partition(":")
        if colon and key.strip() and key.strip() not in fields:
            fields[key.strip().lower()] = value.strip()
    return fields


def check_mod_name(name, where):
    """A folder name that works in the game's mods folder on Windows, Linux and inside an Android app."""
    bad = [c for c in name if c in '"\\/:*?<>|%\'' or not 32 <= ord(c) <= 126]
    if (not name or bad or name[0] in "._ " or name[-1] in "~. " or len(name) > 60
            or name.lower().endswith(".lua")):
        raise Problem("%s: %r can't be the name of a mod's folder (use letters, digits, spaces, - _ ( ) [ ])"
                      % (where, name))


def unpack_mod(path, into):
    """Unpacks one zip of MODS_REPO. Answers (the mod's name, the folder its main.lua is in)."""
    where = os.path.basename(path)
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            for n in names:
                parts = n.replace("\\", "/").split("/")
                if n.startswith(("/", "\\")) or ".." in parts or ":" in parts[0]:
                    raise Problem("%s: a file in it would be unpacked outside of its folder (%s)" % (where, n))
            mains = sorted((n for n in names if n.replace("\\", "/").split("/")[-1] == "main.lua"),
                           key=lambda n: (n.count("/"), n))
            if not mains:
                raise Problem("%s: no main.lua in it. A mod that is one .lua file goes into a folder, "
                              "named main.lua" % where)
            z.extractall(into)
    except zipfile.BadZipFile:
        raise Problem("%s is not a zip file" % where)
    inner = mains[0].replace("\\", "/").split("/")[:-1]
    name = inner[-1] if inner else where[:-len(".zip")]
    return name.strip(), os.path.join(into, *inner)


def gather_mods(work):
    """Fetches MODS_REPO and decides what each mod in it is: always on, or the host's choice. Fills in
    BUILT_IN_MODS, CHOICE_MODS, MOD_SOURCES and MODS_STATE. `work` is a folder for the files in between."""
    global MODS_STATE
    found = {}

    def add(name, folder, where):
        check_mod_name(name, where)
        if name.lower() in (n.lower() for n in list(found) + ["Gore-Hardmode"]):
            raise Problem("%s: there is a mod called %r already" % (where, name))
        found[name] = folder

    local = os.path.join(HERE, "mods")
    if os.path.isdir(local):
        for name in sorted(os.listdir(local)):
            if os.path.isfile(os.path.join(local, name, "main.lua")):
                add(name, os.path.join(local, name), "fork/mods")

    if MODS_REPO:
        checkout = os.environ.get("MODS_DIR")
        if checkout:
            if not os.path.isdir(checkout):
                raise Problem("MODS_DIR: %s is not a folder" % checkout)
        else:
            checkout = os.path.join(work, "repository")
            print("fetching %s at %s" % (MODS_REPO, MODS_REF), flush=True)
            os.makedirs(checkout)
            try:
                for args in (["init", "-q"], ["config", "core.autocrlf", "false"],
                             ["remote", "add", "origin", MODS_REPO],
                             ["fetch", "-q", "--depth", "1", "origin", MODS_REF],
                             ["checkout", "-q", "FETCH_HEAD"]):
                    subprocess.run(["git", "-C", checkout] + args, check=True)
            except (OSError, subprocess.CalledProcessError):
                raise Problem("could not fetch %s at %s (the mods that are built in)" % (MODS_REPO, MODS_REF))
        try:
            commit = subprocess.run(["git", "-C", checkout, "rev-parse", "HEAD"], check=True, capture_output=True,
                                    text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            commit = "unknown"
        MODS_STATE = "%s %s" % (MODS_REPO, commit)
        number = 0
        for entry in sorted(os.listdir(checkout)):
            full = os.path.join(checkout, entry)
            if entry.startswith("."):
                continue
            if os.path.isdir(full):
                if os.path.isfile(os.path.join(full, "main.lua")):
                    add(entry, full, MODS_REPO)
            elif entry.lower().endswith(".zip"):
                number += 1
                name, folder = unpack_mod(full, os.path.join(work, "unpacked", str(number)))
                add(name, folder, entry)

    tags = {"Gore-Hardmode": set(mod_header(REPO).get("incompatible", "").split())}
    for name, folder in found.items():
        tags[name] = set(mod_header(folder).get("incompatible", "").split())
    for name in sorted(found, key=str.lower):
        clash = sorted(other for other in tags if other != name and tags[name] & tags[other])
        if "Gore-Hardmode" in clash:
            raise Problem("the mod %s says it can't run with this repository's mod (\"-- incompatible: %s\"): "
                          "it could never be switched on" % (name, " ".join(sorted(tags[name]))))
        MOD_SOURCES[name] = found[name]
        (CHOICE_MODS if clash else BUILT_IN_MODS).append(name)


def built_in_mods_files(t, stamp):
    """Puts the mods into the game's source: into its mods folder, or (EMBEDDED_MODS) into the block of bytes
    that is compiled into the program. Returns the size of that block and how many files are in it."""
    block = [EMBEDDED_HEADING.encode("ascii")]
    block_files = 0

    def into_block(path, data):
        name = path.encode("utf-8")
        if not 0 < len(name) <= 512 or len(data) >= 1 << 31:
            raise Problem("%s can't be compiled into the program (its name or its size)" % path)
        block.append(len(name).to_bytes(2, "little") + name + len(data).to_bytes(4, "little"))
        block.append(data)

    for name in EMBEDDED_MODS:
        if name not in BUILT_IN_MODS:
            raise Problem("EMBEDDED_MODS: %s is not one of the mods that are always on" % name)

    for name in BUILT_IN_MODS + CHOICE_MODS:
        source = MOD_SOURCES[name]
        own = source == REPO
        embedded = name in EMBEDDED_MODS
        if not os.path.isfile(os.path.join(source, "main.lua")):
            raise Problem("built-in mod %s: no main.lua in %s" % (name, source))
        target = t.path("mods/" + name)
        if os.path.exists(target) or os.path.exists(target + ".lua"):
            raise Problem("mods/%s is already in the game" % name)
        files = mod_files(source, t.root, own)
        size = 0
        for rel in files:
            for part in rel.replace("\\", "/").split("/"):
                if part.startswith("_") or part.endswith("~"):
                    raise Problem("built-in mod %s: %s would be missing from the Android apps" % (name, rel))
            with open(os.path.join(source, rel), "rb") as f:
                data = f.read()
            if rel.lower().endswith(".lua"):
                data = data.replace(b"\r\n", b"\n")
            size += len(data)
            if embedded:
                into_block(name + "/" + rel.replace("\\", "/"), data)
                continue
            out = os.path.join(target, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f:
                f.write(data)
        if size >= 35 * 1048576:
            raise Problem("built-in mod %s is %d bytes; the game refuses mods of 35 MB and more" % (name, size))
        first = stamp if own else "%s %s" % (stamp, MODS_STATE or "fork/mods")
        note = ("%s\n%d\n" % (first, len(files) + 1)).encode("utf-8")
        if embedded:
            into_block(name + "/built-in.txt", note)
            block_files += len(files) + 1
            t.log.append("%s (%d files, %.1f MB): compiled into the program" % (name, len(files), size / 1048576))
            continue
        with open(os.path.join(target, "built-in.txt"), "wb") as f:
            f.write(note)
        t.log.append("mods/%s (%d files, %.1f MB): %s"
                     % (name, len(files), size / 1048576,
                        "the host's choice" if name in CHOICE_MODS else "always on"))
    with open(t.path(SHIPPED_LIST), "wb") as f:
        f.write("".join(name + "\n" for name in shipped_mods()).encode("utf-8"))

    data = b"".join(block)
    relative = "src/pc/mods/fork_embedded.bin"
    absolute = t.path(relative).replace("\\", "/")
    if any(c in absolute for c in '"\n'):
        raise Problem("the game's source is in a folder with a quotation mark in its name: %s" % absolute)
    with open(t.path(relative), "wb") as f:
        f.write(data)
    t.write("src/pc/mods/fork_embedded.c", EMBEDDED_C_FILE % {"relative": relative, "absolute": absolute}, False)
    with open(t.path(EMBEDDED_COUNT), "wb") as f:
        f.write(("%d\n" % block_files).encode("ascii"))
    t.log.append("src/pc/mods/fork_embedded.bin (%.1f MB, %s)"
                 % (len(data) / 1048576, hashlib.sha1(data).hexdigest()[:12]))
    return {"size": len(data), "count": block_files}



WINDOW_NAMES = {
    "pc": "Super Mario 64 Coop Deluxe",
    "vr": "SM64 Co-Op DX VR",
    "android": "Super Mario 64 Coop Deluxe",
}


def check_names():
    for c in GAME_TITLE:
        if c in "\"'\\<>&%$" or not 32 <= ord(c) <= 126:
            raise Problem("GAME_TITLE: the character %r can't be used" % c)
    if GAME_TITLE[:1] in ("@", "?") or "??" in GAME_TITLE:
        raise Problem("GAME_TITLE can't start with '@' or '?' or have '??' in it")
    if not GAME_TITLE.strip() or len(GAME_TITLE) > 60:
        raise Problem("GAME_TITLE has to be 1 to 60 characters")
    name = COOPNET_GAME
    if not 1 <= len(name) <= 32 or any(not (c.isalnum() or c in "-_.") or ord(c) > 126 for c in name):
        raise Problem("%r: a CoopNet name is 1 to 32 letters, digits, '-', '_' or '.'" % name)
    if COOPNET_GAME in ("sm64coopdx", "sm64coopdx-dev", "sm64coopdx-intl", "sm64coop-android", "sm64coopdx-vr-p1"):
        raise Problem("COOPNET_GAME is the name of another game")
    if not 50 <= PUNCH_COLLIDER_LENGTH <= 300 or PUNCH_COLLIDER_LENGTH == 275:
        raise Problem("PUNCH_COLLIDER_LENGTH: 50 to 300 (the game's slider), and not the 275 it replaces")
    if not 10 <= PUNCH_BODY_RADIUS <= 64:
        raise Problem("PUNCH_BODY_RADIUS: 10 to 64")
    if not SETTINGS_LABEL.strip() or len(SETTINGS_LABEL) > 24 or any(
            c in "\"\\%" or not 32 <= ord(c) <= 126 for c in SETTINGS_LABEL):
        raise Problem("SETTINGS_LABEL has to be 1 to 24 plain characters, without quotes, '\\' or '%'")
    for name in EMBEDDED_MODS:
        if name not in BUILT_IN_MODS:
            raise Problem("%s is compiled into the program but not always on: put it in BUILT_IN_MODS" % name)


def game_title(t, base):
    t.replace("src/pc/network/version.h",
              '#define WINDOW_NAME "%s"\n' % WINDOW_NAMES[base],
              '#define WINDOW_NAME "%s" // [gore fork]\n' % GAME_TITLE)
    t.replace("src/pc/lua/smlua_constants_autogen.c",
              '"WINDOW_NAME=\'Super Mario 64 Coop Deluxe\'\\n"',
              '"WINDOW_NAME=\'%s\'\\n"' % GAME_TITLE)
    if base == "pc":
        mac_app(t)


def mac_app(t):
    """The macOS app (the Makefile writes its Info.plist): its name, an identifier, and the sentence macOS
    shows when the game first asks for the microphone. Without that sentence macOS ends a program the moment
    it opens a microphone, which the voice chat does."""
    f = "Makefile"
    line = "\t\techo '    %s' >> $(APP_CONTENTS_DIR)/Info.plist; \\\n"
    t.replace(f,
              line % "<key>CFBundleDisplayName</key>" + line % "<string>sm64coopdx</string>",
              line % "<key>CFBundleDisplayName</key>" + line % ("<string>%s</string>" % GAME_TITLE)
              + line % "<key>CFBundleName</key>" + line % "<string>Realism64</string>"
              + line % "<key>CFBundleIdentifier</key>" + line % ("<string>%s</string>" % MAC_BUNDLE_ID)
              + line % "<key>CFBundleShortVersionString</key>"
              + line % ("<string>1.5.1%s</string>" % VERSION_SUFFIX)
              + line % "<key>NSMicrophoneUsageDescription</key>"
              + line % "<string>Voice chat: the other players hear you while the microphone is on in Options, Sound.</string>")


def version_and_lobbies(t, base):
    t.after("src/pc/network/version.h",
            '#define SM64COOPDX_VERSION "v1.5.1"\n',
            "\n"
            "// [gore fork] This is not the official game. The suffix is part of the version players compare when\n"
            "// they join each other; the names are the CoopNet lobby lists this build uses instead of the\n"
            "// official ones. (SM64COOPDX_VERSION itself stays: mods look at it.)\n"
            '#define FORK_VERSION_SUFFIX "%s"\n'
            '#define FORK_COOPNET_GAME "%s"\n' % (VERSION_SUFFIX, COOPNET_GAME))

    f = "src/pc/network/version.c"
    t.replace(f, '        "%s", SM64COOPDX_VERSION\n',
              '        "%s" FORK_VERSION_SUFFIX, SM64COOPDX_VERSION\n')
    t.replace(f, '        "%s %s", SM64COOPDX_VERSION, VERSION_REGION\n',
              '        "%s" FORK_VERSION_SUFFIX " %s", SM64COOPDX_VERSION, VERSION_REGION\n')
    t.replace(f, '        "%s, %s", SM64COOPDX_VERSION, COMPILE_TIME\n',
              '        "%s" FORK_VERSION_SUFFIX ", %s", SM64COOPDX_VERSION, COMPILE_TIME\n')
    t.replace(f, '        "%s %s, %s", SM64COOPDX_VERSION, VERSION_REGION, COMPILE_TIME\n',
              '        "%s" FORK_VERSION_SUFFIX " %s, %s", SM64COOPDX_VERSION, VERSION_REGION, COMPILE_TIME\n')

    f = "src/pc/network/coopnet/coopnet.c"
    if base == "pc":
        t.replace(f, "coopnet_lobby_list_get(GAME_NAME, password)", "coopnet_lobby_list_get(FORK_COOPNET_GAME, password)")
        t.replace(f, "coopnet_lobby_update(sLocalLobbyId, GAME_NAME, ", "coopnet_lobby_update(sLocalLobbyId, FORK_COOPNET_GAME, ")
        t.replace(f, "coopnet_lobby_create(GAME_NAME, ", "coopnet_lobby_create(FORK_COOPNET_GAME, ")
    elif base == "android":
        t.replace(f, '(password[0] != \'\\0\') ? "sm64coopdx" : GAME_NAME;', "FORK_COOPNET_GAME;")
        t.replace(f, '(gCoopNetPassword[0] != \'\\0\') ? "sm64coopdx" : GAME_NAME;', "FORK_COOPNET_GAME;")
        t.replace(f, "coopnet_lobby_list_get(GAME_NAME, password)", "coopnet_lobby_list_get(FORK_COOPNET_GAME, password)")
        t.replace(f, "coopnet_lobby_update(sLocalLobbyId, GAME_NAME, ", "coopnet_lobby_update(sLocalLobbyId, FORK_COOPNET_GAME, ")
        t.replace(f, "coopnet_lobby_create(GAME_NAME, ", "coopnet_lobby_create(FORK_COOPNET_GAME, ")
    else:
        t.replace(f, '#define VR_COOPNET_GAME_NAME "sm64coopdx-vr-p1"\n',
                  "#define VR_COOPNET_GAME_NAME FORK_COOPNET_GAME // [gore fork]\n")
        t.replace(f, '#define ANDROID_COOPNET_GAME_NAME "sm64coop-android"\n',
                  "#define ANDROID_COOPNET_GAME_NAME FORK_COOPNET_GAME // [gore fork]\n")
        t.replace(f, "#endif\n    return GAME_NAME;\n}\n", "#endif\n    return FORK_COOPNET_GAME; // [gore fork]\n}\n")
        text, _ = t.read(f)
        if "GAME_NAME, " in text.replace("VR_COOPNET_GAME_NAME", "").replace("ANDROID_COOPNET_GAME_NAME", ""):
            raise Problem(f + ": a lobby call still uses GAME_NAME")



def no_update_checks(t, base):
    t.replace("src/pc/pc_main.c",
              "    if (gCLIOpts.network != NT_SERVER && !gCLIOpts.skipUpdateCheck) {\n"
              "        check_for_updates();\n"
              "    }\n",
              "    // [gore fork] No update check: it would offer the original game in place of this build.\n"
              "    if (false && gCLIOpts.network != NT_SERVER && !gCLIOpts.skipUpdateCheck) {\n"
              "        check_for_updates();\n"
              "    }\n")

    if base == "vr":
        f = "platform/android/app/src/main/cpp/quest_android_shims.c"
        t.after(f,
                "static void quest_refresh_update_status(void) {\n",
                "    // [gore fork] No updates from the original's releases.\n"
                "    sVrUpdateStatus = VR_UPDATE_UP_TO_DATE;\n"
                "    gUpdateMessage = false;\n"
                "    if (true) { return; }\n")
        f = "platform/android/app/src/main/java/com/fulldivegames/sm64coopdxvr/QuestNativeActivity.java"
        t.after(f, "    public void downloadLatestStandaloneUpdateFromNative() {\n",
                "        if (FORK_NO_UPDATES) return; // [gore fork]\n")
        t.after(f, "    private void checkForStandaloneUpdate() {\n",
                "        if (FORK_NO_UPDATES) return; // [gore fork]\n")



JAVA_BUILT_IN = """\
    // ------------------------------------------------------------------------------------------------
    // [gore fork] The mods that came with this build (always on, or the host's choice).
    // The app only copies what isn't there yet, so a new version of the app would keep running the old
    // version of a built-in mod. Each built-in mod has a "built-in.txt" that says which build it is from
    // and how many files it has: when the installed one says something else than the one in the app, or
    // files are missing (a copy that was cut short), the folder is replaced.
    // A folder of the same name that isn't ours (no built-in.txt) is kept under another name.
    // ------------------------------------------------------------------------------------------------
    private static final boolean FORK_NO_UPDATES = true;
    private static final String[] FORK_BUILT_IN_MODS = { %(names)s };
    // (compiled into the program now; an earlier version of the app installed them as folders here)
    private static final String[] FORK_EMBEDDED_MODS = { %(embedded)s };

    private void forkInstallBuiltInMods(java.io.File modsDirectory) {
        for (String name : FORK_EMBEDDED_MODS) {
            java.io.File old = new java.io.File(modsDirectory, name);
            if (!new java.io.File(old, "built-in.txt").isFile()) continue;
            try {
                forkDeleteTree(old);
                android.util.Log.i("GoreFork", "Removed the installed copy of " + name + ": it is in the program now");
            } catch (java.io.IOException exception) {
                android.util.Log.e("GoreFork", "Could not remove the old copy of " + name, exception);
            }
        }
        for (String name : FORK_BUILT_IN_MODS) {
            try {
                String asset = "mods/" + name;
                String bundled = forkReadText(getAssets().open(asset + "/built-in.txt"));
                java.io.File installed = new java.io.File(modsDirectory, name);
                java.io.File stamp = new java.io.File(installed, "built-in.txt");
                if (stamp.isFile()) {
                    if (bundled.equals(forkReadText(new java.io.FileInputStream(stamp)))
                            && forkCountFiles(installed) >= forkFilesIn(bundled)) continue;
                    forkDeleteTree(installed);
                } else if (installed.exists()) {
                    java.io.File aside = new java.io.File(modsDirectory, name + " (own copy)");
                    for (int i = 2; aside.exists(); i++) {
                        aside = new java.io.File(modsDirectory, name + " (own copy " + i + ")");
                    }
                    if (!installed.renameTo(aside)) {
                        throw new java.io.IOException("Could not move " + installed);
                    }
                }
                // (the stamp goes last: a copy that was cut short is done again next time)
                forkCopyAssetTree(asset, installed, "built-in.txt");
                forkCopyAssetTree(asset + "/built-in.txt", stamp, null);
                android.util.Log.i("GoreFork", "Installed built-in mod " + name);
            } catch (java.io.IOException exception) {
                android.util.Log.e("GoreFork", "Could not install built-in mod " + name, exception);
            }
        }
    }

    private static String forkReadText(java.io.InputStream input) throws java.io.IOException {
        try {
            java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int count;
            while ((count = input.read(buffer)) != -1) bytes.write(buffer, 0, count);
            return bytes.toString("UTF-8").trim();
        } finally {
            input.close();
        }
    }

    // (the last line of built-in.txt)
    private static int forkFilesIn(String stampText) {
        try {
            return Integer.parseInt(stampText.substring(stampText.lastIndexOf('\\n') + 1).trim());
        } catch (NumberFormatException exception) {
            return 0;
        }
    }

    private static int forkCountFiles(java.io.File file) {
        java.io.File[] children = file.listFiles();
        if (children == null) return file.isFile() ? 1 : 0;
        int count = 0;
        for (java.io.File child : children) count += forkCountFiles(child);
        return count;
    }

    private static void forkDeleteTree(java.io.File file) throws java.io.IOException {
        java.io.File[] children = file.listFiles();
        if (children != null) {
            for (java.io.File child : children) forkDeleteTree(child);
        }
        if (file.exists() && !file.delete()) {
            throw new java.io.IOException("Could not remove " + file);
        }
    }

    private void forkCopyAssetTree(String assetPath, java.io.File destination, String skipAtTop)
            throws java.io.IOException {
        String[] children = getAssets().list(assetPath);
        if (children == null || children.length == 0) {
            java.io.File parent = destination.getParentFile();
            if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
                throw new java.io.IOException("Could not create " + parent);
            }
            java.io.InputStream input = getAssets().open(assetPath);
            try {
                java.io.FileOutputStream output = new java.io.FileOutputStream(destination);
                try {
                    byte[] buffer = new byte[16 * 1024];
                    int count;
                    while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                } finally {
                    output.close();
                }
            } finally {
                input.close();
            }
            return;
        }
        if (!destination.isDirectory() && !destination.mkdirs()) {
            throw new java.io.IOException("Could not create " + destination);
        }
        for (String child : children) {
            if (child.equals(skipAtTop)) continue;
            forkCopyAssetTree(assetPath + "/" + child, new java.io.File(destination, child), null);
        }
    }

"""

GRADLE_SIGNING = """\
    // [gore fork] Every build is signed with the same key, so that a new build installs over the last one.
    signingConfigs {
        fork {
            storeFile file("gore-fork.p12")
            storeType "pkcs12"
            storePassword "gorefork"
            keyAlias "gorefork"
            keyPassword "gorefork"
        }
    }

"""


def keystore_to(t, module):
    source = os.path.join(HERE, *KEYSTORE.split("/"))
    if not os.path.isfile(source):
        raise Problem("missing " + source)
    shutil.copyfile(source, t.path(module + "/gore-fork.p12"))


def android_app_vr(t):
    java = {"names": c_string_list(shipped_mods()), "embedded": c_string_list(EMBEDDED_MODS)}

    f = "platform/android/app/build.gradle"
    t.replace(f, '        applicationId "com.fulldivegames.sm64coopdxvr"\n',
              '        applicationId "com.fulldivegames.sm64coopdxvr%s" // [gore fork]\n' % APP_ID_SUFFIX)
    t.replace(f,
              "    buildTypes {\n"
              "        debug {\n"
              "            debuggable true\n",
              GRADLE_SIGNING +
              "    buildTypes {\n"
              "        debug {\n"
              "            debuggable true\n"
              "            signingConfig signingConfigs.fork\n")
    keystore_to(t, "platform/android/app")

    t.replace("platform/android/app/src/main/AndroidManifest.xml",
              'android:label="SM64 Co-Op DX VR Standalone"',
              'android:label="%s"' % GAME_TITLE)

    f = "platform/android/app/src/main/cpp/quest_android_shims.c"
    t.replace(f, '"/sdcard/Android/data/com.fulldivegames.sm64coopdxvr/files";',
              '"/sdcard/Android/data/com.fulldivegames.sm64coopdxvr%s/files";' % APP_ID_SUFFIX)
    t.replace(f, '"/sdcard/Android/data/com.fulldivegames.sm64coopdxvr/files/baserom.us.z64";',
              '"/sdcard/Android/data/com.fulldivegames.sm64coopdxvr%s/files/baserom.us.z64";' % APP_ID_SUFFIX)

    f = "platform/android/app/src/main/java/com/fulldivegames/sm64coopdxvr/QuestNativeActivity.java"
    t.before(f, "    private void installBundledResources() {\n", JAVA_BUILT_IN % java)
    t.before(f, '            copyMissingAssetDirectory("mods", new File(root, "mods"));\n',
             '            forkInstallBuiltInMods(new File(root, "mods")); // [gore fork]\n')


def android_app_port(t):
    java = {"names": c_string_list(shipped_mods()), "embedded": c_string_list(EMBEDDED_MODS)}

    f = "platform/app/build.gradle"
    t.replace(f, '            applicationId "com.maniscat2.sm64coopdx"\n',
              '            applicationId "com.maniscat2.sm64coopdx%s" // [gore fork]\n' % APP_ID_SUFFIX)
    t.replace(f,
              "    buildTypes {\n"
              "        release {\n"
              "            minifyEnabled false\n",
              GRADLE_SIGNING +
              "    buildTypes {\n"
              "        release {\n"
              "            signingConfig signingConfigs.fork\n"
              "            minifyEnabled false\n")
    keystore_to(t, "platform/app")

    t.replace("platform/app/src/main/res/values/strings.xml",
              '<string name="app_name">Super Mario 64 Coop Deluxe</string>',
              '<string name="app_name">%s</string>' % GAME_TITLE)

    t.replace("src/pc/platform.h",
              '#define ANDROID_APPNAME "com.maniscat2.sm64coopdx"\n',
              '#define ANDROID_APPNAME "com.maniscat2.sm64coopdx%s" // [gore fork]\n' % APP_ID_SUFFIX)

    f = "platform/app/src/main/java/org/libsdl/app/SDLActivity.java"
    t.before(f, "    public static void copyAssetFilesToDir(String destpath) {\n", JAVA_BUILT_IN % java)
    t.after(f,
            '        activity.copyFileOrDir("", destpath); // copy all files in assets folder in my project\n',
            '        activity.forkInstallBuiltInMods(new java.io.File(destpath, "mods")); // [gore fork]\n')



ICONS = os.path.join(HERE, "icon")
ANDROID_DENSITIES = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]

WINDOW_ICON_C = """
// [gore fork] The window's icon. Windows takes it from the program and macOS from the app; anywhere else a
// window has the icon it is given here.
#if !defined(_WIN32) && !defined(__APPLE__) && !defined(__ANDROID__)
#include "fork_window_icon.h"

static void fork_window_icon(SDL_Window *window) {
    SDL_Surface *icon = SDL_CreateRGBSurfaceWithFormatFrom((void *) sForkWindowIcon, FORK_WINDOW_ICON_SIZE,
        FORK_WINDOW_ICON_SIZE, 32, FORK_WINDOW_ICON_SIZE * 4, SDL_PIXELFORMAT_RGBA32);
    if (icon == NULL) { return; }
    SDL_SetWindowIcon(window, icon);
    SDL_FreeSurface(icon);
}
#else
static void fork_window_icon(SDL_Window *window) { (void) window; }
#endif

"""


def icon_file(t, name, rel, must_exist=True):
    source = os.path.join(ICONS, *name.split("/"))
    if not os.path.isfile(source):
        raise Problem("missing %s (python3 fork/icon/make.py makes it)" % source)
    if must_exist and not t.exists(rel):
        raise Problem("%s: the game has no such file to put the icon over" % rel)
    os.makedirs(os.path.dirname(t.path(rel)), exist_ok=True)
    shutil.copyfile(source, t.path(rel))


def icons(t, base):
    icon_file(t, "icon.ico", "res/icon.ico")
    icon_file(t, "icon.icns", "res/icon.icns")
    icon_file(t, "icon.png", "res/icon.icon/Assets/icon.png")
    t.replace("res/icon.icon/icon.json", '"scale" : 3.5,', '"scale" : 4,')

    with open(os.path.join(ICONS, "window-64.rgba"), "rb") as f:
        pixels = f.read()
    if len(pixels) != 64 * 64 * 4:
        raise Problem("fork/icon/window-64.rgba is not 64 x 64 pixels")
    lines = ["// [gore fork] made by fork/apply.py from fork/icon/window-64.rgba: red, green, blue, alpha\n",
             "#define FORK_WINDOW_ICON_SIZE 64\n",
             "static const unsigned char sForkWindowIcon[FORK_WINDOW_ICON_SIZE * FORK_WINDOW_ICON_SIZE * 4] = {\n"]
    for at in range(0, len(pixels), 32):
        lines.append("    " + ",".join(str(b) for b in pixels[at:at + 32]) + ",\n")
    lines.append("};\n")
    t.write("src/pc/gfx/fork_window_icon.h", "".join(lines), False)
    f = "src/pc/gfx/gfx_sdl.c"
    t.before(f, "static void gfx_sdl_init(const char *window_title) {\n", WINDOW_ICON_C)
    t.replace(f,
              "        SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE\n"
              "    );\n",
              "        SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE\n"
              "    );\n"
              "    if (wnd != NULL) { fork_window_icon(wnd); } // [gore fork]\n")

    if base == "android":
        with open(os.path.join(ICONS, "background.txt")) as f:
            colour = f.read().strip()
        if not re.match(r"^#[0-9A-F]{6}$", colour):
            raise Problem("fork/icon/background.txt: not a colour")
        for res in ("platform/app/src/main/res", "platform/android/app/res"):
            for density in ANDROID_DENSITIES:
                for name in ("ic_launcher.png", "ic_launcher_round.png", "ic_launcher_foreground.png"):
                    rel = "%s/mipmap-%s/%s" % (res, density, name)
                    if res.startswith("platform/app/") or t.exists(rel):
                        icon_file(t, "android/mipmap-%s/%s" % (density, name), rel)
        icon_file(t, "android/ic_launcher-playstore.png", "platform/app/src/main/ic_launcher-playstore.png")
        t.replace("platform/app/src/main/res/values/ic_launcher_background.xml",
                  '<color name="ic_launcher_background">#824B00</color>',
                  '<color name="ic_launcher_background">%s</color>' % colour)

    if base == "vr":
        for density in ANDROID_DENSITIES:
            icon_file(t, "android/mipmap-%s/ic_launcher.png" % density,
                      "platform/android/app/src/main/res/mipmap-%s/ic_launcher.png" % density, must_exist=False)
        t.replace("platform/android/app/src/main/AndroidManifest.xml",
                  '        android:hasCode="true"\n',
                  '        android:hasCode="true"\n'
                  '        android:icon="@mipmap/ic_launcher"\n')
    t.log.append("the icon (fork/icon)")



VR_BRIDGE_H = """\
// [gore fork] What the built-in mod is told about this player's VR state, so that it can show it to the
// others. See vr_net_bridge_get_state at the end of vr_hand_interaction.c, and vrsync.lua in the mod.
#define VR_NET_MAX_EFFECTS 48

enum VrNetFlag {
    VR_NET_FLAG_FIRE_FLOWER = 1 << 0,
    VR_NET_FLAG_HAMMER_SUIT = 1 << 1,
    VR_NET_FLAG_SONIC_SHOES = 1 << 2,
    VR_NET_FLAG_BIG_HANDS   = 1 << 3,
    VR_NET_FLAG_PROPELLER   = 1 << 4,
    VR_NET_FLAG_POWER_STAR  = 1 << 5,
    // bits 8 and 9: which hat he holds in his hand (enum VrNetHat)
    VR_NET_FLAG_HAT_SHIFT   = 8,
};

enum VrNetHand {
    VR_NET_HAND_CLOSED = 1 << 0,
    VR_NET_HAND_HAT    = 1 << 1,
};

enum VrNetHat {
    VR_NET_HAT_NORMAL = 0,
    VR_NET_HAT_WING,
    VR_NET_HAT_METAL,
    VR_NET_HAT_VANISH,
};

// Things of his in the level: what he throws, the items waiting to be picked up, caps.
enum VrNetEffect {
    VR_NET_EFFECT_FIREBALL = 1,
    VR_NET_EFFECT_FIREBALL_CHARGE,
    VR_NET_EFFECT_HAMMER,
    VR_NET_EFFECT_HAMMER_CHARGE,
    VR_NET_EFFECT_RASENGAN,
    VR_NET_EFFECT_RASEN_SHURIKEN,
    VR_NET_EFFECT_ITEM_FIRE_FLOWER,
    VR_NET_EFFECT_ITEM_HAMMER_SUIT,
    VR_NET_EFFECT_ITEM_SONIC_SHOES,
    VR_NET_EFFECT_ITEM_BIG_HANDS,
    VR_NET_EFFECT_ITEM_PROPELLER,
    VR_NET_EFFECT_ITEM_POWER_STAR,
    VR_NET_EFFECT_CAP_WING,
    VR_NET_EFFECT_CAP_VANISH,
    VR_NET_EFFECT_CAP_METAL,
    VR_NET_EFFECT_CAP_NORMAL,
};

enum VrNetEvent {
    VR_NET_EVENT_LEVEL_SELECT = 1, // value: the level
};

struct VrNetState {
    u32 flags;
    f32 bigHandsScale;
    u8 handValid[2];
    u8 handHow[2]; // enum VrNetHand
    f32 hand[2][3];
    u32 effectCount;
    u8 effectKind[VR_NET_MAX_EFFECTS];
    f32 effectPos[VR_NET_MAX_EFFECTS][3];
};

bool vr_net_bridge_online(void);
bool vr_net_bridge_get_state(struct VrNetState* state);
void vr_net_bridge_push_hit(u8 victimGlobalIndex, s16 attackYaw, u8 attackType);
bool vr_net_bridge_pop_hit(u8* victimGlobalIndex, s16* attackYaw, u8* attackType);
void vr_net_bridge_push_event(u8 kind, s32 value);
bool vr_net_bridge_pop_event(u8* kind, s32* value);
void vr_net_bridge_track_cap(struct Object* cap, u8 kind);
// (in rendering_graph_node.c, which is where the hat in the hand lives)
u8 vr_net_bridge_held_hat(void);

// [gore fork] Where this player's eyes are in the level and where they look, and which way each of his
// hands is turned (at the end of rendering_graph_node.c).
bool fork_vr_head_world(Vec3f position, s16* yaw, s16* pitch, s16* roll, bool* firstPerson);
bool fork_vr_hand_world(u32 hand, Vec3f fingers, Vec3f thumb);

// [gore fork] Third person while this player is dead (at the end of rendering_graph_node.c).
void fork_vr_death_camera(bool dead);
void fork_vr_death_camera_tick(void);
unsigned int fork_vr_camera_mode_choice(void);

"""

VR_BRIDGE_REDIRECT = """\

// [gore fork] In this file "a VR lobby" means "online": every lobby of this game has players who understand
// a VR hit. The hit itself isn't sent as the VR fork's own packet (the flat builds don't know it) but queued
// for the built-in mod, which sends it as a mod packet. (Both lines come after the headers on purpose.)
#define ns_coopnet_vr_public_session() vr_net_bridge_online()
#define network_send_vr_player_hit(victim, yaw, type) vr_net_bridge_push_hit((victim), (yaw), (type))
"""

VR_BRIDGE_C = """\

// =========================================================================================================
// [gore fork] What the other players get to see
//
// Nothing above is sent to anybody: hands, power-ups and projectiles exist on this player's game only. The
// built-in mod asks here once per frame and passes the answer on (vrsync.lua). This sits at the end of the
// file because it reads the file's own state.
// =========================================================================================================
#define VR_NET_HIT_QUEUE 16

static struct {
    u8 victim;
    s16 yaw;
    u8 type;
} sVrNetHits[VR_NET_HIT_QUEUE];
static u32 sVrNetHitRead = 0;
static u32 sVrNetHitWrite = 0;

bool vr_net_bridge_online(void) {
    return gNetworkType != NT_NONE && gNetworkPlayerLocal != NULL;
}

void vr_net_bridge_push_hit(u8 victimGlobalIndex, s16 attackYaw, u8 attackType) {
    if (sVrNetHitWrite - sVrNetHitRead >= VR_NET_HIT_QUEUE) {
        return;
    }
    const u32 slot = sVrNetHitWrite % VR_NET_HIT_QUEUE;
    sVrNetHits[slot].victim = victimGlobalIndex;
    sVrNetHits[slot].yaw = attackYaw;
    sVrNetHits[slot].type = attackType;
    sVrNetHitWrite++;
}

bool vr_net_bridge_pop_hit(u8* victimGlobalIndex, s16* attackYaw, u8* attackType) {
    if (victimGlobalIndex == NULL || attackYaw == NULL || attackType == NULL ||
        sVrNetHitRead == sVrNetHitWrite) {
        return false;
    }
    const u32 slot = sVrNetHitRead % VR_NET_HIT_QUEUE;
    *victimGlobalIndex = sVrNetHits[slot].victim;
    *attackYaw = sVrNetHits[slot].yaw;
    *attackType = sVrNetHits[slot].type;
    sVrNetHitRead++;
    return true;
}

// Events: things that happen once (the Level Select).
#define VR_NET_EVENT_QUEUE 8

static struct {
    u8 kind;
    s32 value;
} sVrNetEvents[VR_NET_EVENT_QUEUE];
static u32 sVrNetEventRead = 0;
static u32 sVrNetEventWrite = 0;

void vr_net_bridge_push_event(u8 kind, s32 value) {
    if (sVrNetEventWrite - sVrNetEventRead >= VR_NET_EVENT_QUEUE) {
        return;
    }
    const u32 slot = sVrNetEventWrite % VR_NET_EVENT_QUEUE;
    sVrNetEvents[slot].kind = kind;
    sVrNetEvents[slot].value = value;
    sVrNetEventWrite++;
}

bool vr_net_bridge_pop_event(u8* kind, s32* value) {
    if (kind == NULL || value == NULL || sVrNetEventRead == sVrNetEventWrite) {
        return false;
    }
    const u32 slot = sVrNetEventRead % VR_NET_EVENT_QUEUE;
    *kind = sVrNetEvents[slot].kind;
    *value = sVrNetEvents[slot].value;
    sVrNetEventRead++;
    return true;
}

// The caps of the Spawn Menu. Nothing above keeps track of them once they are made, so this does: where
// they are is all the others need. (A slot is given up when its object is no longer that cap.)
#define VR_NET_TRACKED_CAPS 8

static struct Object* sVrNetCaps[VR_NET_TRACKED_CAPS] = { NULL };
static u8 sVrNetCapKinds[VR_NET_TRACKED_CAPS] = { 0 };

static const BehaviorScript* vr_net_bridge_cap_behavior(u8 kind) {
    switch (kind) {
        case VR_NET_EFFECT_CAP_WING:  return bhvWingCap;
        case VR_NET_EFFECT_CAP_METAL: return bhvMetalCap;
        default:                      return bhvVanishCap;
    }
}

static bool vr_net_bridge_cap_alive(u32 slot) {
    struct Object* cap = sVrNetCaps[slot];
    return cap != NULL && (cap->activeFlags & ACTIVE_FLAG_ACTIVE) &&
        obj_has_behavior(cap, vr_net_bridge_cap_behavior(sVrNetCapKinds[slot]));
}

void vr_net_bridge_track_cap(struct Object* cap, u8 kind) {
    if (cap == NULL) {
        return;
    }
    for (u32 slot = 0; slot < VR_NET_TRACKED_CAPS; slot++) {
        if (!vr_net_bridge_cap_alive(slot)) {
            sVrNetCaps[slot] = cap;
            sVrNetCapKinds[slot] = kind;
            return;
        }
    }
}

static void vr_net_bridge_add_effect(struct VrNetState* state, u8 kind, struct Object* object) {
    if (object == NULL || object->activeFlags == ACTIVE_FLAG_DEACTIVATED ||
        state->effectCount >= VR_NET_MAX_EFFECTS) {
        return;
    }
    const u32 slot = state->effectCount++;
    state->effectKind[slot] = kind;
    state->effectPos[slot][0] = object->oPosX;
    state->effectPos[slot][1] = object->oPosY;
    state->effectPos[slot][2] = object->oPosZ;
}

bool vr_net_bridge_get_state(struct VrNetState* state) {
    if (state == NULL) {
        return false;
    }
    memset(state, 0, sizeof(*state));
    state->bigHandsScale = 1.0f;
    if (!vr_is_active() || gMarioStates[0].marioObj == NULL) {
        return false;
    }

    for (u32 hand = 0; hand < 2 && hand < VR_CONTROLLER_COUNT; hand++) {
        struct VrControllerState controller;
        Vec3f position;
        if (!vr_get_controller_state(hand, &controller) ||
            !vr_get_controller_world_fist_from_state(hand, &controller, position, NULL)) {
            continue;
        }
        state->handValid[hand] = 1;
        if (controller.squeeze > 0.5f || controller.trigger > 0.5f) {
            state->handHow[hand] |= VR_NET_HAND_CLOSED;
        }
        // The hat he took off his head is in this hand.
        if (vr_is_controller_holding_cap(hand)) {
            state->handHow[hand] |= VR_NET_HAND_HAT;
            state->flags |= (u32)vr_net_bridge_held_hat() << VR_NET_FLAG_HAT_SHIFT;
        }
        state->hand[hand][0] = position[0];
        state->hand[hand][1] = position[1];
        state->hand[hand][2] = position[2];
    }

    if (vr_special_moves_fire_flower_active()) { state->flags |= VR_NET_FLAG_FIRE_FLOWER; }
    if (vr_special_moves_hammer_suit_active()) { state->flags |= VR_NET_FLAG_HAMMER_SUIT; }
    if (vr_special_moves_sonic_shoes_active()) { state->flags |= VR_NET_FLAG_SONIC_SHOES; }
    if (vr_special_moves_propeller_active())   { state->flags |= VR_NET_FLAG_PROPELLER; }
    if (vr_special_moves_power_star_active())  { state->flags |= VR_NET_FLAG_POWER_STAR; }
    if (vr_special_moves_big_hands_active()) {
        state->flags |= VR_NET_FLAG_BIG_HANDS;
        state->bigHandsScale = vr_special_moves_big_hands_scale();
    }

    for (u32 slot = 0; slot < VR_FIREBALL_PROJECTILE_COUNT; slot++) {
        vr_net_bridge_add_effect(state, VR_NET_EFFECT_FIREBALL, sVrFireballProjectiles[slot]);
    }
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_FIREBALL_CHARGE, sVrFireballChargeObject);
    for (u32 slot = 0; slot < VR_HAMMER_PROJECTILE_COUNT; slot++) {
        vr_net_bridge_add_effect(state, VR_NET_EFFECT_HAMMER, sVrHammerProjectiles[slot]);
    }
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_HAMMER_CHARGE, sVrHammerChargeObject);
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_RASENGAN, sVrRasenganObject);
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_RASEN_SHURIKEN, sVrRasenShurikenProjectile);

    // The items waiting in the level (out of his boxes, or out of his Spawn Menu).
    for (u32 slot = 0; slot < VR_FIRE_FLOWER_PICKUP_COUNT; slot++) {
        vr_net_bridge_add_effect(state, VR_NET_EFFECT_ITEM_FIRE_FLOWER, sVrFireFlowerPickups[slot]);
    }
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_ITEM_HAMMER_SUIT, sVrHammerSuitPickupObject);
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_ITEM_SONIC_SHOES, sVrSonicShoesPickupObject);
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_ITEM_BIG_HANDS, sVrBigHandsPickupObject);
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_ITEM_PROPELLER, sVrPropellerPickupObject);
    vr_net_bridge_add_effect(state, VR_NET_EFFECT_ITEM_POWER_STAR, sVrPowerStarPickup);
    for (u32 slot = 0; slot < VR_NET_TRACKED_CAPS; slot++) {
        if (vr_net_bridge_cap_alive(slot)) {
            vr_net_bridge_add_effect(state, sVrNetCapKinds[slot], sVrNetCaps[slot]);
        }
    }

    // The hat he threw.
    extern struct Object* gVrPaintingExitHatObject;
    struct Object* hat = gVrPaintingExitHatObject;
    if (hat != NULL && (hat->activeFlags & ACTIVE_FLAG_ACTIVE)) {
        u8 kind = VR_NET_EFFECT_CAP_NORMAL;
        if (obj_has_behavior(hat, bhvWingCap)) {
            kind = VR_NET_EFFECT_CAP_WING;
        } else if (((hat->oBehParams >> 8) & MARIO_METAL_CAP) != 0) {
            kind = VR_NET_EFFECT_CAP_METAL;
        }
        vr_net_bridge_add_effect(state, kind, hat);
    }
    return true;
}
"""

VR_BRIDGE_LUA = """\
// [gore fork] This player's VR state, for the built-in mod (vrsync.lua). Only the VR builds have these two
// functions; a mod that finds them missing knows it runs on a flat build.
//
// vr_net_state() -> nil while VR isn't in use, else an array:
//     flags, bigHandsScale,
//     leftValid, leftHow, x, y, z,  rightValid, rightHow, x, y, z,
//     count, then (kind, x, y, z) for each thing of his in the level
// (the meaning of flags, how and kind: enum VrNetFlag, VrNetHand, VrNetEffect in vr_hand_interaction.h)
int smlua_func_vr_net_state(lua_State* L) {
    struct VrNetState state;
    if (!vr_net_bridge_get_state(&state)) {
        lua_pushnil(L);
        return 1;
    }
    int n = 0;
    lua_createtable(L, 13 + (int)state.effectCount * 4, 0);
#define FORK_PUSH(value) do { lua_pushnumber(L, (lua_Number)(value)); lua_rawseti(L, -2, ++n); } while (0)
    FORK_PUSH(state.flags);
    FORK_PUSH(state.bigHandsScale);
    for (int hand = 0; hand < 2; hand++) {
        FORK_PUSH(state.handValid[hand]);
        FORK_PUSH(state.handHow[hand]);
        FORK_PUSH(state.hand[hand][0]);
        FORK_PUSH(state.hand[hand][1]);
        FORK_PUSH(state.hand[hand][2]);
    }
    FORK_PUSH(state.effectCount);
    for (u32 i = 0; i < state.effectCount; i++) {
        FORK_PUSH(state.effectKind[i]);
        FORK_PUSH(state.effectPos[i][0]);
        FORK_PUSH(state.effectPos[i][1]);
        FORK_PUSH(state.effectPos[i][2]);
    }
#undef FORK_PUSH
    return 1;
}

// vr_net_pop_hit() -> victimGlobalIndex, yaw, attackType of the next VR hit on another player; nothing when
// there is none waiting.
int smlua_func_vr_net_pop_hit(lua_State* L) {
    u8 victim = 0;
    s16 yaw = 0;
    u8 type = 0;
    if (!vr_net_bridge_pop_hit(&victim, &yaw, &type)) {
        return 0;
    }
    lua_pushinteger(L, victim);
    lua_pushinteger(L, yaw);
    lua_pushinteger(L, type);
    return 3;
}

// vr_net_pop_event() -> kind, value of the next thing this player did that the others are told about
// (enum VrNetEvent); nothing when there is none waiting.
int smlua_func_vr_net_pop_event(lua_State* L) {
    u8 kind = 0;
    s32 value = 0;
    if (!vr_net_bridge_pop_event(&kind, &value)) {
        return 0;
    }
    lua_pushinteger(L, kind);
    lua_pushinteger(L, value);
    return 2;
}

// vr_net_head() -> x, y, z, yaw, pitch, roll, firstPerson: where this player's eyes are in the level and
// where they look (yaw as Mario's, pitch up, roll to his left shoulder; all three as the game's 16-bit
// angles), and whether he looks out of his Mario's head. With firstPerson the angles are in the level;
// without it they are from straight ahead of where he sits (see fork_vr_head_world). Nothing while the
// headset isn't tracked.
int smlua_func_vr_net_head(lua_State* L) {
    Vec3f position;
    s16 yaw = 0;
    s16 pitch = 0;
    s16 roll = 0;
    bool firstPerson = false;
    if (!fork_vr_head_world(position, &yaw, &pitch, &roll, &firstPerson)) {
        return 0;
    }
    lua_pushnumber(L, position[0]);
    lua_pushnumber(L, position[1]);
    lua_pushnumber(L, position[2]);
    lua_pushinteger(L, yaw);
    lua_pushinteger(L, pitch);
    lua_pushinteger(L, roll);
    lua_pushboolean(L, firstPerson);
    return 7;
}

// vr_net_hands() -> leftThere, fx, fy, fz, tx, ty, tz, rightThere, fx, fy, fz, tx, ty, tz: how each hand is
// turned, in the level. f: the way its fingers point; t: the way its thumb does when the hand is flat. Both
// one unit long. (A hand that isn't there: false and six zeros.)
int smlua_func_vr_net_hands(lua_State* L) {
    for (u32 hand = 0; hand < 2; hand++) {
        Vec3f fingers = { 0.0f, 0.0f, 0.0f };
        Vec3f thumb = { 0.0f, 0.0f, 0.0f };
        const bool there = fork_vr_hand_world(hand, fingers, thumb);
        lua_pushboolean(L, there);
        for (u32 axis = 0; axis < 3; axis++) { lua_pushnumber(L, there ? fingers[axis] : 0.0f); }
        for (u32 axis = 0; axis < 3; axis++) { lua_pushnumber(L, there ? thumb[axis] : 0.0f); }
    }
    return 14;
}

// vr_set_death_camera(dead): the built-in mod says each frame whether this player is dead. While he is,
// the VR camera is third person (see fork_vr_death_camera in rendering_graph_node.c).
int smlua_func_vr_set_death_camera(lua_State* L) {
    fork_vr_death_camera(lua_toboolean(L, 1) != 0);
    return 0;
}

"""

VR_DEATH_CAMERA_C = """\

// [gore fork] Third person while this player is dead.
//
// In first person the player looks out of Mario's head, and dying is something that happens to Mario's
// body: he would see none of it. So for as long as he is dead the camera mode is third person, whatever he
// chose, and what he chose comes back when he lives again.
//
// The built-in mod knows when he is dead (most of the deaths are its own) and says so every frame with
// vr_set_death_camera(true). If it stops saying so without saying "alive" (the lobby was left with a dead
// Mario), his choice comes back by itself after a second. The config file is always written with his
// choice (configfile.c asks fork_vr_camera_mode_choice).
#define FORK_DEATH_CAMERA_TIMEOUT 30 // game frames

static bool sForkDeathCamera = false;
static unsigned int sForkDeathCameraChoice = VR_CAMERA_MODE_FIRST_PERSON;
static u32 sForkDeathCameraFrame = 0;

static void fork_vr_death_camera_end(void) {
    sForkDeathCamera = false;
    configVrCameraMode = sForkDeathCameraChoice < VR_CAMERA_MODE_COUNT
        ? sForkDeathCameraChoice
        : VR_CAMERA_MODE_FIRST_PERSON;
}

void fork_vr_death_camera(bool dead) {
    if (dead && vr_is_active()) {
        if (!sForkDeathCamera) {
            sForkDeathCamera = true;
            sForkDeathCameraChoice = configVrCameraMode;
        }
        sForkDeathCameraFrame = gGlobalTimer;
    } else if (sForkDeathCamera) {
        fork_vr_death_camera_end();
    }
    // (as the camera menu does after a change; it does nothing when the mode is what it was)
    vr_handle_camera_mode_change();
}

// Before the camera mode is looked at (first thing in vr_handle_camera_mode_change, so every frame).
void fork_vr_death_camera_tick(void) {
    if (!sForkDeathCamera) {
        return;
    }
    if (!vr_is_active() || (u32)(gGlobalTimer - sForkDeathCameraFrame) > FORK_DEATH_CAMERA_TIMEOUT) {
        fork_vr_death_camera_end();
        return;
    }
    if (configVrCameraMode != VR_CAMERA_MODE_THIRD_PERSON) {
        // The camera menu changed it meanwhile: that is his choice from now on. He is still dead.
        sForkDeathCameraChoice = configVrCameraMode;
        configVrCameraMode = VR_CAMERA_MODE_THIRD_PERSON;
    }
}

unsigned int fork_vr_camera_mode_choice(void) {
    return sForkDeathCamera ? sForkDeathCameraChoice : configVrCameraMode;
}
"""

VR_EYES_C = """\
// =========================================================================================================
// [gore fork] First person: his eyes are where his character's are
//
// The VR game put the first-person camera at a height out of a table: 160 above his feet for Mario (and 7
// more on top), just under the top of the hat for Luigi, Toad, Waluigi and Wario by numbers that put Luigi
// half a Mario above Mario, and Mario's for every character a mod brings. None of those is where the
// character's eyes are (Mario's are about 118 above his feet), so it then stretched the body it shows the
// player: the chest was lifted until the neck sat at another number of the table (135 for Mario, whose
// neck is at 88). A player a third taller than the Mario everybody else sees, who looks down at things a
// Mario looks straight at: on the others' screens his head pointed at the floor in front of whatever he
// was looking at, and from his own eyes everything was too small and too low.
//
// Here the height is measured: where the joint his head sits on is above his feet, read off the skeleton
// of the model he wears while it stands still (ACT_IDLE, on ground that doesn't move), and his eyes
// FORK_VR_EYES_UP above that. Any model: the built-in five, a model of a mod, a tall one, a short one. It
// is measured again when he changes character and whenever he stands still again, the camera glides to a
// new value, and until the first measurement it is Mario's. The body is no longer stretched.
//
// "First Person Height" in the VR Camera Settings is now from there: 100 is his character's eyes, less is
// lower, more is higher. (The heights saved before meant something else and are set back to 100 once.)
// =========================================================================================================
#define FORK_VR_EYES_UP 30.0f     // how far the eyes are above the joint the head sits on (vrsync.lua: EYES_UP)
#define FORK_VR_NECK_MARIO 88.0f  // how far that joint is above Mario's feet
#define FORK_VR_NECK_STILL 5      // game frames he has to have stood still before the skeleton is read

static f32 sForkVrTorsoLift = 0.0f;         // what "Torso Height" lifted his chest by, the last time it was drawn
static u32 sForkVrTorsoLiftFrame = UINT32_MAX;
static f32 sForkVrNeck = 0.0f;              // measured (0: not yet)
static f32 sForkVrNeckShown = 0.0f;         // what the camera uses: glides to it
static bool sForkVrNeckSure = false;        // measured standing still, for the model he wears now
static const void* sForkVrNeckModel = NULL;
static u32 sForkVrNeckCharacter = UINT32_MAX;
static u32 sForkVrNeckFrame = UINT32_MAX;
static u32 sForkVrNeckStill = 0;
static f32 sForkVrNeckFeet = 0.0f;

static f32 fork_vr_neck_height(void) {
    struct MarioState* m = &gMarioStates[0];
    struct MarioBodyState* body = m->marioBodyState;
    if (m->marioObj != NULL && body != NULL && sForkVrNeckFrame != gGlobalTimer) {
        sForkVrNeckFrame = gGlobalTimer;

        const void* model = m->marioObj->header.gfx.sharedChild;
        const u32 character = gNetworkPlayers[0].overrideModelIndex;
        if (model != sForkVrNeckModel || character != sForkVrNeckCharacter) {
            sForkVrNeckModel = model;
            sForkVrNeckCharacter = character;
            sForkVrNeckSure = false;
            sForkVrNeckStill = 0;
        }

        const f32 feet = m->marioObj->header.gfx.pos[1];
        const bool level = fabsf(feet - sForkVrNeckFeet) < 0.05f;
        sForkVrNeckFeet = feet;
        if (level && m->action == ACT_IDLE && !vr_special_moves_propeller_active()) {
            sForkVrNeckStill++;
        } else {
            sForkVrNeckStill = 0;
        }

        // (the skeleton as it was drawn last: this frame's isn't drawn yet when the camera asks)
        const u32 drawn = body->updateHeadPosTime;
        if (level && (drawn == gGlobalTimer || drawn + 1 == gGlobalTimer)) {
            const f32 lift = sForkVrTorsoLiftFrame == drawn ? sForkVrTorsoLift : 0.0f;
            const f32 neck = body->animPartsPos[MARIO_ANIM_PART_HEAD][1] - lift - feet;
            if (isfinite(neck) && neck > 20.0f && neck < 600.0f) {
                if (sForkVrNeckStill >= FORK_VR_NECK_STILL) {
                    // (a breath doesn't move the camera)
                    if (!sForkVrNeckSure || fabsf(neck - sForkVrNeck) > 1.5f) {
                        sForkVrNeck = neck;
                    }
                    sForkVrNeckSure = true;
                } else if (!sForkVrNeckSure && sForkVrNeckStill == 0 &&
                           (m->action & ACT_GROUP_MASK) == ACT_GROUP_MOVING &&
                           !(m->action & (ACT_FLAG_DIVING | ACT_FLAG_BUTT_OR_STOMACH_SLIDE | ACT_FLAG_SHORT_HITBOX))) {
                    // He hasn't stood still yet with this model, he is off running: close enough until he
                    // does. (Running leans him forward a little; the highest it gets is the nearest.)
                    if (sForkVrNeck <= 0.0f || neck > sForkVrNeck || fabsf(neck - sForkVrNeck) > 25.0f) {
                        sForkVrNeck = neck;
                    }
                }
            }
        }

        const f32 wanted = sForkVrNeck > 0.0f ? sForkVrNeck : FORK_VR_NECK_MARIO;
        if (sForkVrNeckShown <= 0.0f || fabsf(wanted - sForkVrNeckShown) < 0.5f) {
            sForkVrNeckShown = wanted;
        } else {
            sForkVrNeckShown += (wanted - sForkVrNeckShown) * 0.3f;
        }
    }
    return sForkVrNeckShown > 0.0f ? sForkVrNeckShown : FORK_VR_NECK_MARIO;
}

// What the game's three users of the first-person camera height get in place of the saved number: the
// regular camera (which adds 7 of its own, so here they are taken off), the one while swimming and the one
// that leans with his body in flight and on a shell.
static unsigned int fork_vr_camera_height(unsigned int character) {
    const f32 slider = (f32) MIN(*config_vr_camera_height_for_character(character), VR_CAMERA_HEIGHT_MAX);
    const f32 normal = (f32) config_vr_camera_default_height_for_character(character);
    const f32 height = fork_vr_neck_height() + FORK_VR_EYES_UP - 7.0f + (slider - normal);
    if (!(height > 0.0f)) {
        return 0U;
    }
    return (unsigned int) MIN(height + 0.5f, (f32) VR_CAMERA_HEIGHT_MAX);
}

"""

VR_HEAD_C = """\

// =========================================================================================================
// [gore fork] Where this player's eyes are in the level, where they look, and how his hands are turned
//
// For the built-in mod, which tells the others (vrsync.lua): they turn his Mario's head this way, they
// place his hands by how far each is from his eyes, and they turn each hand the way he holds it. Measured
// the way his hands are (vr_get_controller_world_fist_raw_from_state): what the headset tracks, put through
// the game's camera, so that everything fits together in every camera mode.
//
// His eyes are where his own picture is drawn from (vr_build_head_view_matrix), and that is not always
// where the headset is: in first person a PC headset's height doesn't count (his eyes are as high as his
// character's, however tall he is and wherever he was when he recentred), and neither does any headset's
// with True First Person or True Diving. Leaving that out put his hands too low or too high on everybody
// else's screen by exactly that much.
//
// Where he looks: in first person that is a direction in the level. In third person it isn't: there the
// headset looks at his Mario from where the camera is, mostly from behind and from above, and a Mario who
// looks that way in the level has his head as far round as it goes whenever he runs towards the camera,
// and looks at the floor all the time. So in third person the angles are from straight ahead of where the
// player sits, and the others turn his Mario's head that far from the way his Mario faces.
// =========================================================================================================
static bool fork_vr_camera_inverse(Mat4 inverse) {
    if (!vr_is_active() || sCameraNode == NULL) {
        return false;
    }
    Mat4 cameraMatrix;
    vr_build_game_camera_matrix(cameraMatrix, sCameraNode->pos, sCameraNode->focus, sCameraNode->roll);
    mtxf_inverse(inverse, cameraMatrix);
    return true;
}

// `firstPerson`: he looks out of his Mario's head. His own game then draws his body facing where he looks,
// whichever way his Mario is running (see vr_get_stabilized_body_yaw), and so do the others.
bool fork_vr_head_world(Vec3f position, s16* yaw, s16* pitch, s16* roll, bool* firstPerson) {
    float translation[3] = { 0 };
    float q[4] = { 0 };
    Mat4 inverse;
    if (position == NULL || yaw == NULL || pitch == NULL || roll == NULL ||
        !vr_get_head_translation(translation) || !vr_get_head_rotation(q) || !fork_vr_camera_inverse(inverse)) {
        return false;
    }
    for (u32 i = 0; i < 4; i++) {
        if (!isfinite(q[i]) || (i < 3 && !isfinite(translation[i]))) {
            return false;
        }
    }
    vr_apply_roomscale_tracking_compensation(translation);
    const bool first = configVrCameraMode == VR_CAMERA_MODE_FIRST_PERSON;
    // (as vr_build_head_view_matrix does)
    if (first && (configVrExperimentalTrueFirstPerson || vr_first_person_true_diving_active())) {
        translation[1] = 0.0f;
    }
#ifndef __ANDROID__
    if (first) {
        translation[1] = 0.0f;
    }
#endif

    const f32 x = q[0], y = q[1], z = q[2], w = q[3];
    // (the headset looks down its own -Z; +Y is the top of the head)
    const f32 local[3][3] = {
        { translation[0] * 100.0f, translation[1] * 100.0f, translation[2] * 100.0f },
        { -2.0f * (x * z + w * y), -2.0f * (y * z - w * x), -(1.0f - 2.0f * (x * x + y * y)) },
        { 2.0f * (x * y - w * z), 1.0f - 2.0f * (x * x + z * z), 2.0f * (y * z + w * x) },
    };
    Vec3f forward;
    Vec3f up;
    for (u32 axis = 0; axis < 3; axis++) {
        position[axis] = local[0][0] * inverse[0][axis] + local[0][1] * inverse[1][axis] +
                         local[0][2] * inverse[2][axis] + inverse[3][axis];
        if (first) {
            forward[axis] = local[1][0] * inverse[0][axis] + local[1][1] * inverse[1][axis] +
                            local[1][2] * inverse[2][axis];
            up[axis] = local[2][0] * inverse[0][axis] + local[2][1] * inverse[1][axis] +
                       local[2][2] * inverse[2][axis];
        } else {
            // (the headset's axes with straight ahead as a yaw of 0: half a turn about the one that is up)
            const f32 sign = axis == 1 ? 1.0f : -1.0f;
            forward[axis] = local[1][axis] * sign;
            up[axis] = local[2][axis] * sign;
        }
    }
    const f32 flat = sqrtf(forward[0] * forward[0] + forward[2] * forward[2]);
    if (!isfinite(flat) || !isfinite(forward[1]) || !isfinite(position[0]) || !isfinite(position[1]) ||
        !isfinite(position[2]) || (flat <= 0.0001f && fabsf(forward[1]) <= 0.0001f)) {
        return false;
    }
    // (straight up or down has no yaw of its own: the top of the head says which way he faces)
    if (flat > 0.02f) {
        *yaw = atan2s(forward[2], forward[0]);
    } else if (forward[1] > 0.0f) {
        *yaw = atan2s(-up[2], -up[0]);
    } else {
        *yaw = atan2s(up[2], up[0]);
    }
    *pitch = atan2s(flat, forward[1]);

    // roll: how far the top of his head leans to his left, off where it is with a level head
    const f32 levelLeft[3] = { coss(*yaw), 0.0f, -sins(*yaw) };
    const f32 levelUp[3] = {
        forward[1] * levelLeft[2] - forward[2] * levelLeft[1],
        forward[2] * levelLeft[0] - forward[0] * levelLeft[2],
        forward[0] * levelLeft[1] - forward[1] * levelLeft[0],
    };
    *roll = atan2s(up[0] * levelUp[0] + up[1] * levelUp[1] + up[2] * levelUp[2],
                   up[0] * levelLeft[0] + up[1] * levelLeft[1] + up[2] * levelLeft[2]);
    if (firstPerson != NULL) {
        *firstPerson = first;
    }
    return true;
}

// How a hand (0: left, 1: right) is turned, in the level: the way its fingers point, and the way its thumb
// does when the hand is flat. Exactly what this player sees of his own glove (vr_patch_controller_hand_
// matrices): the glove model's first axis follows the controller's tip, and its other two are the
// controller's, turned by the "glove rotation" this player has set.
bool fork_vr_hand_world(u32 hand, Vec3f fingers, Vec3f thumb) {
    struct VrControllerState state;
    Mat4 inverse;
    if (fingers == NULL || thumb == NULL || hand >= 2 || hand >= VR_CONTROLLER_COUNT ||
        !vr_get_controller_state(hand, &state) || (!state.gripPoseValid && !state.aimPoseValid) ||
        !fork_vr_camera_inverse(inverse)) {
        return false;
    }
    const float* rotation = state.aimPoseValid ? state.aimRotation : state.gripRotation;
    Vec3f right = { 1.0f, 0.0f, 0.0f };
    Vec3f top = { 0.0f, 1.0f, 0.0f };
    Vec3f backward = { 0.0f, 0.0f, 1.0f };
    vr_rotate_pose_vector(rotation, right, right);
    vr_rotate_pose_vector(rotation, top, top);
    vr_rotate_pose_vector(rotation, backward, backward);

    const unsigned int degrees = (hand == VR_CONTROLLER_LEFT ? configVrLeftGloveRotationX
                                                             : configVrRightGloveRotationX) % 360U;
    const s16 turn = (s16)(degrees * 0x10000U / 360U);
    const f32 sinTurn = sins(turn), cosTurn = coss(turn);
    // (Mario's hands have the thumb on the far side of their second axis)
    f32 local[2][3];
    for (u32 axis = 0; axis < 3; axis++) {
        local[0][axis] = -backward[axis];
        local[1][axis] = -(cosTurn * top[axis] + sinTurn * right[axis]);
    }
    f32 length[2] = { 0.0f, 0.0f };
    for (u32 axis = 0; axis < 3; axis++) {
        fingers[axis] = local[0][0] * inverse[0][axis] + local[0][1] * inverse[1][axis] +
                        local[0][2] * inverse[2][axis];
        thumb[axis] = local[1][0] * inverse[0][axis] + local[1][1] * inverse[1][axis] +
                      local[1][2] * inverse[2][axis];
        length[0] += fingers[axis] * fingers[axis];
        length[1] += thumb[axis] * thumb[axis];
    }
    if (!isfinite(length[0]) || !isfinite(length[1]) || length[0] <= 0.0001f || length[1] <= 0.0001f) {
        return false;
    }
    length[0] = sqrtf(length[0]);
    length[1] = sqrtf(length[1]);
    for (u32 axis = 0; axis < 3; axis++) {
        fingers[axis] /= length[0];
        thumb[axis] /= length[1];
    }
    return true;
}
"""

VR_BRIDGE_HAT_C = """\

// [gore fork] Which hat it is that he holds in his hand, for the other players (enum VrNetHat in
// vr_hand_interaction.h; see vr_net_bridge_get_state there).
u8 vr_net_bridge_held_hat(void) {
    if (sVrPaintingExitHatWingCap || (sVrHeldCapFlags & MARIO_WING_CAP) != 0) {
        return VR_NET_HAT_WING;
    }
    if ((sVrHeldCapFlags & MARIO_METAL_CAP) != 0) {
        return VR_NET_HAT_METAL;
    }
    if ((sVrHeldCapFlags & MARIO_VANISH_CAP) != 0) {
        return VR_NET_HAT_VANISH;
    }
    return VR_NET_HAT_NORMAL;
}
"""


FORK_VOICE_H = """\
// [gore fork] Voice chat for the flat builds. See fork_voice.c.
#ifndef FORK_VOICE_H
#define FORK_VOICE_H

#include <PR/ultratypes.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct Packet;

void fork_voice_update(void);
void fork_voice_receive_capability(struct Packet* p);
void fork_voice_receive_audio(struct Packet* p);
const uint8_t* fork_voice_mix(const uint8_t* buffer, size_t length);

#endif
"""

FORK_VOICE_C = """\
// [gore fork] Voice chat for the flat builds.
//
// The VR builds this one shares its lobbies with have voice chat built in. This is the other end of it,
// written for this build: the same two packets, the same sound format (16 kHz mono, G.711 mu-law, 320
// samples = 20 ms per packet), so both kinds of build hear each other.
//
//   * A game says every five seconds that it does voice (PACKET_VR_VOICE_CAPABILITY). Sound is only sent
//     to games that have said so.
//   * What arrives is queued per player and mixed into the game's own sound just before that goes to the
//     sound card (audio_sdl.c).
//   * The microphone is off until the player switches it on (Options > Sound). It is read through SDL,
//     which on Android also asks for the permission the first time.
//   * The Wii U is the exception: its SDL cannot record. There the microphone is the one in the GamePad,
//     read through the console's own library (the second half of "The microphone" below).
#include <stdatomic.h>
#include <string.h>

#ifdef TARGET_WII_U
#include <malloc.h>
#include <mic/mic.h>
#else
#include <SDL2/SDL.h>
#endif

#include "fork_voice.h"
#include "pc/configfile.h"
#include "pc/network/network.h"
#include "pc/network/network_player.h"
#include "pc/network/packets/packet.h"

#define FV_RATE 16000
#define FV_FRAME 320        // samples in one packet
#define FV_QUEUE 8192       // samples waiting per player (half a second)
#define FV_VERSION 1
#define FV_MIX_BYTES 16384  // the most game sound mixed in one go
#define FV_ANNOUNCE 150     // frames between two "I do voice"
#define FV_GATE 500         // quieter than this is silence...
#define FV_HANG 15          // ...once it has lasted this many packets (0.3 s)

struct FvQueue {
    s16 samples[FV_QUEUE];
    _Atomic u32 read;  // (moved by the sound output)
    _Atomic u32 write; // (moved by the network)
};

static struct FvQueue sQueues[MAX_PLAYERS];
static bool sCapable[MAX_PLAYERS];
static bool sWasOn = false;
static u32 sAnnounceTimer = 0;
static u32 sMicRetry = 0;
static u32 sQuietPackets = FV_HANG;
static u8 sMixed[FV_MIX_BYTES];

static bool fv_on(void) {
    return configForkVoice && gNetworkType != NT_NONE && gNetworkPlayerLocal != NULL;
}

// G.711 mu-law: 16 bits of sound in 8.
static u8 fv_encode(s16 pcm) {
    s32 value = pcm;
    u8 sign = 0;
    if (value < 0) {
        value = -value;
        sign = 0x80;
    }
    if (value > 32635) { value = 32635; }
    value += 132;
    u8 exponent = 7;
    for (s32 bit = 0x4000; exponent > 0 && (value & bit) == 0; bit >>= 1) {
        exponent--;
    }
    u8 mantissa = (u8)((value >> (exponent + 3)) & 0x0F);
    return (u8)~(sign | (exponent << 4) | mantissa);
}

static s16 fv_decode(u8 code) {
    code = (u8)~code;
    s32 value = (((code & 0x0F) << 3) + 132) << ((code & 0x70) >> 4);
    value -= 132;
    return (s16)((code & 0x80) ? -value : value);
}


static void fv_announce(void) {
    struct Packet p = { 0 };
    packet_init(&p, PACKET_VR_VOICE_CAPABILITY, false, PLMT_NONE);
    u8 globalIndex = gNetworkPlayerLocal->globalIndex;
    u8 version = FV_VERSION;
    packet_write(&p, &globalIndex, sizeof(globalIndex));
    packet_write(&p, &version, sizeof(version));
    network_send(&p);
}

static void fv_send(const s16* frame) {
    // Silence isn't sent: an open microphone in a quiet room would cost every listener 16 kB a second.
    s32 peak = 0;
    for (u32 i = 0; i < FV_FRAME; i++) {
        s32 magnitude = frame[i] < 0 ? -(s32)frame[i] : frame[i];
        if (magnitude > peak) { peak = magnitude; }
    }
    if (peak >= FV_GATE) {
        sQuietPackets = 0;
    } else if (sQuietPackets >= FV_HANG) {
        return;
    } else {
        sQuietPackets++;
    }

    u8 encoded[FV_FRAME];
    for (u32 i = 0; i < FV_FRAME; i++) {
        encoded[i] = fv_encode(frame[i]);
    }
    for (u32 i = 0; i < MAX_PLAYERS; i++) {
        struct NetworkPlayer* np = &gNetworkPlayers[i];
        if (!np->connected || np == gNetworkPlayerLocal || np->globalIndex >= MAX_PLAYERS ||
            !sCapable[np->globalIndex]) {
            continue;
        }
        struct Packet p = { 0 };
        packet_init(&p, PACKET_VR_VOICE_AUDIO, false, PLMT_NONE);
        u8 globalIndex = gNetworkPlayerLocal->globalIndex;
        packet_write(&p, &globalIndex, sizeof(globalIndex));
        packet_write(&p, encoded, sizeof(encoded));
        network_send_to(np->localIndex, &p);
    }
}

// ---- The microphone ----
// Six things, written twice: is it open, open it, shut it, how many samples (at 16 kHz) are waiting, throw
// away what is waiting, and take one packet's worth.
#ifdef TARGET_WII_U

// The GamePad's microphone gives 32 kHz mono, 16 bit, into a ring of samples that this file owns and the
// console fills. MICGetStatus says how many are waiting and where the first one is; MICSetDataConsumed
// says how many were taken. Two of its samples make one of ours.
#define FV_WIIU_RING 0x8000 // samples: one second (the console wants 0x2800 or more)
#define FV_WIIU_OPEN_FLAG (1 << 1)

static s16* sWiiuRing = NULL;
static MICWorkMemory sWiiuWork;
static MICHandle sWiiuMic = -1;

static bool fv_mic_is_open(void) {
    return sWiiuMic >= 0;
}

static void fv_mic_shut(void) {
    if (sWiiuMic >= 0) {
        MICClose(sWiiuMic);
        MICUninit(sWiiuMic);
        sWiiuMic = -1;
    }
}

static bool fv_mic_open(void) {
    if (sWiiuRing == NULL) {
        sWiiuRing = memalign(0x40, FV_WIIU_RING * sizeof(s16));
        if (sWiiuRing == NULL) { return false; }
    }
    memset(sWiiuRing, 0, FV_WIIU_RING * sizeof(s16));
    sWiiuWork.sampleMaxCount = FV_WIIU_RING;
    sWiiuWork.sampleBuffer = sWiiuRing;

    MICError error = MIC_ERROR_OK;
    MICHandle handle = MICInit(MIC_INSTANCE_0, 0, &sWiiuWork, &error);
    if (handle < 0) {
        // (no GamePad connected, most likely)
        return false;
    }
    if (MICOpen(handle) != MIC_ERROR_OK) {
        MICUninit(handle);
        return false;
    }
    sWiiuMic = handle;
    return true;
}

// How many of the console's samples are waiting and where the first is; false if the microphone has gone
// (the GamePad was switched off): it is shut then, and opened again by the retry.
static bool fv_wiiu_status(u32* waiting, u32* position) {
    MICStatus status;
    memset(&status, 0, sizeof(status));
    if (MICGetStatus(sWiiuMic, &status) != MIC_ERROR_OK || (status.state & FV_WIIU_OPEN_FLAG) == 0 ||
        status.availableData < 0 || status.availableData > FV_WIIU_RING ||
        status.bufferPos < 0 || status.bufferPos >= FV_WIIU_RING) {
        fv_mic_shut();
        return false;
    }
    *waiting = (u32)status.availableData;
    *position = (u32)status.bufferPos;
    return true;
}

static u32 fv_mic_waiting(void) {
    u32 waiting = 0, position = 0;
    if (!fv_mic_is_open() || !fv_wiiu_status(&waiting, &position)) { return 0; }
    return waiting / 2;
}

static void fv_mic_drop(void) {
    u32 waiting = 0, position = 0;
    if (!fv_mic_is_open() || !fv_wiiu_status(&waiting, &position)) { return; }
    if (waiting > 0) { MICSetDataConsumed(sWiiuMic, (int)waiting); }
}

static bool fv_mic_take(s16* frame) {
    u32 waiting = 0, position = 0;
    if (!fv_mic_is_open() || !fv_wiiu_status(&waiting, &position) || waiting < FV_FRAME * 2) { return false; }
    for (u32 i = 0; i < FV_FRAME; i++) {
        s32 first = sWiiuRing[(position + i * 2) % FV_WIIU_RING];
        s32 second = sWiiuRing[(position + i * 2 + 1) % FV_WIIU_RING];
        frame[i] = (s16)((first + second) / 2);
    }
    return MICSetDataConsumed(sWiiuMic, FV_FRAME * 2) == MIC_ERROR_OK;
}

// (the ring holds one second; nearly full means the game stood still and what waits is old)
#define FV_MIC_TOO_MUCH ((FV_WIIU_RING / 2) - FV_FRAME * 2)

#else

static SDL_AudioDeviceID sMic = 0;

static bool fv_mic_is_open(void) {
    return sMic != 0;
}

static void fv_mic_shut(void) {
    if (sMic != 0) {
        SDL_CloseAudioDevice(sMic);
        sMic = 0;
    }
}

static bool fv_mic_open(void) {
    if (!SDL_WasInit(SDL_INIT_AUDIO)) { return false; }
    SDL_AudioSpec want, have;
    SDL_zero(want);
    want.freq = FV_RATE;
    want.format = AUDIO_S16SYS;
    want.channels = 1;
    want.samples = FV_FRAME;
    want.callback = NULL;
    // (no changes allowed: SDL converts whatever the microphone gives into exactly this)
    sMic = SDL_OpenAudioDevice(NULL, 1, &want, &have, 0);
    if (sMic == 0) { return false; }
    SDL_PauseAudioDevice(sMic, 0);
    return true;
}

static u32 fv_mic_waiting(void) {
    return SDL_GetQueuedAudioSize(sMic) / sizeof(s16);
}

static void fv_mic_drop(void) {
    SDL_ClearQueuedAudio(sMic);
}

static bool fv_mic_take(s16* frame) {
    const u32 bytes = FV_FRAME * sizeof(s16);
    return SDL_GetQueuedAudioSize(sMic) >= bytes && SDL_DequeueAudio(sMic, frame, bytes) == bytes;
}

#define FV_MIC_TOO_MUCH FV_RATE

#endif

static void fv_close_mic(void) {
    fv_mic_shut();
    sQuietPackets = FV_HANG;
}

static void fv_microphone(void) {
    if (!configForkVoiceMic) {
        fv_close_mic();
        sMicRetry = 0;
        return;
    }
    if (!fv_mic_is_open()) {
        if (sMicRetry > 0) {
            sMicRetry--;
            return;
        }
        if (!fv_mic_open()) {
            // No microphone, or no permission (yet): listening still works. Try again in five seconds.
            sMicRetry = FV_ANNOUNCE;
            return;
        }
    }

    // After a hitch there can be a second of old sound waiting; nobody wants to hear that late.
    if (fv_mic_waiting() > FV_MIC_TOO_MUCH) {
        fv_mic_drop();
        return;
    }
    s16 frame[FV_FRAME];
    for (u32 guard = 0; guard < 16 && fv_mic_take(frame); guard++) {
        fv_send(frame);
    }
    if (!fv_mic_is_open()) {
        // (it went away while being read)
        sMicRetry = FV_ANNOUNCE;
    }
}

// Once per game frame, from network_update.
void fork_voice_update(void) {
    if (!fv_on()) {
        if (sWasOn) {
            memset(sCapable, 0, sizeof(sCapable));
            for (u32 i = 0; i < MAX_PLAYERS; i++) {
                atomic_store(&sQueues[i].read, atomic_load(&sQueues[i].write));
            }
        }
        sWasOn = false;
        fv_close_mic();
        return;
    }
    if (!sWasOn || ++sAnnounceTimer >= FV_ANNOUNCE) {
        sAnnounceTimer = 0;
        fv_announce();
    }
    sWasOn = true;

    // (a seat that has emptied may be taken by somebody who doesn't do voice)
    for (u32 i = 0; i < MAX_PLAYERS; i++) {
        struct NetworkPlayer* np = &gNetworkPlayers[i];
        if (!np->connected && np->globalIndex < MAX_PLAYERS) {
            sCapable[np->globalIndex] = false;
        }
    }
    fv_microphone();
}

void fork_voice_receive_capability(struct Packet* p) {
    u8 globalIndex = UNKNOWN_GLOBAL_INDEX;
    u8 version = 0;
    packet_read(p, &globalIndex, sizeof(globalIndex));
    packet_read(p, &version, sizeof(version));
    if (p->error || globalIndex >= MAX_PLAYERS || packet_spoofed(p, globalIndex) || !fv_on()) {
        return;
    }
    sCapable[globalIndex] = (version == FV_VERSION);
}

void fork_voice_receive_audio(struct Packet* p) {
    u8 globalIndex = UNKNOWN_GLOBAL_INDEX;
    u8 encoded[FV_FRAME];
    packet_read(p, &globalIndex, sizeof(globalIndex));
    packet_read(p, encoded, sizeof(encoded));
    if (p->error || globalIndex >= MAX_PLAYERS || packet_spoofed(p, globalIndex) || !fv_on()) {
        return;
    }
    sCapable[globalIndex] = true;

    struct FvQueue* queue = &sQueues[globalIndex];
    u32 write = atomic_load(&queue->write);
    u32 read = atomic_load(&queue->read);
    // (full: the sound output isn't taking anything; what comes now is dropped, not what waits)
    if (write - read > FV_QUEUE - FV_FRAME) {
        return;
    }
    for (u32 i = 0; i < FV_FRAME; i++) {
        queue->samples[(write + i) % FV_QUEUE] = fv_decode(encoded[i]);
    }
    atomic_store(&queue->write, write + FV_FRAME);
}

// The game's sound (32 kHz stereo, 16 bit) on its way to the sound card. Answers the same sound when
// nobody is talking, otherwise a copy with the voices in it.
const uint8_t* fork_voice_mix(const uint8_t* buffer, size_t length) {
    if (buffer == NULL || length == 0 || length > FV_MIX_BYTES || (length % 4) != 0 ||
        !fv_on() || configForkVoiceVolume == 0) {
        return buffer;
    }
    bool talking = false;
    for (u32 i = 0; i < MAX_PLAYERS; i++) {
        if (atomic_load(&sQueues[i].write) != atomic_load(&sQueues[i].read)) {
            talking = true;
            break;
        }
    }
    if (!talking) {
        return buffer;
    }

    memcpy(sMixed, buffer, length);
    s16* out = (s16*)sMixed;
    const size_t frames = length / 4;
    const s32 volume = configForkVoiceVolume > 200 ? 200 : (s32)configForkVoiceVolume;
    for (u32 i = 0; i < MAX_PLAYERS; i++) {
        struct FvQueue* queue = &sQueues[i];
        u32 read = atomic_load(&queue->read);
        const u32 write = atomic_load(&queue->write);
        // One voice sample lasts two frames of the game's sound (16 kHz in 32 kHz).
        for (size_t frame = 0; frame < frames && read != write; frame++) {
            const s32 voice = queue->samples[read % FV_QUEUE] * volume / 100;
            for (u32 channel = 0; channel < 2; channel++) {
                s32 sum = out[frame * 2 + channel] + voice;
                if (sum > 32767) { sum = 32767; }
                if (sum < -32768) { sum = -32768; }
                out[frame * 2 + channel] = (s16)sum;
            }
            if (frame & 1) { read++; }
        }
        atomic_store(&queue->read, read);
    }
    return sMixed;
}
"""


def voice_chat_flat(t, base):
    """The flat builds' end of the VR builds' voice chat."""
    for name, text in (("src/pc/network/fork_voice.h", FORK_VOICE_H), ("src/pc/network/fork_voice.c", FORK_VOICE_C)):
        if t.exists(name):
            raise Problem(name + " exists already")
        t.write(name, text, False)
        t.log.append(name)

    f = "src/pc/network/network.c"
    t.before(f, "    network_rehost_update();\n    network_reconnect_update();\n",
             "    fork_voice_update(); // [gore fork]\n")
    t.after(f, '#include "network.h"\n', '#include "fork_voice.h" // [gore fork]\n')

    f = "src/pc/audio/audio_sdl.c"
    t.replace(f, "        SDL_QueueAudio(dev, buf, len);\n",
              "        SDL_QueueAudio(dev, fork_voice_mix(buf, len), len); // [gore fork] (with the voices in it)\n")
    wiiu = "        const uint8_t *queue_buf = audio_prepare_wiiu_pcm(buf, len);\n"
    if wiiu in t.read(f)[0]:
        t.replace(f, wiiu,
                  "        const uint8_t *queue_buf = audio_prepare_wiiu_pcm(fork_voice_mix(buf, len), len); // [gore fork]\n")
    t.after(f, '#include "audio_api.h"\n', '#include "pc/network/fork_voice.h" // [gore fork]\n')

    xbox = "src/pc/audio/audio_xbox360.c"
    if t.exists(xbox):
        t.after(xbox, '#include "audio_api.h"\n', '#include "pc/network/fork_voice.h"\n')
        t.after(xbox, "    if (!open || !buf) return;\n", "    buf = fork_voice_mix(buf, len);\n")

    f = "src/pc/configfile.c"
    t.after(f, "bool         configMuteFocusLoss                  = false;\n",
            "// [gore fork] voice chat: hear the others; the microphone is off until the player turns it on\n"
            "bool         configForkVoice                      = true;\n"
            "bool         configForkVoiceMic                   = false;\n"
            "unsigned int configForkVoiceVolume                = 100; // percent\n")
    t.after(f,
            '    {.name = "mute_focus_loss",                .type = CONFIG_TYPE_BOOL, .boolValue = &configMuteFocusLoss},\n',
            '    {.name = "fork_voice",                     .type = CONFIG_TYPE_BOOL, .boolValue = &configForkVoice},\n'
            '    {.name = "fork_voice_mic",                 .type = CONFIG_TYPE_BOOL, .boolValue = &configForkVoiceMic},\n'
            '    {.name = "fork_voice_volume",              .type = CONFIG_TYPE_UINT, .uintValue = &configForkVoiceVolume},\n')
    t.after("src/pc/configfile.h", "extern bool         configMuteFocusLoss;\n",
            "extern bool         configForkVoice;       // [gore fork]\n"
            "extern bool         configForkVoiceMic;\n"
            "extern unsigned int configForkVoiceVolume;\n")

    t.before("src/pc/djui/djui_panel_sound.c",
             "        djui_button_create(body, DLANG(MENU, BACK), DJUI_BUTTON_STYLE_BACK, djui_panel_menu_back);\n",
             "        // [gore fork]\n"
             '        djui_checkbox_create(body, "Voice chat (hear the others)", &configForkVoice, NULL);\n'
             '        djui_checkbox_create(body, "Microphone on (the others hear you)", &configForkVoiceMic, NULL);\n'
             '        djui_slider_create(body, "Voice volume", &configForkVoiceVolume, 0, 200, NULL);\n'
             "\n")

    if base == "android":
        t.replace("platform/app/src/main/AndroidManifest.xml",
                  '    <!-- <uses-permission android:name="android.permission.RECORD_AUDIO" /> -->\n',
                  '    <uses-permission android:name="android.permission.RECORD_AUDIO" /> <!-- [gore fork] voice chat -->\n')


def vr_for_everybody(t, base):
    if base != "vr":
        f = "src/pc/network/packets/packet.h"
        t.after(f, "    PACKET_COMMAND,\n    PACKET_MODERATOR,\n",
                "\n"
                "    // [gore fork] Packets of the VR builds, which share this build's lobbies. Same numbers as there.\n"
                "    PACKET_VR_PHYSICAL_HIT,\n"
                "    PACKET_VR_VOICE_CAPABILITY,\n"
                "    PACKET_VR_VOICE_AUDIO,\n")
        f = "src/pc/network/packets/packet.c"
        t.before(f, '        default: LOG_ERROR("received unknown packet: %d", p->buffer[0]);\n',
                 "        // [gore fork] From a VR build. The hit isn't sent in this game (hits come through the\n"
                 "        // built-in mod); voice is, and fork_voice.c is this build's end of it.\n"
                 "        case PACKET_VR_PHYSICAL_HIT:          break;\n"
                 "        case PACKET_VR_VOICE_CAPABILITY:      fork_voice_receive_capability(p);           break;\n"
                 "        case PACKET_VR_VOICE_AUDIO:           fork_voice_receive_audio(p);                break;\n")
        t.after(f, '#include "pc/debuglog.h"\n', '#include "pc/network/fork_voice.h" // [gore fork]\n')
        voice_chat_flat(t, base)
        return

    f = "src/pc/network/coopnet/coopnet.c"
    t.replace(f,
              "bool ns_coopnet_is_standard_public_session(void) {\n"
              "    return gNetworkType != NT_NONE &&\n"
              "        sActiveLobbyChannelValid &&\n"
              "        sActiveLobbyChannel == COOPNET_LOBBY_STANDARD_PUBLIC;\n"
              "}\n",
              "bool ns_coopnet_is_standard_public_session(void) {\n"
              "    // [gore fork] There are no lobbies of the official game here: nothing has to be held back.\n"
              "    return false;\n"
              "}\n")
    t.replace(f,
              "bool ns_coopnet_vr_public_session(void) {\n"
              "    return gNetworkType != NT_NONE &&\n"
              "        sActiveLobbyChannelValid &&\n"
              "        sActiveLobbyChannel == COOPNET_LOBBY_VR_PUBLIC;\n"
              "}\n",
              "bool ns_coopnet_vr_public_session(void) {\n"
              "    // [gore fork] No lobby is for VR builds only: flat players are in the same ones. (This is what\n"
              "    // decided whether joining needs the VR handshake, and whether a game without it is kicked.)\n"
              "    return false;\n"
              "}\n")

    f = "src/pc/djui/djui_panel_join.c"
    t.replace(f,
              "static void djui_panel_join_public_lobbies(struct DjuiBase* caller) {\n"
              "    djui_panel_confirm_create(\n"
              "        caller,\n"
              '        "Public Lobby Warning",\n'
              '        "This is technically an unauthorized build of SM64 Co-op DX. "\n'
              '        "There are movement advantages in our build that could be considered cheating. "\n'
              '        "Cheats are disabled, and power-ups are disabled as well in public lobbies. "\n'
              '        "Play at your own risk.",\n'
              "        djui_panel_join_public_lobbies_acknowledged\n"
              "    );\n"
              "}\n"
              "\n"
              "static void djui_panel_join_vr_public_lobbies(struct DjuiBase* caller) {\n"
              "    djui_panel_join_lobbies_create(caller, \"\", COOPNET_LOBBY_VR_PUBLIC);\n"
              "}\n",
              "// [gore fork] One list of public lobbies, with nothing switched off in it: no warning to click away\n"
              "// and no second \"VR\" list.\n"
              "static void djui_panel_join_public_lobbies(struct DjuiBase* caller) {\n"
              "    djui_panel_join_public_lobbies_acknowledged(caller);\n"
              "}\n")
    t.replace(f,
              '        djui_button_create(body, "Public VR Lobbies", DJUI_BUTTON_STYLE_NORMAL, '
              "djui_panel_join_vr_public_lobbies);\n",
              "")
    f = "src/pc/djui/djui_panel_join_lobbies.c"
    t.replace(f, "        if (!private && channel == COOPNET_LOBBY_STANDARD_PUBLIC) {\n",
              "        if (false && !private && channel == COOPNET_LOBBY_STANDARD_PUBLIC) { // [gore fork] not true here\n")
    f = "src/pc/djui/djui_panel_host.c"
    t.before(f,
             "        djui_panel_host_update_coopnet_fields();\n"
             "#endif\n"
             "\n"
             "        struct DjuiRect* rect2 = djui_rect_container_create(body, 32);\n",
             "        // [gore fork] \"VR Public\" or \"Standard Public\" is the same lobby here: nothing to choose.\n"
             "        djui_base_set_visible(&sRectPublicChannel->base, false);\n")

    f = "src/game/vr_hand_interaction.h"
    t.before(f, "#endif // VR_HAND_INTERACTION_H\n", VR_BRIDGE_H)
    f = "src/game/vr_hand_interaction.c"
    t.after(f, '#include "pc/vr/vr.h"\n', VR_BRIDGE_REDIRECT)
    text, crlf = t.read(f)
    for needed, count in (("ns_coopnet_vr_public_session()", 3), ("network_send_vr_player_hit(", 3),
                          ("sVrFireballProjectiles[VR_FIREBALL_PROJECTILE_COUNT]", 1),
                          ("sVrHammerProjectiles[VR_HAMMER_PROJECTILE_COUNT]", 1),
                          ("static struct Object* sVrFireballChargeObject = NULL;", 1),
                          ("static struct Object* sVrHammerChargeObject = NULL;", 1),
                          ("static struct Object* sVrRasenganObject = NULL;", 1),
                          ("static struct Object* sVrRasenShurikenProjectile = NULL;", 1),
                          ("static struct Object* sVrFireFlowerPickups[VR_FIRE_FLOWER_PICKUP_COUNT]", 1),
                          ("static struct Object* sVrHammerSuitPickupObject = NULL;", 1),
                          ("static struct Object* sVrSonicShoesPickupObject = NULL;", 1),
                          ("static struct Object* sVrBigHandsPickupObject = NULL;", 1)):
        if text.count(needed) != count:
            raise Problem("%s: expected %d of %r, found %d" % (f, count, needed, text.count(needed)))
    if not text.endswith("}\n"):
        raise Problem(f + ": doesn't end where a function ends")
    t.write(f, text + VR_BRIDGE_C, crlf)
    t.log.append(f)
    for f2, needed in (("src/game/vr_propeller.inc.h", "static struct Object* sVrPropellerPickupObject;"),
                       ("src/game/vr_power_star.inc.h", "static struct Object* sVrPowerStarPickup;")):
        text, _ = t.read(f2)
        if text.count(needed) != 1:
            raise Problem("%s: expected 1 of %r, found %d" % (f2, needed, text.count(needed)))

    t.replace(f,
              "    pickup->oVelY = 0.0f;\n"
              "    obj_update_gfx_pos_and_angle(pickup);\n"
              "    return true;\n"
              "}\n"
              "\n"
              "bool vr_special_moves_hammer_suit_active(void) {\n",
              "    pickup->oVelY = 0.0f;\n"
              "    obj_update_gfx_pos_and_angle(pickup);\n"
              "    // [gore fork] so that the others see it too\n"
              "    vr_net_bridge_track_cap(pickup,\n"
              "        cap == VR_CHEAT_SPAWN_WING_CAP ? VR_NET_EFFECT_CAP_WING :\n"
              "        (cap == VR_CHEAT_SPAWN_METAL_CAP ? VR_NET_EFFECT_CAP_METAL : VR_NET_EFFECT_CAP_VANISH));\n"
              "    return true;\n"
              "}\n"
              "\n"
              "bool vr_special_moves_hammer_suit_active(void) {\n")

    f = "src/game/rendering_graph_node.c"
    text, crlf = t.read(f)
    for needed in ("static bool sVrPaintingExitHatWingCap = false;", "static u32 sVrHeldCapFlags;",
                   '#include "vr_hand_interaction.h"'):
        if text.count(needed) != 1:
            raise Problem("%s: expected 1 of %r, found %d" % (f, needed, text.count(needed)))
    if not text.endswith("}\n"):
        raise Problem(f + ": doesn't end where a function ends")
    for needed in ("static struct GraphNodeCamera* sCameraNode = NULL;",
                   "static void vr_build_game_camera_matrix(",
                   "static void vr_apply_roomscale_tracking_compensation("):
        if text.count(needed) != 1:
            raise Problem("%s: expected 1 of %r, found %d" % (f, needed, text.count(needed)))
    t.write(f, text + VR_BRIDGE_HAT_C + VR_HEAD_C + VR_DEATH_CAMERA_C, crlf)
    t.log.append(f)

    t.replace(f, "*config_vr_camera_height_for_character(", "fork_vr_camera_height(", count=3)
    t.before(f, "static bool vr_build_head_rotation_matrix(Mat4 matrix) {\n", VR_EYES_C)
    t.replace(f,
              "    return sVrTorsoAlignment + previousHeightOffset;\n",
              "    return previousHeightOffset; // [gore fork] (was: sVrTorsoAlignment + previousHeightOffset)\n")
    t.before(f,
             "    // Animated part translations are local to their parent bone. Applying\n",
             "    if (!previousFrame && gCurMarioBodyState->currAnimPart == MARIO_ANIM_PART_TORSO) { // [gore fork]\n"
             "        sForkVrTorsoLift = heightOffset;\n"
             "        sForkVrTorsoLiftFrame = gGlobalTimer;\n"
             "    }\n"
             "\n")
    f2 = "src/pc/configfile.h"
    t.replace(f2,
              "#define VR_CAMERA_HEIGHT_DEFAULT_MARIO 160U\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_LUIGI \\\n"
              "    (VR_HAT_TOP_HEIGHT_LUIGI - VR_CAMERA_HAT_INSET)\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_TOAD \\\n"
              "    (VR_HAT_TOP_HEIGHT_TOAD - VR_CAMERA_HAT_INSET)\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_WALUIGI \\\n"
              "    (VR_HAT_TOP_HEIGHT_WALUIGI - VR_CAMERA_HAT_INSET)\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_WARIO \\\n"
              "    (VR_HAT_TOP_HEIGHT_WARIO - VR_CAMERA_HAT_INSET)\n",
              "// [gore fork] 100: the eyes of the character he plays (see fork_vr_camera_height)\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_MARIO 100U\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_LUIGI 100U\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_TOAD 100U\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_WALUIGI 100U\n"
              "#define VR_CAMERA_HEIGHT_DEFAULT_WARIO 100U\n")
    f2 = "src/pc/configfile.c"
    t.after(f2,
            "        sConfigVrCameraHeightVersion = 9;\n"
            "    }\n",
            "\n"
            "    if (sConfigVrCameraHeightVersion < 10) {\n"
            "        // [gore fork] The number is no longer a height above his feet: 100 is his character's eyes.\n"
            "        for (unsigned int character = 0; character < CT_MAX; character++) {\n"
            "            *config_vr_camera_height_for_character(character) =\n"
            "                config_vr_camera_default_height_for_character(character);\n"
            "        }\n"
            "        sConfigVrCameraHeightVersion = 10;\n"
            "    }\n")
    f2 = "src/pc/djui/djui_panel_vr.c"
    t.replace(f2,
              '            "First Person Height",\n',
              '            "First Person Height (100 = eye level)", // [gore fork]\n')

    t.replace(f,
              "void vr_handle_camera_mode_change(void) {\n"
              "    const unsigned int cameraMode =\n",
              "void vr_handle_camera_mode_change(void) {\n"
              "    fork_vr_death_camera_tick(); // [gore fork]\n"
              "    const unsigned int cameraMode =\n")
    f = "src/pc/configfile.c"
    t.replace(f,
              "        case CONFIG_TYPE_UINT:\n"
              '            fprintf(file, "%s %u\\n", option->name, *option->uintValue);\n',
              "        case CONFIG_TYPE_UINT:\n"
              "            // [gore fork] (see fork_vr_death_camera in rendering_graph_node.c)\n"
              '            fprintf(file, "%s %u\\n", option->name,\n'
              "                    option->uintValue == &configVrCameraMode ? fork_vr_camera_mode_choice()\n"
              "                                                             : *option->uintValue);\n")
    t.before(f, "static void configfile_save_option(FILE *file, const struct ConfigOption *option, bool isSecret) {\n",
             "unsigned int fork_vr_camera_mode_choice(void); // [gore fork]\n\n")

    f = "src/pc/djui/djui_panel_vr.c"
    t.replace(f,
              "    djui_panel_shutdown();\n"
              "    dynos_warp_to_level(level, 1, 1);\n",
              "    djui_panel_shutdown();\n"
              "    vr_net_bridge_push_event(VR_NET_EVENT_LEVEL_SELECT, level); // [gore fork]\n"
              "    dynos_warp_to_level(level, 1, 1);\n")

    f = "src/pc/lua/smlua_functions.c"
    t.after(f, '#include "game/hardcoded.h"\n', '#include "game/vr_hand_interaction.h" // [gore fork]\n')
    t.before(f, "void smlua_bind_functions(void) {\n", VR_BRIDGE_LUA)
    t.after(f, '    smlua_bind_function(L, "return_self", smlua_func_return_self); // compatibility band-aid\n',
            "\n"
            "    // [gore fork]\n"
            '    smlua_bind_function(L, "vr_net_state", smlua_func_vr_net_state);\n'
            '    smlua_bind_function(L, "vr_net_pop_hit", smlua_func_vr_net_pop_hit);\n'
            '    smlua_bind_function(L, "vr_net_pop_event", smlua_func_vr_net_pop_event);\n'
            '    smlua_bind_function(L, "vr_net_head", smlua_func_vr_net_head);\n'
            '    smlua_bind_function(L, "vr_net_hands", smlua_func_vr_net_hands);\n'
            '    smlua_bind_function(L, "vr_set_death_camera", smlua_func_vr_set_death_camera);\n')



VR_BODY_H = """\

// [gore fork] A VR player's Mario, as everybody else sees him (at the end of rendering_graph_node.c).
void fork_vr_remote_pose(s32 playerIndex, u8 hands, Vec3f left, Vec3f right, f32 handScale,
                         s16 headYaw, s16 headPitch, s16 headRoll, const f32* turns);
void fork_vr_remote_pose_clear(s32 playerIndex);
bool fork_vr_remote_head(s32 playerIndex, Mat4 joint, Vec3s rotation);
s32 fork_vr_remote_hand_case(struct MarioBodyState* bodyState, s32 parameter);
void fork_vr_remote_body(Vec3s translation, Mat4 matrix, bool previousFrame);

"""

VR_BODY_C = """\
#include "mario_misc.h"
#include "object_list_processor.h"

// =========================================================================================================
// [gore fork] A VR player's Mario, as everybody else sees him
//
// A VR player's game knows where his hands and his head are; the game sends none of that. The built-in mod
// does (vrsync.lua), and on every game that receives it, it says here each frame what it knows about each
// VR player: vr_remote_pose(). While his Mario is drawn,
//   - his arms reach for where his hands are (the upper arm and the forearm are turned, and made longer
//     when a hand is further away than Mario's short arms reach),
//   - his hands, Mario's own, are at exactly those places, open or closed as his are, and turned the way
//     he holds them (as his own game shows him his gloves),
//   - his head looks where his headset looks (as far as a neck goes).
// A hand's place is given from the joint between his torso and his head (where his head sits on his
// shoulders), along the axes of the level. The VR game measures it from the player's eyes, and the mod adds
// how far Mario's eyes are above that joint: the others see his hands where he sees them from his own eyes,
// whatever height his VR camera is at.
//
// Only for the other players' Marios: this player's own is the VR game's business. Nothing here is saved or
// sent. A pose the mod stops repeating is dropped after FORK_VR_POSE_FRAMES frames.
// =========================================================================================================
#define FORK_VR_POSE_FRAMES 3      // game frames
#define FORK_VR_ARM_STRETCH 3.0f   // how much longer than Mario's own an arm may get before the bend is gone
#define FORK_VR_HAND_REACH 260.0f  // a hand further from the joint than this is brought back to it
#define FORK_VR_WRIST_BACK 50.0f   // from the place a hand is tracked at (the middle of the fist) back to its
                                   // wrist, where the hand's model starts: in the model's own units

enum ForkVrHands {
    FORK_VR_LEFT_VALID   = 1 << 0,
    FORK_VR_LEFT_CLOSED  = 1 << 1,
    FORK_VR_RIGHT_VALID  = 1 << 2,
    FORK_VR_RIGHT_CLOSED = 1 << 3,
    FORK_VR_HEAD_VALID   = 1 << 4,
    FORK_VR_LEFT_TURNED  = 1 << 5, // the mod said how this hand is turned
    FORK_VR_RIGHT_TURNED = 1 << 6,
    FORK_VR_HEAD_RELATIVE = 1 << 7, // the head's yaw is from the way his Mario faces, not in the level
};

// how far a head turns from the way the body faces: to a side, up and down, an ear to a shoulder
#define FORK_VR_HEAD_YAW   0x3555 // 75 degrees
#define FORK_VR_HEAD_PITCH 0x2AAA // 60
#define FORK_VR_HEAD_ROLL  0x1C71 // 40

struct ForkVrPose {
    // what the mod said
    bool used;
    u32 frame;               // gGlobalTimer of the last time
    u8 hands;                // enum ForkVrHands
    f32 handScale;           // the Big Hands power-up
    Vec3f hand[2][2];        // [left, right][now, the frame before]: from the joint
    f32 turn[2][2][2][3];    // [left, right][now, before][the way the fingers point, the way the thumb does]
    Vec3s head;              // yaw (as Mario's: in the level, or with FORK_VR_HEAD_RELATIVE from the way his
                             // Mario faces), pitch (up), roll (his head to his left shoulder)
    // what drawing him found: [now, the frame before], for the two matrices the game keeps of everything
    u32 neckFrame[2];
    Vec3f neck[2];
    u32 armFrame[2][2];      // [hand][...]: the frame this arm was last turned in (the forearm and the hand follow)
    Vec3f wrist[2][2];       // [hand][...]: where the hand's model starts, in the level
    f32 scale[2][2];         // [hand][...]: the size of the model in the level
    f32 basis[2][2][3][3];   // [hand][...]: along the forearm, up, to the side (as the camera sees them)
    // the model's own measures, read off its skeleton as it goes by (0: not seen yet)
    f32 upperLength[2];
    f32 foreLength[2];
};

static struct ForkVrPose sForkVrPoses[MAX_PLAYERS];

static struct ForkVrPose* fork_vr_pose_of(s32 playerIndex) {
    if (playerIndex <= 0 || playerIndex >= MAX_PLAYERS) {
        return NULL;
    }
    struct ForkVrPose* pose = &sForkVrPoses[playerIndex];
    if (!pose->used || (u32)(gGlobalTimer - pose->frame) > FORK_VR_POSE_FRAMES) {
        return NULL;
    }
    return pose;
}

static void fork_vr_limit_reach(Vec3f offset) {
    const f32 length = sqrtf(offset[0] * offset[0] + offset[1] * offset[1] + offset[2] * offset[2]);
    if (!isfinite(length)) {
        offset[0] = offset[1] = offset[2] = 0.0f;
    } else if (length > FORK_VR_HAND_REACH) {
        const f32 shorter = FORK_VR_HAND_REACH / length;
        offset[0] *= shorter;
        offset[1] *= shorter;
        offset[2] *= shorter;
    }
}

// Makes two directions one unit long and square to each other (the first one stays where it points).
static bool fork_vr_square(f32 first[3], f32 second[3]) {
    f32 length = sqrtf(first[0] * first[0] + first[1] * first[1] + first[2] * first[2]);
    if (!isfinite(length) || length <= 0.01f) {
        return false;
    }
    for (u32 axis = 0; axis < 3; axis++) { first[axis] /= length; }
    const f32 along = second[0] * first[0] + second[1] * first[1] + second[2] * first[2];
    for (u32 axis = 0; axis < 3; axis++) { second[axis] -= first[axis] * along; }
    length = sqrtf(second[0] * second[0] + second[1] * second[1] + second[2] * second[2]);
    if (!isfinite(length) || length <= 0.01f) {
        return false;
    }
    for (u32 axis = 0; axis < 3; axis++) { second[axis] /= length; }
    return true;
}

// `turns`: twelve numbers or NULL. For the left hand and then the right: the way its fingers point (x, y, z)
// and the way its thumb points when the hand is flat (x, y, z), in the level.
void fork_vr_remote_pose(s32 playerIndex, u8 hands, Vec3f left, Vec3f right, f32 handScale,
                         s16 headYaw, s16 headPitch, s16 headRoll, const f32* turns) {
    if (playerIndex <= 0 || playerIndex >= MAX_PLAYERS) {
        return;
    }
    struct ForkVrPose* pose = &sForkVrPoses[playerIndex];
    const bool again = pose->used && pose->frame == gGlobalTimer;
    const bool continuous = pose->used && (again || pose->frame + 1 == gGlobalTimer);
    const u8 before = continuous ? pose->hands : 0;

    Vec3f now[2];
    for (u32 axis = 0; axis < 3; axis++) {
        now[0][axis] = left != NULL ? left[axis] : 0.0f;
        now[1][axis] = right != NULL ? right[axis] : 0.0f;
    }
    for (u32 hand = 0; hand < 2; hand++) {
        fork_vr_limit_reach(now[hand]);
        const u8 valid = hand == 0 ? FORK_VR_LEFT_VALID : FORK_VR_RIGHT_VALID;
        for (u32 axis = 0; axis < 3; axis++) {
            if (!again) {
                // (a hand that wasn't there a frame ago starts where it is, it doesn't fly in)
                pose->hand[hand][1][axis] = (before & valid) ? pose->hand[hand][0][axis] : now[hand][axis];
            }
            pose->hand[hand][0][axis] = now[hand][axis];
        }

        // how it is turned
        const u8 turned = hand == 0 ? FORK_VR_LEFT_TURNED : FORK_VR_RIGHT_TURNED;
        f32 turn[2][3];
        bool known = turns != NULL && (hands & valid) && (hands & turned);
        if (known) {
            for (u32 i = 0; i < 6; i++) { turn[i / 3][i % 3] = turns[hand * 6 + i]; }
            known = fork_vr_square(turn[0], turn[1]);
        }
        if (!known) {
            hands &= (u8) ~turned;
            continue;
        }
        for (u32 which = 0; which < 2; which++) {
            for (u32 axis = 0; axis < 3; axis++) {
                if (!again) {
                    pose->turn[hand][1][which][axis] = (before & turned) ? pose->turn[hand][0][which][axis]
                                                                         : turn[which][axis];
                }
                pose->turn[hand][0][which][axis] = turn[which][axis];
            }
        }
    }
    pose->hands = hands;
    pose->handScale = (isfinite(handScale) && handScale > 0.1f && handScale < 20.0f) ? handScale : 1.0f;
    pose->head[0] = headYaw;
    pose->head[1] = headPitch;
    pose->head[2] = headRoll;
    if (pose->used && !continuous) {
        // (back after a pause, or a player who took this place in the lobby: nothing kept from before)
        for (u32 hand = 0; hand < 2; hand++) {
            pose->upperLength[hand] = 0.0f;
            pose->foreLength[hand] = 0.0f;
        }
    }
    pose->frame = gGlobalTimer;
    pose->used = true;
}

void fork_vr_remote_pose_clear(s32 playerIndex) {
    if (playerIndex > 0 && playerIndex < MAX_PLAYERS) {
        sForkVrPoses[playerIndex].used = false;
    }
}

static s16 fork_vr_angle(f32 radians, s32 limit) {
    if (!isfinite(radians)) {
        return 0;
    }
    s32 angle = (s32)(radians * (32768.0f / 3.14159265f));
    if (angle > limit) { angle = limit; }
    if (angle < -limit) { angle = -limit; }
    return (s16) angle;
}

// The head: asked by geo_mario_head_rotation, which sets the angles of the node that turns Mario's head.
// `joint` is where that node hangs, as the camera sees it: its first axis is up along his spine, its second
// the way his chest faces, its third to his left. The node turns about the third first (a positive angle
// nods), then about the first (to his left), then about the second (lifts his left ear).
// The angles are worked out from where the headset looks in the level and where that joint is right now, so
// the head keeps looking the same way while the body under it runs, leans or lies down.
bool fork_vr_remote_head(s32 playerIndex, Mat4 joint, Vec3s rotation) {
    struct ForkVrPose* pose = fork_vr_pose_of(playerIndex);
    if (pose == NULL || !(pose->hands & FORK_VR_HEAD_VALID) || joint == NULL || rotation == NULL ||
        gCurGraphNodeCamera == NULL || gCurGraphNodeCamera->matrixPtr == NULL) {
        return false;
    }
    // (his Mario, not his reflection in the mirror room)
    if (gMarioObjects[playerIndex] == NULL || gCurGraphNodeObject != &gMarioObjects[playerIndex]->header.gfx) {
        return false;
    }
    Mat4* camera = gCurGraphNodeCamera->matrixPtr;

    // the joint's three axes, in the level
    f32 parent[3][3];
    for (u32 b = 0; b < 3; b++) {
        f32 length = 0.0f;
        for (u32 i = 0; i < 3; i++) {
            parent[b][i] = joint[b][0] * (*camera)[i][0] + joint[b][1] * (*camera)[i][1] +
                           joint[b][2] * (*camera)[i][2];
            length += parent[b][i] * parent[b][i];
        }
        length = sqrtf(length);
        if (!isfinite(length) || length <= 0.0001f) {
            return false;
        }
        for (u32 i = 0; i < 3; i++) { parent[b][i] /= length; }
    }

    // the head's three axes as the headset has them, in the level: up, forward, to his left
    s16 yaw = pose->head[0];
    if (pose->hands & FORK_VR_HEAD_RELATIVE) {
        // (third person: that far from the way his Mario is drawn facing)
        yaw = (s16)(yaw + gMarioObjects[playerIndex]->header.gfx.angle[1]);
    }
    const f32 sinYaw = sins(yaw), cosYaw = coss(yaw);
    const f32 sinPitch = sins(pose->head[1]), cosPitch = coss(pose->head[1]);
    const f32 sinRoll = sins(pose->head[2]), cosRoll = coss(pose->head[2]);
    const f32 forward[3] = { sinYaw * cosPitch, sinPitch, cosYaw * cosPitch };
    const f32 levelLeft[3] = { cosYaw, 0.0f, -sinYaw };
    const f32 levelUp[3] = {
        forward[1] * levelLeft[2] - forward[2] * levelLeft[1],
        forward[2] * levelLeft[0] - forward[0] * levelLeft[2],
        forward[0] * levelLeft[1] - forward[1] * levelLeft[0],
    };
    f32 wanted[3][3];
    for (u32 i = 0; i < 3; i++) {
        wanted[0][i] = levelUp[i] * cosRoll + levelLeft[i] * sinRoll;
        wanted[1][i] = forward[i];
    }
    wanted[2][0] = wanted[0][1] * forward[2] - wanted[0][2] * forward[1];
    wanted[2][1] = wanted[0][2] * forward[0] - wanted[0][0] * forward[2];
    wanted[2][2] = wanted[0][0] * forward[1] - wanted[0][1] * forward[0];

    // the same, measured along the joint's axes: what the node's matrix has to be
    f32 turn[3][3];
    for (u32 a = 0; a < 3; a++) {
        for (u32 b = 0; b < 3; b++) {
            turn[a][b] = wanted[a][0] * parent[b][0] + wanted[a][1] * parent[b][1] + wanted[a][2] * parent[b][2];
        }
    }

    if (turn[1][1] > 0.2f && turn[2][2] > 0.2f) {
        // (the angles mtxf_rotate_zxy_and_translate makes exactly this matrix of)
        f32 sinX = -turn[2][1];
        if (sinX > 1.0f) { sinX = 1.0f; }
        if (sinX < -1.0f) { sinX = -1.0f; }
        rotation[0] = fork_vr_angle(asinf(sinX), FORK_VR_HEAD_YAW);
        rotation[1] = fork_vr_angle(atan2f(turn[2][0], turn[2][2]), FORK_VR_HEAD_ROLL);
        rotation[2] = fork_vr_angle(atan2f(turn[0][1], turn[1][1]), FORK_VR_HEAD_PITCH);
    } else {
        // He looks past his shoulder, or his body lies the other way: as far to that side as a head goes.
        f32 up = turn[1][0];
        if (up > 1.0f) { up = 1.0f; }
        if (up < -1.0f) { up = -1.0f; }
        rotation[0] = fork_vr_angle(atan2f(turn[1][2], turn[1][1]), FORK_VR_HEAD_YAW);
        rotation[1] = 0;
        rotation[2] = fork_vr_angle(-asinf(up), FORK_VR_HEAD_PITCH);
    }
    return true;
}

// The hands, open or closed: asked by geo_switch_mario_hand. `parameter` is the switch node's: 0 is the
// right hand, anything else the left. Answers the case to draw (0: fist, 1: open), or -1 for "as always".
s32 fork_vr_remote_hand_case(struct MarioBodyState* bodyState, s32 parameter) {
    if (bodyState == NULL) {
        return -1;
    }
    struct ForkVrPose* pose = fork_vr_pose_of((s32)(bodyState - gBodyStates));
    if (pose == NULL) {
        return -1;
    }
    const bool right = parameter == 0;
    if (!(pose->hands & (right ? FORK_VR_RIGHT_VALID : FORK_VR_LEFT_VALID))) {
        return -1;
    }
    return (pose->hands & (right ? FORK_VR_RIGHT_CLOSED : FORK_VR_LEFT_CLOSED)) ? 0 : 1;
}

static f32 fork_vr_bone_length(Vec3s translation) {
    const f32 x = translation[0];
    const f32 y = translation[1];
    const f32 z = translation[2];
    const f32 length = sqrtf(x * x + y * y + z * z);
    return (length >= 5.0f && length <= 600.0f) ? length : 0.0f;
}

// The size the model is drawn at, off a matrix nothing has stretched yet.
static f32 fork_vr_matrix_scale(Mat4 matrix) {
    const f32 y = sqrtf(matrix[1][0] * matrix[1][0] + matrix[1][1] * matrix[1][1] + matrix[1][2] * matrix[1][2]);
    const f32 z = sqrtf(matrix[2][0] * matrix[2][0] + matrix[2][1] * matrix[2][1] + matrix[2][2] * matrix[2][2]);
    const f32 scale = (y + z) * 0.5f;
    return (isfinite(scale) && scale > 0.001f) ? scale : 0.001f;
}

// Where the elbow is, for a shoulder and a hand. Inside Mario's own reach his arm keeps its measures and
// bends; further out both halves get longer by the same factor, and a little bend stays. The elbow points
// down and away from the body. (The VR fork's own answer for the player's own arms, vr_calculate_basic_arm_
// ik_elbow, with the joint between head and torso where that has the headset.)
static bool fork_vr_elbow(u32 hand, Vec3f shoulder, Vec3f target, Vec3f neck, f32 upperLength, f32 lowerLength,
                          Vec3f elbow) {
    Vec3f toHand = { target[0] - shoulder[0], target[1] - shoulder[1], target[2] - shoulder[2] };
    const f32 distance = sqrtf(toHand[0] * toHand[0] + toHand[1] * toHand[1] + toHand[2] * toHand[2]);
    if (!isfinite(distance) || distance <= 0.001f) {
        return false;
    }
    for (u32 axis = 0; axis < 3; axis++) { toHand[axis] /= distance; }

    const f32 reach = upperLength + lowerLength;
    f32 stretch = distance / MAX(reach * 0.98f, 0.001f);
    if (stretch < 1.0f) { stretch = 1.0f; }
    if (stretch > FORK_VR_ARM_STRETCH) { stretch = FORK_VR_ARM_STRETCH; }
    upperLength *= stretch;
    lowerLength *= stretch;

    f32 solve = distance;
    const f32 nearest = fabsf(upperLength - lowerLength) + 0.001f;
    const f32 furthest = upperLength + lowerLength - 0.001f;
    if (solve < nearest) { solve = nearest; }
    if (solve > furthest) { solve = furthest; }
    const f32 along = (upperLength * upperLength - lowerLength * lowerLength + solve * solve) / (2.0f * solve);
    const f32 bend = sqrtf(MAX(upperLength * upperLength - along * along, 0.0f));

    Vec3f outward = { shoulder[0] - neck[0], 0.0f, shoulder[2] - neck[2] };
    f32 length = sqrtf(outward[0] * outward[0] + outward[2] * outward[2]);
    if (length > 0.001f) {
        outward[0] /= length;
        outward[2] /= length;
    } else {
        outward[0] = hand == 0 ? 1.0f : -1.0f;
        outward[2] = 0.0f;
    }

    Vec3f bendDirection = { outward[0] * 0.35f, -1.0f, outward[2] * 0.35f };
    const f32 bendAlong = bendDirection[0] * toHand[0] + bendDirection[1] * toHand[1] + bendDirection[2] * toHand[2];
    for (u32 axis = 0; axis < 3; axis++) { bendDirection[axis] -= toHand[axis] * bendAlong; }
    length = sqrtf(bendDirection[0] * bendDirection[0] + bendDirection[1] * bendDirection[1] +
                   bendDirection[2] * bendDirection[2]);
    if (length <= 0.001f) {
        // (the hand is straight below the shoulder: bend outward)
        bendDirection[0] = toHand[1] * outward[2] - toHand[2] * outward[1];
        bendDirection[1] = toHand[2] * outward[0] - toHand[0] * outward[2];
        bendDirection[2] = toHand[0] * outward[1] - toHand[1] * outward[0];
        length = sqrtf(bendDirection[0] * bendDirection[0] + bendDirection[1] * bendDirection[1] +
                       bendDirection[2] * bendDirection[2]);
    }
    if (length <= 0.001f) {
        return false;
    }
    for (u32 axis = 0; axis < 3; axis++) {
        elbow[axis] = shoulder[axis] + toHand[axis] * along + bendDirection[axis] / length * bend;
    }
    return true;
}

// Turns a part of the arm so that it points from where it is to `target`, and makes it as long as that
// takes. The models' arms lie along their first axis. `matrix` is the part as the camera sees it; what is
// kept of it is where it is. `basis` gets the three directions it ends up with.
static bool fork_vr_point_at(Mat4 matrix, Mat4 camera, Vec3f target, f32 modelLength, f32 scale, f32 basis[3][3]) {
    Vec3f position;
    get_pos_from_transform_mtx(position, matrix, camera);
    const Vec3f toTarget = { target[0] - position[0], target[1] - position[1], target[2] - position[2] };
    const f32 distance = sqrtf(toTarget[0] * toTarget[0] + toTarget[1] * toTarget[1] + toTarget[2] * toTarget[2]);
    if (!isfinite(distance) || distance <= 0.001f || modelLength <= 0.001f) {
        return false;
    }

    // (from the level's axes to the camera's)
    f32 along[3], up[3], side[3];
    for (u32 axis = 0; axis < 3; axis++) {
        along[axis] = (toTarget[0] * camera[0][axis] + toTarget[1] * camera[1][axis] +
                       toTarget[2] * camera[2][axis]) / distance;
        up[axis] = camera[1][axis];
    }
    f32 length = 0.0f;
    for (u32 attempt = 0; attempt < 2; attempt++) {
        side[0] = along[1] * up[2] - along[2] * up[1];
        side[1] = along[2] * up[0] - along[0] * up[2];
        side[2] = along[0] * up[1] - along[1] * up[0];
        length = sqrtf(side[0] * side[0] + side[1] * side[1] + side[2] * side[2]);
        if (length > 0.001f) {
            break;
        }
        // (it points straight up or down: any side will do)
        for (u32 axis = 0; axis < 3; axis++) { up[axis] = camera[2][axis]; }
    }
    if (!isfinite(length) || length <= 0.001f) {
        return false;
    }
    for (u32 axis = 0; axis < 3; axis++) { side[axis] /= length; }
    up[0] = side[1] * along[2] - side[2] * along[1];
    up[1] = side[2] * along[0] - side[0] * along[2];
    up[2] = side[0] * along[1] - side[1] * along[0];

    const f32 stretch = distance / modelLength;
    for (u32 axis = 0; axis < 3; axis++) {
        matrix[0][axis] = along[axis] * stretch;
        matrix[1][axis] = up[axis] * scale;
        matrix[2][axis] = side[axis] * scale;
        basis[0][axis] = along[axis];
        basis[1][axis] = up[axis];
        basis[2][axis] = side[axis];
    }
    return true;
}

// Called by geo_process_animated_part and geo_process_bone for each part of a Mario's skeleton, once with
// the matrix of this frame and once with the one of the frame before (the game draws in between the two).
// `translation` is the part's place on the part before it, as the model has it.
void fork_vr_remote_body(Vec3s translation, Mat4 matrix, bool previousFrame) {
    if (gCurMarioBodyState == NULL || gCurGraphNodeHeldObject != NULL || gCurGraphNodeCamera == NULL ||
        translation == NULL || matrix == NULL) {
        return;
    }
    const s32 playerIndex = (s32)(gCurMarioBodyState - gBodyStates);
    struct ForkVrPose* pose = fork_vr_pose_of(playerIndex);
    if (pose == NULL) {
        return;
    }
    // (his Mario, not his reflection in the mirror room)
    if (gMarioObjects[playerIndex] == NULL || gCurGraphNodeObject != &gMarioObjects[playerIndex]->header.gfx) {
        return;
    }
    Mat4* camera = previousFrame ? gCurGraphNodeCamera->matrixPtrPrev : gCurGraphNodeCamera->matrixPtr;
    if (camera == NULL) {
        return;
    }

    const u32 when = previousFrame ? 1 : 0;
    const s32 part = gCurMarioBodyState->currAnimPart;
    if (part == MARIO_ANIM_PART_HEAD) {
        get_pos_from_transform_mtx(pose->neck[when], matrix, *camera);
        pose->neckFrame[when] = gGlobalTimer;
        return;
    }

    u32 hand;
    switch (part) {
        case MARIO_ANIM_PART_LEFT_ARM:
        case MARIO_ANIM_PART_LEFT_FOREARM:
        case MARIO_ANIM_PART_LEFT_HAND:
            hand = 0;
            break;
        case MARIO_ANIM_PART_RIGHT_ARM:
        case MARIO_ANIM_PART_RIGHT_FOREARM:
        case MARIO_ANIM_PART_RIGHT_HAND:
            hand = 1;
            break;
        default:
            return;
    }

    // The skeleton's measures: a part's place on the part before it is how long that one is. (Mario's:
    // upper arm 65, forearm 60. Whatever model the player wears says its own, a frame before they are used.)
    if (!previousFrame) {
        if (part == MARIO_ANIM_PART_LEFT_FOREARM || part == MARIO_ANIM_PART_RIGHT_FOREARM) {
            pose->upperLength[hand] = fork_vr_bone_length(translation);
        } else if (part == MARIO_ANIM_PART_LEFT_HAND || part == MARIO_ANIM_PART_RIGHT_HAND) {
            pose->foreLength[hand] = fork_vr_bone_length(translation);
        }
    }

    const bool upperArm = part == MARIO_ANIM_PART_LEFT_ARM || part == MARIO_ANIM_PART_RIGHT_ARM;
    if (upperArm) {
        pose->armFrame[hand][when] = gGlobalTimer - 1; // "not turned", until it is
    }
    if (!(pose->hands & (hand == 0 ? FORK_VR_LEFT_VALID : FORK_VR_RIGHT_VALID))) {
        return;
    }
    // (the head comes before the arms in every skeleton made like Mario's; in one where it doesn't, the arms
    // are left as they are)
    if (pose->neckFrame[when] != gGlobalTimer) {
        return;
    }
    const f32 upperLength = pose->upperLength[hand];
    const f32 foreLength = pose->foreLength[hand];
    if (upperLength <= 0.0f || foreLength <= 0.0f) {
        return;
    }
    const bool turned = (pose->hands & (hand == 0 ? FORK_VR_LEFT_TURNED : FORK_VR_RIGHT_TURNED)) != 0;

    if (upperArm) {
        const f32 scale = fork_vr_matrix_scale(matrix);
        // Where the arm has to end: at the wrist. The hand is tracked in its middle, and its model starts at
        // the wrist, so the wrist is that far back the way the fingers come from.
        const f32 back = turned ? FORK_VR_WRIST_BACK * scale * pose->handScale : 0.0f;
        for (u32 axis = 0; axis < 3; axis++) {
            pose->wrist[hand][when][axis] = pose->neck[when][axis] + pose->hand[hand][when][axis] -
                                            (turned ? pose->turn[hand][when][0][axis] * back : 0.0f);
        }
        Vec3f shoulder;
        Vec3f elbow;
        get_pos_from_transform_mtx(shoulder, matrix, *camera);
        if (!fork_vr_elbow(hand, shoulder, pose->wrist[hand][when], pose->neck[when], upperLength * scale,
                           foreLength * scale, elbow)) {
            return;
        }
        if (!fork_vr_point_at(matrix, *camera, elbow, upperLength, scale, pose->basis[hand][when])) {
            return;
        }
        pose->scale[hand][when] = scale;
        pose->armFrame[hand][when] = gGlobalTimer;
        return;
    }

    // The forearm and the hand only follow an upper arm that was turned (in this frame, for this matrix).
    if (pose->armFrame[hand][when] != gGlobalTimer) {
        return;
    }
    const f32 scale = pose->scale[hand][when];
    Vec3f target;
    for (u32 axis = 0; axis < 3; axis++) { target[axis] = pose->wrist[hand][when][axis]; }

    if (part == MARIO_ANIM_PART_LEFT_FOREARM || part == MARIO_ANIM_PART_RIGHT_FOREARM) {
        if (!fork_vr_point_at(matrix, *camera, target, foreLength, scale, pose->basis[hand][when])) {
            pose->armFrame[hand][when] = gGlobalTimer - 1;
        }
        return;
    }

    // The hand: at the end of the forearm, its own size (the forearm's stretch is not for it), times the Big
    // Hands power-up's. The models of Mario's hands have their fingers along the first axis, the thumb on
    // the far side of the second, and the third to the left of a hand held thumb up.
    f32 axes[3][3]; // as the camera sees them
    if (turned) {
        // the way the VR player holds it
        const f32* fingers = pose->turn[hand][when][0];
        const f32* thumb = pose->turn[hand][when][1];
        const f32 level[3][3] = {
            { fingers[0], fingers[1], fingers[2] },
            { -thumb[0], -thumb[1], -thumb[2] },
            { thumb[1] * fingers[2] - thumb[2] * fingers[1],
              thumb[2] * fingers[0] - thumb[0] * fingers[2],
              thumb[0] * fingers[1] - thumb[1] * fingers[0] },
        };
        for (u32 row = 0; row < 3; row++) {
            for (u32 axis = 0; axis < 3; axis++) {
                axes[row][axis] = level[row][0] * (*camera)[0][axis] + level[row][1] * (*camera)[1][axis] +
                                  level[row][2] * (*camera)[2][axis];
            }
        }
    } else {
        // (a VR game that doesn't say: straight on from the forearm, thumb up)
        for (u32 axis = 0; axis < 3; axis++) {
            axes[0][axis] = pose->basis[hand][when][0][axis];
            axes[1][axis] = -pose->basis[hand][when][1][axis];
            axes[2][axis] = -pose->basis[hand][when][2][axis];
        }
    }
    const f32 size = scale * pose->handScale;
    for (u32 row = 0; row < 3; row++) {
        for (u32 axis = 0; axis < 3; axis++) {
            matrix[row][axis] = axes[row][axis] * size;
        }
    }
    for (u32 axis = 0; axis < 3; axis++) {
        matrix[3][axis] = target[0] * (*camera)[0][axis] + target[1] * (*camera)[1][axis] +
                          target[2] * (*camera)[2][axis] + (*camera)[3][axis];
    }
}
"""

VR_BODY_LUA = """\
// [gore fork] What the built-in mod knows about a VR player, for drawing his Mario (see fork_vr_remote_pose
// in rendering_graph_node.c). Every build has this function; a mod that finds it missing runs on a game
// that isn't this one.
//
// vr_remote_pose(playerIndex, hands, lx, ly, lz, rx, ry, rz, handScale, headYaw, headPitch, headRoll
//                [, twelve numbers])
//     each frame, for each VR player. playerIndex: the local one (1 and up). hands: 1 = there is a left
//     hand, 2 = it is closed, 4 and 8 = the same for the right one, 16 = the head angles count, 32 and 64 =
//     the twelve numbers say how the left and the right hand are turned, 128 = headYaw is from the way his
//     Mario faces. A hand's place is from the joint his head sits on, along the level's axes. The head
//     angles are in the level (headYaw without 128). The twelve numbers: for
//     the left hand and then the right, the way its fingers point (x, y, z) and the way its thumb points
//     when the hand is flat (x, y, z), in the level.
// vr_remote_pose(playerIndex)
//     he isn't one any more (it also ends by itself, a few frames after the last call).
static s32 fork_lua_s32(lua_State* L, int index) {
    const lua_Number value = lua_tonumber(L, index);
    if (!(value > -2147483000.0 && value < 2147483000.0)) {
        return 0;
    }
    return (s32) value;
}

int smlua_func_vr_remote_pose(lua_State* L) {
    const s32 playerIndex = fork_lua_s32(L, 1);
    if (lua_gettop(L) < 12) {
        fork_vr_remote_pose_clear(playerIndex);
        return 0;
    }
    Vec3f left = { (f32) lua_tonumber(L, 3), (f32) lua_tonumber(L, 4), (f32) lua_tonumber(L, 5) };
    Vec3f right = { (f32) lua_tonumber(L, 6), (f32) lua_tonumber(L, 7), (f32) lua_tonumber(L, 8) };
    f32 turns[12];
    const bool turned = lua_gettop(L) >= 24;
    for (int i = 0; i < 12; i++) {
        turns[i] = turned ? (f32) lua_tonumber(L, 13 + i) : 0.0f;
    }
    fork_vr_remote_pose(playerIndex, (u8)(fork_lua_s32(L, 2) & 0xFF), left, right, (f32) lua_tonumber(L, 9),
                        (s16) fork_lua_s32(L, 10), (s16) fork_lua_s32(L, 11), (s16) fork_lua_s32(L, 12),
                        turned ? turns : NULL);
    return 0;
}

"""


def vr_punch(t):
    """A VR player's punch hits where his glove is (the VR builds; see PUNCH_BODY_RADIUS)."""
    f = "src/game/vr_hand_interaction.c"
    t.replace(f,
              "    const f32 playerRadius = fmaxf(\n"
              "        fmaxf(object->hitboxRadius, object->hurtboxRadius),\n"
              "        64.0f * modelScale\n"
              "    );\n",
              "    // [gore fork] As big as his Mario is. (Was: the larger of his hitbox and 64, and 225 high.)\n"
              "    (void) fistLength;\n"
              "    const f32 playerRadius = %.1ff * modelScale;\n"
              "    const f32 forkPlayerHeight = object->hitboxHeight > 0.0f ? object->hitboxHeight : 160.0f;\n"
              % PUNCH_BODY_RADIUS)
    t.replace(f,
              "    const f32 playerTop = playerBottom + 225.0f * modelScale;\n"
              "    const f32 collisionRadius = playerRadius + fistRadius;\n",
              "    const f32 playerTop = playerBottom + forkPlayerHeight * modelScale; // [gore fork]\n"
              "    const f32 collisionRadius = playerRadius + fistRadius;\n")
    t.replace(f,
              "        playerTop < sweep->minimum[1] - fistLength ||\n",
              "        playerTop < sweep->minimum[1] - fistRadius || // [gore fork] was: fistLength\n")
    t.replace(f,
              "            y + fistRadius >= playerBottom &&\n"
              "            y + fistRadius - fistLength <= playerTop) {\n",
              "            y + fistRadius >= playerBottom &&\n"
              "            y - fistRadius <= playerTop) { // [gore fork] was: fistRadius - fistLength\n")

    f = "src/pc/configfile.c"
    t.replace(f,
              "unsigned int configVrPunchColliderLength          = 275;\n",
              "unsigned int configVrPunchColliderLength          = %d; // [gore fork] was: 275\n"
              % PUNCH_COLLIDER_LENGTH)
    t.after(f,
            "        if (configVrPunchColliderLength == 250U) {\n"
            "            configVrPunchColliderLength = 275U;\n"
            "        }\n"
            "        sConfigVrInteractionTuningVersion = 3;\n"
            "    }\n",
            "\n"
            "    if (sConfigVrInteractionTuningVersion < 4) {\n"
            "        // [gore fork] The punch is the glove. Only the default that reached below it is changed; a\n"
            "        // length the player set himself stays.\n"
            "        if (configVrPunchColliderLength == 275U) {\n"
            "            configVrPunchColliderLength = %dU;\n"
            "        }\n"
            "        sConfigVrInteractionTuningVersion = 4;\n"
            "    }\n" % PUNCH_COLLIDER_LENGTH)
    t.replace("src/pc/djui/djui_panel_vr.c",
              "    configVrPunchColliderLength = 275;\n",
              "    configVrPunchColliderLength = %d; // [gore fork] was: 275\n" % PUNCH_COLLIDER_LENGTH)


def vr_players_body(t):
    f = "src/game/rendering_graph_node.h"
    t.before(f, "#endif // RENDERING_GRAPH_NODE_H\n", VR_BODY_H)

    f = "src/game/rendering_graph_node.c"
    t.replace(f,
              "    mtxf_scale_vec3f(matrix, matrix, scale);\n"
              "    mtxf_mul(gMatStack[gMatStackIndex + 1], matrix, gMatStack[gMatStackIndex]);\n",
              "    mtxf_scale_vec3f(matrix, matrix, scale);\n"
              "    mtxf_mul(gMatStack[gMatStackIndex + 1], matrix, gMatStack[gMatStackIndex]);\n"
              "    fork_vr_remote_body(node->translation, gMatStack[gMatStackIndex + 1], false); // [gore fork]\n",
              count=2)
    t.replace(f,
              "        mtxf_scale_vec3f(matrix, matrix, scale);\n"
              "        mtxf_mul(gMatStackPrev[gMatStackIndex + 1], matrix, gMatStackPrev[gMatStackIndex]);\n",
              "        mtxf_scale_vec3f(matrix, matrix, scale);\n"
              "        mtxf_mul(gMatStackPrev[gMatStackIndex + 1], matrix, gMatStackPrev[gMatStackIndex]);\n"
              "        fork_vr_remote_body(node->translation, gMatStackPrev[gMatStackIndex + 1], true); // [gore fork]\n",
              count=2)
    text, crlf = t.read(f)
    for needed in ("static void geo_process_animated_part(struct GraphNodeAnimatedPart *node) {",
                   "static void geo_process_bone(struct GraphNodeBone *node) {",
                   "struct MarioBodyState *gCurMarioBodyState = NULL;"):
        if text.count(needed) != 1:
            raise Problem("%s: expected 1 of %r, found %d" % (f, needed, text.count(needed)))
    if not text.endswith("}\n"):
        raise Problem(f + ": doesn't end where a function ends")
    t.write(f, text + VR_BODY_C, crlf)
    t.log.append(f)

    f = "src/game/mario_misc.c"
    t.before(f, "        // update head position in bodyState only if it's a valid Mario\n",
             "        // [gore fork] A VR player's head looks where his headset looks.\n"
             "        if (marioActive && plrIdx != 0) {\n"
             "            fork_vr_remote_head(plrIdx, *c, rotNode->rotation);\n"
             "        }\n"
             "\n")
    t.before(f,
             "        if (bodyState->handState == MARIO_HAND_FISTS) {\n"
             "            // switch between fists (0) and open (1)\n",
             "        { // [gore fork] A VR player's hands are open or closed as his are.\n"
             "            const s32 forkCase = fork_vr_remote_hand_case(bodyState, switchCase->parameter);\n"
             "            if (forkCase >= 0) {\n"
             "                switchCase->selectedCase = forkCase;\n"
             "                return NULL;\n"
             "            }\n"
             "        }\n")
    text, _ = t.read(f)
    for needed in ('#include "rendering_graph_node.h"', "geo_mario_head_rotation(s32 callContext, struct GraphNode* node, "):
        if text.count(needed) != 1:
            raise Problem("%s: expected 1 of %r, found %d" % (f, needed, text.count(needed)))

    f = "src/pc/lua/smlua_functions.c"
    t.after(f, '#include "game/hardcoded.h"\n', '#include "game/rendering_graph_node.h" // [gore fork]\n')
    t.before(f, "void smlua_bind_functions(void) {\n", VR_BODY_LUA)
    t.after(f, '    smlua_bind_function(L, "return_self", smlua_func_return_self); // compatibility band-aid\n',
            "\n"
            "    // [gore fork]\n"
            '    smlua_bind_function(L, "vr_remote_pose", smlua_func_vr_remote_pose);\n')



EXPECTED = {
    "pc": lambda t: not t.exists("src/pc/vr/vr.c") and not t.exists("Android.mk"),
    "vr": lambda t: t.exists("src/pc/vr/vr.c") and t.exists("platform/android/app/build.gradle"),
    "android": lambda t: t.exists("Android.mk") and t.exists("platform/app/build.gradle"),
}


def say(kind, base, message):
    """A line for the log, and on the run's page when this runs in GitHub Actions (`kind`: notice, warning)."""
    print(message, flush=True)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::%s title=fork/apply.py (%s)::%s" % (kind, base, message), flush=True)


def copy_state(folder, tree):
    """Whether the copy in `folder` still is the files of the commit it was taken from: True, False, or None
    where that can't be told (no git, or this repository came without its history)."""
    def git(*args):
        try:
            return subprocess.run(["git", "-C", REPO] + list(args), check=True, capture_output=True,
                                  text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    committed = git("rev-parse", "HEAD:" + folder)
    changed = git("status", "--porcelain", "--", folder)
    if committed is None or changed is None:
        return None
    return committed == tree and changed == ""


def fetch(base, directory):
    """Puts the base's source into `directory`: this repository's copy of it, or the original if the copy
    isn't here (a checkout can leave the folder out)."""
    pin = BASES[base]
    local = os.path.join(REPO, pin["folder"])
    if os.path.isfile(os.path.join(local, "src", "pc", "network", "version.h")):
        same = copy_state(pin["folder"], pin["tree"])
        if same is False:
            say("warning", base, "the game's source is this repository's %s/, which is NOT the files of %s at %s "
                "any more: something in it has been changed" % (pin["folder"], pin["repo"], pin["commit"]))
        else:
            which = "the files of commit %s" % pin["commit"][:7] if same else "not compared with its commit"
            say("notice", base, "the game's source is this repository's %s/ (%s)" % (pin["folder"], which))
        shutil.copytree(local, directory, symlinks=True)
        return

    say("notice", base, "this repository's %s/ isn't here: the game's source is fetched from %s at %s" % (
        pin["folder"], pin["repo"], pin["commit"]))
    os.makedirs(directory)

    def git(*args):
        subprocess.run(["git", "-C", directory] + list(args), check=True)
    git("init", "-q")
    git("config", "core.autocrlf", "false")
    git("remote", "add", "origin", pin["repo"])
    git("fetch", "-q", "--depth", "1", "origin", pin["commit"])
    git("checkout", "-q", "FETCH_HEAD")


def apply(base, directory):
    t = Tree(directory)
    if not t.exists("src/pc/network/version.h"):
        raise Problem("%s is not a checkout of the game" % directory)
    if not EXPECTED[base](t):
        raise Problem("%s doesn't look like the '%s' base" % (directory, base))
    text, _ = t.read("src/pc/network/version.h")
    if "FORK_VERSION_SUFFIX" in text:
        raise Problem("%s has been changed already; start from a clean checkout" % directory)

    check_names()
    stamp = build_stamp()
    work = tempfile.mkdtemp(prefix="fork-mods-")
    try:
        gather_mods(work)
        object_limit(t)
        embedded = built_in_mods_files(t, stamp)
        built_in_mods_c(t, embedded)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    game_title(t, base)
    version_and_lobbies(t, base)
    f = "src/pc/network/coopnet/coopnet.c"
    # The coordinator reports a destination ID, not a session user ID.
    t.replace(f, "u8 localIndex = coopnet_user_id_to_local_index(tag);", """u8 localIndex = UNKNOWN_LOCAL_INDEX;
                for (u8 i = 1; tag && i < MAX_PLAYERS; ++i) {
                    if (gNetworkPlayers[i].connected && coopnet_get_dest_id(coopnet_raw_get_id(i)) == tag) {
                        localIndex = i;
                        break;
                    }
                }""")
    t.replace(f, "if (localIndex == 0) {\n                    name", "if (tag && coopnet_get_dest_id(sLocalLobbyOwnerId) == tag) {\n                    name")
    t.replace(f, "    coopnet_send_to(userId, data, dataLength);\n\n    return 0;",
              "    return coopnet_send_to(userId, data, dataLength) == COOPNET_OK ? 0 : -1;")
    f = "src/pc/network/packets/packet_reliable.c"
    # Send an ACK to the actual sender even when another peer owns slot zero.
    t.before(f, "    network_send_to(0, &ack);", "    ack.addr = p->addr; // borrowed for this non-reliable send\n")
    t.replace(f, "remove_node_from_list(head);", "remove_node_from_list(node);")
    f = "src/pc/network/network_player.c"
    t.replace(f, "if (!np->connected) { return; }", "if (np == NULL || !np->connected) { return; }")
    t.replace(f, "network_shutdown(false, false, true, false);\n        }\n\n        elapsed",
              "network_shutdown(false, false, true, false);\n            return;\n        }\n\n        elapsed")
    f = "src/pc/network/packets/packet_ordered.c"
    t.replace(f, "globalId > MAX_PLAYERS", "globalId >= MAX_PLAYERS")
    t.replace(f, "globalIndex > MAX_PLAYERS", "globalIndex >= MAX_PLAYERS", count=2)
    # Older flat/VR receivers read an eight-byte wire size directly into size_t.
    # On a 32-bit client that overwrites the next field during the mod handshake.
    f = "src/pc/network/packets/packet_mod_list.c"
    for target in ("mod", "file"):
        old = "    packet_read(p, &%s->size, sizeof(u64));" % target
        if old in t.read(f)[0]:
            t.replace(f, old, "    u64 wireSize = 0;\n"
                      "    packet_read(p, &wireSize, sizeof(wireSize));\n"
                      "    if (p->error || wireSize > MAX_MOD_SIZE) {\n"
                      "        djui_popup_create(DLANG(NOTIF, DISCONNECT_BIG_MOD), 4);\n"
                      "        network_shutdown(false, false, false, false);\n"
                      "        return;\n    }\n"
                      "    %s->size = (size_t)wireSize;" % target)
    no_update_checks(t, base)
    vr_for_everybody(t, base)
    vr_players_body(t)
    if base == "vr":
        vr_punch(t)
        android_app_vr(t)
    if base == "android":
        android_app_port(t)
    icons(t, base)

    seen = []
    for entry in t.log:
        if entry not in seen:
            seen.append(entry)
    print("%s: %d changes in %d places" % (base, len(t.log), len(seen)))
    for entry in seen:
        print("  " + entry)
    print("  \"%s\", version v1.5.1%s, CoopNet name %s, %d objects (%s)"
          % (GAME_TITLE, VERSION_SUFFIX, COOPNET_GAME, OBJECT_POOL, stamp.strip()))
    print("  compiled into the program: %s (%d files, %.1f MB; no list of mods shows it, \"%s\" in the pause menu)"
          % (", ".join(EMBEDDED_MODS), embedded["count"], embedded["size"] / 1048576, SETTINGS_LABEL))
    print("  always on, in the mods folder: %s"
          % (", ".join(name for name in BUILT_IN_MODS if name not in EMBEDDED_MODS) or "nothing"))
    print("  the host's choice: %s" % (", ".join(CHOICE_MODS) or "nothing"))
    if MODS_STATE:
        print("  the other mods are from %s" % MODS_STATE)


def main(argv):
    if len(argv) != 3 or argv[1] not in BASES:
        print("usage: python3 fork/apply.py <pc|vr|android> <directory>", file=sys.stderr)
        return 2
    base, directory = argv[1], os.path.abspath(argv[2])
    try:
        if not os.path.exists(directory):
            fetch(base, directory)
        apply(base, directory)
    except Problem as problem:
        print("error: %s" % problem, file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            print("::error title=fork/apply.py (%s)::%s" % (base, problem))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
