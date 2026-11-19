# Xbox 360 game target (bring-up)

Use the Wii U engine **with** the Realism64 fork applied. The following is the game build path under development, not the standalone diagnostic. It has not produced a verified `default.xex` yet.

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

`gfx_xbox360.c` consumes the game's Fast3D triangle batches, evaluates the combiner, and writes a 320×180 software color buffer. The window backend expands it into the acquired tiled 720p front buffer. This is a CPU renderer, not a port of GX2 shaders. Performance, light-map effects, visual parity, console startup, mod loading and saving remain unverified. CoopNet is off by default.
