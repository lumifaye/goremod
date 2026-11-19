# Realism64 Xbox 360 port — experimental work in progress

Target: JTAG/RGH Xbox 360, Realism64 only, based on the Wii U version, with controller input and CoopNet where feasible. **There is no playable Xbox build, game XEX, or complete game renderer.** This is an incremental main-branch source commit. The manual diagnostic workflow exists but has not been run; no Xbox hardware/emulator gameplay test has been run.

Base at start of this update: `lumifaye/goremod` main `445596d63440ed96dbd5b7208882eb2ea8d1ffe8`; xSDK source pinned to `9e6de98f6b5d737bce0fecd2864edae94bdd2637`.

## Incremental work in this commit

- `WiiU/src/pc/controller/`: experimental XAM controller backend and controller selection. It maps buttons, triggers and sticks, and now sends timed XAM rumble with host-mocked output/timer coverage. Actual XAM behavior, rebinding, focus and game-build integration remain unverified.
- `WiiU/src/pc/audio/`: experimental 32 kHz signed stereo to 48 kHz six-channel float xSDK audio backend. Not integrated into the game or verified on Xbox.
- `WiiU/src/pc/gfx/`: experimental xSDK 720p display/presentation window API. It is **not a 3D renderer**, and is not integrated into the game.
- `WiiU/src/pc/network/packets/`: select the Wii U little-endian scalar packet conversion for Xbox. Raw bytes and all game/network packet call sites still require an endian audit.
- `WiiU/third_party/libjuice/src/`: preliminary xSDK IPv4-only compatibility, numeric address formatting, interface enumeration and socket nonblocking adaptations. The Xbox build must explicitly define `__XSDK__` and add `xbox360_compat.c` to libjuice's sources. The code has not been cross-compiled against the xSDK or tested with XAM/network hardware; it is not a working CoopNet port.
- `xbox360-port/diagnostic/`: separate early display/controller/audio diagnostic, **not the game**. No XEX has been confirmed. Its build script explicitly defines `__XSDK__` because a compiler-provided definition was not established.
- `xbox360-port/tests/`: host mocks and packet vectors. The ICE pair experiment described below used separately fetched local test/source files and is not included as a self-contained test here.
- The generated workspace-only `xbox360-partial.patch` is not needed to apply the source changes; the committed source tree is authoritative.

## Tests run

The committed mock tests can be run from a repository checkout with `bash xbox360-port/tests/run_NAME_test.sh`:

- `controller`: host mocks for XAM input mapping, rumble amplitude/timed stop and controller dispatch.
- `audio`: host mocks for sample conversion, queueing and shutdown.
- `window`: host mocks for display/presentation lifecycle and error handling.
- `diagnostic`: mocked diagnostic loop, controller and audio integration.
- `net_compat`: host-side numeric IPv4 address and port formatting checks.
- `packet`: native little-endian vectors and big-endian PowerPC/QEMU packet vectors. Optional `PPC_CC` and `QEMU_PPC` must point to those tools. The PPC compiler used was devkitPPC, not the xSDK ABI compiler.

A separate native-host libjuice experiment passed simultaneous and legacy-controlled ICE setup plus bidirectional UDP with the staged xSDK-specific branches enabled. It used host sockets and locally fetched source/test inputs; it does **not** validate XAM, Xbox ABI, NAT behavior, game CoopNet, or cross-platform compatibility.

Passing mocks and host tests do not establish Xbox ABI compatibility, graphics or audio behavior, in-game networking, cross-platform interoperability, or actual hardware functionality.

## Toolchain status and persistence

The xSDK custom-ABI compiler build was still running at the last check after a two-job GCC stage-one build was killed by memory pressure. Binutils succeeded. If the one-job build succeeds, its background script attempts to build `libxsdk.a` and the separate diagnostic XEX. **No successful compiler/library/XEX result has been confirmed.**

Its sources, build tree and logs are under `/home/user/.cache/xbox360-sdk`, symlinked to `/var/tmp/arena-xsdk-6312199`. Both locations are ephemeral or excluded from workspace snapshots; they may not survive a later turn or sandbox reset. Do not claim success until the process exit status and artifacts are verified.

## Major remaining work

1. Finish/verify the custom-ABI xSDK toolchain and diagnostic cross-build; resolve any compile, link or packaging errors. Test a diagnostic separately in Xenia and on real RGH/JTAG hardware.
2. Implement or legally adapt a compatible Xenos 3D renderer, shaders and game graphics integration. Wii U GX2 code cannot be used unchanged. The accessible Diddy Kong Racing Xbox renderer targets a different engine; permissions/provenance need investigation before copying.
3. Build Realism64 from its fork-generated Wii U sources with Xbox-specific platform selection. Integrate controller, audio, timing, threading, file paths, save data, ROM/assets and memory management.
4. Cross-compile and test networking and DNS on the actual xSDK; audit endian-sensitive game and protocol call sites; integrate CoopNet and test hosting/joining against PC and Wii U. IPv4-only networking and actual NAT behavior need validation.
5. Produce a game `default.xex`; test startup, menus, gameplay, controller and performance separately in emulator and on actual hardware.

References: [xSDK](https://github.com/xenosworks/xsdk), [SDL-xenon](https://github.com/xenosworks/SDL-xenon), [Diddy Kong Racing Xbox 360](https://github.com/Matherzinho/Diddy-Kong-Racing-Xbox-360). An indexed `ZenithUzu/sm64coopdx360` description could not be verified because its repository returned 404; its source was not used.
