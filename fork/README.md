# Realism64

this is my realism version of SM64 Coop DX. it started as GORE / Hard-Mode but i heavily edited it and made it more of a realism mode

it has a 30,000 object limit and builds for pc, vr, android and wii u. the builds use their own CoopNet name (`lumi64`) so they don't join the official game's lobbies

you need your own Super Mario 64 US ROM because it isn't included

## builds

- windows: `Realism64-Windows.zip`
- linux: `Realism64-Linux.zip`
- mac: `Realism64-macOS-AppleSilicon.zip` or `Realism64-macOS-Intel.zip` (macOS 11 or newer)
- windows vr: `Realism64-VR-Windows.zip`
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

windows builds use the original games' saves and settings folders. android installs separately. the pc vr zip doesn't include offline chat dictation

## platform field kits

These are local features: they do not change other players or require matching hardware in a lobby.

| Build | Feature | How to use it |
| --- | --- | --- |
| Desktop (Windows, Linux, macOS) | Practice splits in game time | `/split start`, `/split` for each checkpoint, then `/split stop`. |
| VR (PC VR and Quest) | Hands-together pulse check | Hold both tracked hands together for half a second to see health. Separate them before checking again. |
| Android (flat) | Dive warning | A local popup warns once when swimming deep with less than four health wedges. |
| Wii U | Co-op spotter | `/spotter` reports the closest teammate in the same course, act and area, with distance in game units. |
| Xbox 360 | Low-health heartbeat | Below four health wedges the controller pulses, faster on the last wedge. Requires rumble enabled. |

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
