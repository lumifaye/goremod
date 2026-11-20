# Xbox 360 game target (bring-up)

Use the Wii U engine **with** the Realism64 fork applied. The following is the game build path under development, not the standalone diagnostic. Actions has produced a game `default.xex`; gameplay is not yet verified.

From the repository root on Linux, choose a fresh staging directory outside the checkout:

```sh
game=$(mktemp -d)
cp -a WiiU/. "$game/"
python3 fork/apply.py pc "$game"
export XSDK_ROOT=/absolute/path/to/xsdk  # 9e6de98f6b5d737bce0fecd2864edae94bdd2637
export PATH="$HOME/xsdk-gcc/bin:$PATH"
make -C "$game" TARGET_XBOX360=1 all
```

The target links the engine ELF with xSDK's title startup and packages it with `elf2xex.py`. Intended output: `build/us_xbox360/default.xex`, with resources beside the XEX on a writable `game:/` mount. Do not set `TARGET_WII_U` at the same time. Host asset tools are native; title objects require the xSDK ABI compiler, not devkitPPC. SDK headers alone are not sufficient. Remaining engine dependencies (including SDL2 interfaces and zlib) must be available for the **target**, not linked from the Linux host; `EXTRA_INCLUDES` and `XBOX_PORT_LIBS` are the include/library inputs. A complete dependency sysroot is not supplied.

The default renderer sends Fast3D batches to the Xenos GPU at the presentation resolution. It compiles a vertex/pixel program on first use of each combiner and keeps it for subsequent draws. A new shader may hitch on first use. Vertex memory rotates through fenced blocks; texture pages are recycled only after outstanding draws finish. The title log should say `xbox renderer: native Xenos`. A GPU allocation or program setup failure can switch the title to software; look for `xbox GPU:` in `default.log`.

For a visual comparison or if the native path shows no picture, place an empty `software-renderer.txt` beside `default.xex` and restart. Delete the file to use the GPU again. The CPU path is much slower on hardware. Use `xbox slow tick` log lines to compare the same scene; their absence is not a measured frame rate.

### CoopNet multiplayer

CoopNet is built into the Xbox game by default. On **Host**, select **CoopNet** and set the player limit to at least two. On the second device, use **Join** and browse the Realism64 lobbies. Use matching game versions and mods. Existing settings may still select Direct Connection. Xbox uses IPv4 and requires network access to the configured CoopNet service and the ICE endpoints it supplies. Cross-compilation alone does not verify matchmaking or NAT traversal.

### Reproducing the Actions build

`.github/workflows/xbox360-game.yml` checks out the exact revisions of xSDK, zlib and SDL2. After installing the pinned compiler, apply `git -C "$XSDK_ROOT" apply "$PWD/xbox360-port/xsdk-vdswap.patch"` once and run `make -C "$XSDK_ROOT" build/libxsdk.a`. Then use those zlib/SDL checkouts to build the target libraries:

```sh
ports=$(mktemp -d)
xbox360-port/build-deps.sh /path/to/SDL /path/to/zlib "$ports/build" "$ports/install"
make -C "$game" -j3 TARGET_XBOX360=1 EXTRA_INCLUDES="$ports/install/include" \
    XBOX_PORT_LIBS="-L$ports/install/lib -lSDL2" all
```

SDL2 uses xSDK pthreads and its monotonic clock; game rendering, audio output, controller input and text entry use the native Xbox backends. The workflow checks the packaged XEX2 header and uploads the title and its resource directories only on success. To try a successful build, extract those files together on writable storage and place your own unmodified US `baserom.us.z64` alongside `default.xex` (or under `roms/`). A successful package still needs a boot and gameplay check on the console.
