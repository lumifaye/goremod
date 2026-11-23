# Realism64

this is my realism version of SM64 Coop DX. it started as GORE / Hard-Mode but i heavily edited it and made it more of a realism mode

it has a 30,000 object limit and builds for pc, vr, android and wii u. the builds use their own CoopNet name (`lumi64`) so they don't join the official game's lobbies

you need your own Super Mario 64 US ROM because it isn't included

## builds

- windows (flat screen and PC VR): `Realism64-Windows-VR-and-Flatscreen.zip`
- linux: `Realism64-Linux.zip`
- mac: `Realism64-macOS-AppleSilicon.zip` (macOS 11+) or `Realism64-macOS-Intel.zip` (macOS 10.15+). Intel is published as a separate release in the same workflow run, so it does not delay the main release.
- android: `Realism64-Android.apk`
- quest: `Realism64-VR-Quest.apk`
- wii u: `Realism64-WiiU.zip` (test build, console testing is limited)

linux needs SDL2, OpenGL, libcurl and zlib. on mac you might need to allow the unsigned app in System Settings > Privacy & Security. quest needs SideQuest or adb. for wii u you need Aroma and your ROM at `wiiu/apps/sm64coopdx/roms/baserom.us.z64`

## what's different

- my edited realism mod is built in and its settings are under **Gore Settings**. the other included mods are in the mods menu
- vr and flat screen players share lobbies. other players can see vr hands and some vr items. vr head turning is off because it looked wrong in testing
- flat screen and vr builds have voice chat and the mic starts off. wii u sound and voice chat haven't been tested on a console
- Character Select bodies keep their character where possible. multiplayer blood, caps and bodies use the host's save
- updates from the original games are off so they don't replace this build

windows now uses one executable for flat screen and PC VR; enable VR Mode in settings when using a headset. It uses OpenGL in both modes and does not support DirectX-only hardware. Android installs separately. The Windows package doesn't include offline chat dictation.

**Experimental Better Graphics** is in Display settings and defaults off. On Windows and Quest it adds per-pixel world-space lighting for normally lit 3D geometry, plus texture-space material lighting where bundled normal maps exist. Complex materials may fall back to original lighting; fullbright and HUD are excluded from scene lighting. PC/Linux/macOS and Android phone builds use the simpler vertex-lighting path. Windows, Quest, Linux, macOS and Android phone builds also have an experimental OpenGL GPU shadow map from submitted opaque scene triangles, with soft filtered real-time shadows. The map uses the previous rendered frame, a bounded area and triangle budget, and does not include transparent or cutout materials; unusually complex materials may not receive shadows. On Windows and Quest, enabling it removes built-in contact shadow decals even if the GPU shadow map cannot initialize. On Linux, macOS and Android phones, the built-in decals remain until a shadow map is available and return if it fails or fullbright is enabled. Turn Better Graphics off to restore the original shadows. The larger shadow map can use more GPU memory and bandwidth. On flat-screen OpenGL, it also adds a subtle screen-space bloom, approximate light shafts toward a fixed world-space sun direction, and underwater camera ripple; the shafts use bright pixels rather than real volumetric occlusion, and these effects currently affect the HUD too and are skipped on multisampled targets. VR eyes are excluded from the post effect for comfort. All Better Graphics platforms also add an approximate view-dependent wet sheen to normally lit player models, in and out of water; it is vertex lighting, not a reflection of the scene. It can cost performance and is not available on Wii U or Xbox 360.

## platform field kits

These are local features: they do not change other players or require matching hardware in a lobby.

| Build | Feature | How to use it |
| --- | --- | --- |
| Desktop (Windows, Linux, macOS) | Practice splits in game time | `/split start`, `/split` for each checkpoint, then `/split stop`. |
| VR (PC VR and Quest) | Hands-together pulse check | Hold both tracked hands together for half a second to see health. Separate them before checking again. |
| Android (flat) | Dive warning | A local popup warns once when swimming deep with less than four health wedges. |
| Wii U | Co-op spotter | `/spotter` reports the closest teammate in the same course, act and area, with distance in game units. |
| Xbox 360 | Low-health heartbeat | Below four health wedges the controller pulses, faster on the last wedge. Requires rumble enabled. |

Additional field tools:

- **Xbox 360:** Hard landings give a rumble pulse based on descent speed. Hold **Back** and tap **D-pad Up** for a health, coins and stars readout.
- **Android:** Each 25-coin milestone shows a single popup, without needing to watch the counter.
- **Wii U:** `/trail mark` drops a local breadcrumb. `/trail` shows the X/Y/Z offsets back to it; `/trail clear` or a warp removes it.
- **VR:** `/reach` measures the current span between your tracked hands in game units.
- **Desktop:** `/jumpstats` toggles a landing report with horizontal distance and peak height measured from the first ascending airborne frame.

Use `/fieldkit` to toggle the automatic VR, Android or Xbox feature for the session. Desktop and Wii U tools only run when requested.

## building

run `build-fork.yml` from Actions or put `[build]` in a commit message to build everything, including wii u. for individual builds use `[build pc]`, `[build linux]`, `[build macos]`, `[build pcvr]`, `[build android]`, `[build quest]` or `[build wiiu]` (`[wiiu]` works too). use `[skip ci]` to skip workflow runs on a push

the releases have whatever builds succeeded. all new builds are prereleases

to apply the changes by hand use `python3 fork/apply.py pc game` (use `vr` or `android` for those bases). `PC`, `VR` and `Android` are copies of the upstream sources so don't edit them for this project. changes go in `fork/apply.py` and the mod files. `WiiU` is the wii u port with project changes

## credits

this version is my fork of SM64 Coop DX by the Coop DX team, the vr fork by fulldivegames and the android port by ManIsCat2. the wii u port is by efsmert

the mod started from GORE / Hard-Mode! by the GORE Team: IncredibleHolc, Cooliokid956, Blocky.cmd, Birdekek, Saniky, Tilly, Isaac, Frijoles, ProfeJavix and I'mYourCat. i've heavily edited it into my own realism version so it doesn't really represent the original Hard-Mode anymore

wii u builds include CoopNet (GNU AGPL v3) and libjuice (MPL 2.0). their source and licenses are in `WiiU/third_party/coopnet` and `WiiU/third_party/libjuice`

the android signing key is in `fork/signing/` so builds can update each other. anyone with access to it can sign an update so use a private key before distributing to strangers
