# Realism64

SM64 Coop DX with GORE / Hard-Mode built in, a 30,000 object limit, and PC, VR, Android and Wii U builds. The builds use their own CoopNet name (`lumi64`), so they don't join the official game's lobbies.

You need your own Super Mario 64 US ROM. It's not included.

## Builds

- Windows: `Realism64-Windows.zip`
- Linux: `Realism64-Linux.zip`
- Mac: `Realism64-macOS-AppleSilicon.zip` or `Realism64-macOS-Intel.zip` (macOS 11+)
- Windows VR: `Realism64-VR-Windows.zip`
- Android: `Realism64-Android.apk`
- Quest: `Realism64-VR-Quest.apk`
- Wii U: `Realism64-WiiU.zip` (test build; console testing is limited)

Linux needs SDL2, OpenGL, libcurl and zlib. On Mac, you might need to allow the unsigned app in System Settings > Privacy & Security. Quest needs SideQuest or adb. The Wii U needs Aroma and your ROM at `wiiu/apps/sm64coopdx/roms/baserom.us.z64`.

## What's different

- Gore is built in, with its settings under **Gore Settings**. Other included mods are in the mods menu.
- VR and flat-screen players share lobbies. VR hands and some VR items are shown to other players. VR head turning is disabled because it looked wrong in testing.
- Voice chat works between the flat and VR builds. The microphone starts off. Wii U sound and voice chat haven't been tested on a console.
- Character Select bodies keep their character where possible. Multiplayer blood, caps and bodies use the host's save.
- Updates from the original games are disabled so they don't replace this build.

The Windows builds use the original games' saves and settings folders. Android installs separately. The PC VR zip doesn't include offline chat dictation.

## Building

`build-fork.yml` can be started from Actions, or with `[build]` in a commit message. Use `[build pc]`, `[build linux]`, `[build macos]`, `[build pcvr]`, `[build android]` or `[build quest]` for individual targets. `build-wiiu.yml` uses `[wiiu]` or Actions. Use `[skip ci]` to skip workflow runs on a push. Builds on a private repo use Actions minutes.

Releases contain the builds that succeeded. A full platform build becomes the latest release; partial builds don't. Wii U builds are prereleases.

To apply the changes by hand: `python3 fork/apply.py pc game` (use `vr` or `android` for those bases). `PC`, `VR` and `Android` are copies of the upstream sources; don't edit them for this project. Changes go in `fork/apply.py` and the mod files. `WiiU` is the Wii U port with project changes.

## Adding mods

Upload a mod zip to the repo in `MODS_REPO` in `fork/apply.py`, then build. Mods that list the same `-- incompatible:` value are optional in the menu; the others are always on. To pin the mod repo, set `MODS_REF`; to use a local copy, set `MODS_DIR`.

## Credits and licenses

GORE / Hard-Mode! is by the GORE Team: IncredibleHolc, Cooliokid956, Blocky.cmd, Birdekek, Saniky, Tilly, Isaac, Frijoles, ProfeJavix and I'mYourCat.

SM64 Coop DX is by the Coop DX team. The VR fork is by fulldivegames, the Android port by ManIsCat2, and the Wii U port by efsmert. Wii U builds include CoopNet (GNU AGPL v3) and libjuice (MPL 2.0); their source and licenses are in `WiiU/third_party/coopnet` and `WiiU/third_party/libjuice`.

The Android signing key is in `fork/signing/` so builds can update each other. Anyone with access to it can sign an update; use a private key before distributing to strangers.
