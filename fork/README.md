# Realism64: the game with this mod built in

A build of SM64 Coop DX in which GORE / Hard-Mode is part of the game, the object limit is 30,000 instead of
1,200, and which comes in seven kinds. Its window and its Android apps are called
"Realism64!!- COOP NET SUPPORT!!!111"; to CoopNet it is `lumi64`.

| Build | For | Made from | What comes out |
| --- | --- | --- | --- |
| `pc` | Windows, flat screen | [coop-deluxe/sm64coopdx](https://github.com/coop-deluxe/sm64coopdx) v1.5.1 | `Realism64-Windows.zip` |
| `linux` | Linux (64-bit Intel or AMD), flat screen | the same source as `pc` | `Realism64-Linux.zip` |
| `macos` | Macs, flat screen: one for Apple's processors, one for Intel's | the same source as `pc` | `Realism64-macOS-AppleSilicon.zip`, `Realism64-macOS-Intel.zip` |
| `pcvr` | Windows, PC VR (OpenXR) | [fulldivegames/sm64coopdx-VR-Standalone-Physics-based](https://github.com/fulldivegames/sm64coopdx-VR-Standalone-Physics-based) v0.9.26 | `Realism64-VR-Windows.zip` |
| `android` | Android phones and tablets | [ManIsCat2/sm64coopdx](https://github.com/ManIsCat2/sm64coopdx), branch `android` (Av1.5.1) | `Realism64-Android.apk` |
| `quest` | Quest, standalone | the same source as `pcvr` (its `platform/android`) | `Realism64-VR-Quest.apk` |

There is an eighth, for a Wii U with homebrew, built apart from the seven and **not tried on a console**:
`Realism64-WiiU.zip`. See "The Wii U folder".

The three sources are in this repository, each as it is at one fixed commit: the folders `PC`, `VR` and
`Android` at the top (see "Copies of the sources"). A build copies the one it needs, `apply.py` changes that
copy, and it is compiled. Nothing is downloaded from the originals. No ROM is involved: like the originals, each build asks for your own copy of the game at
first start.

**Status: all seven build.** The Linux and Mac programs are started once during the build, as far as their
search for the ROM; nobody has played them. What is described below is written from the source of the games and checked
with small tests outside of them; whoever wrote it has not looked at any of it in a running game. The newest
part, a VR player's arms and hands on the others' screens, has been seen by one player; his head came out
wrong and is no longer turned (see "His arms and hands"). The mod being compiled into the program is checked
as far as a build can: the Windows, Linux and Mac programs are started and what they write out is compared;
that the game then loads it, and what the menus look like without its entry, nobody has seen yet.

## Building

`.github/workflows/build-fork.yml`. It starts

- from the Actions tab, "Build Realism64" → "Run workflow" (once the file is on `main`), or
- on a push whose commit message contains `[build]` (all of them) or `[build pc]`, `[build linux]`,
  `[build macos]`, `[build pcvr]`, `[build android]`, `[build quest]` (one of them; more than one can be
  named). Other pushes start nothing.

What got built becomes a release on the repository's "Releases" page, "Realism64 build <number>" with the
tag `build-<number>` (`fork/ci-release.sh`). Releases stay until somebody deletes them and anybody can
download from them. A run that built all of them becomes the latest release; a run that built only some is
released too and says so in its title. The same files are on the run's page under "Artifacts" for 14 days
(GitHub only gives those to somebody who is logged in). A full run takes about 15 minutes, the builds
side by side. On a private repository that
comes out of the monthly allowance, and there Windows minutes count double and Mac minutes ten times.

The steps that build run through `fork/ci.sh`: when one fails, the lines that say why are on the run's page
as annotations, without opening the log. `fork/ci-dlls.sh` packs the DLLs a Windows program needs.

### Linux and Mac

Both are the `pc` source, built the way the official game's own workflow builds it. There is no VR build
for them: the VR fork's PC VR is written for Windows only.

- **Linux.** Built on Ubuntu 22.04, so it runs on systems of that age or newer. It uses the system's SDL2,
  OpenGL, libcurl and zlib (`fork/README-linux.txt` goes into the zip as `README.txt`). The program is
  changed after the build to look for `libdiscord_game_sdk.so` next to itself; as built it only finds it
  when started from inside its own folder.
- **Mac.** `Realism64.app`, with SDL2 and GLEW compiled during the build and put inside the app, for macOS 11
  and later. `apply.py` gives the app its name, an identifier (`MAC_BUNDLE_ID`) and the sentence macOS shows
  when the microphone is first asked for; without that sentence macOS ends a program that opens a
  microphone, which the voice chat does. The app is signed by nobody ("ad hoc"): macOS refuses it at the
  first start until the player allows it in System Settings > Privacy & Security, or runs
  `xattr -dr com.apple.quarantine Realism64.app`. Signing it properly needs a paid Apple developer account.

Each of these builds is checked before it is packed: the built-in mods are in it, every library it asks for
is in the package or part of the system, and the program is started once, as far as its search for the ROM.
The two Windows programs are started once as well. After each of those starts, `fork/ci-embedded.sh` looks
whether the program wrote out the mod that is compiled into it: every file, and the models, sounds, levels
and textures the same as in this repository. The two Android apps can't be started in a build; there the
mod's last file name is looked for inside the app's library.

By hand, for one of them: `python3 fork/apply.py pc some-folder`, then build `some-folder` the way that game's
own README says.

## What is changed

All of it is in `apply.py`, with the numbers and names at the top of the file.

1. **Object limit.** `OBJECT_POOL_CAPACITY` 1200 → 30000 (`OBJECT_POOL`). It can't be switched off: the
   objects live in a fixed table, 2.4 kB each, used or not (73 MB at 30,000), and the game counts them in a
   16-bit number, so 32,767 is the ceiling without deeper changes. Two places walked the whole table every
   frame. Clearing the collision count now only walks the part that has been used. Drawing kept every slot,
   used or not, in one ring and gave up after 5000 nodes, with the unused ones first: with a table this size
   that drew no object at all (the first builds did exactly that). Now only objects that exist are in the
   ring, in the order they were made, and the guard is the table's size plus 5000. The mod reads the limit
   from the game (`persist.lua`), so on the unchanged game it behaves as before.
2. **The mod is in the program.** This repository's mod is not a folder in `mods`: its files (180 of them, 27 MB) are
   compiled into the program as bytes (`EMBEDDED_MODS`; `src/pc/mods/fork_embedded.c` and `.bin`, written by
   `apply.py`). No list shows it: not the host's mods menu, not the list of a lobby's mods, not the Mod Menu,
   not what CoopNet and Discord are told. Its switches are under their own button in the pause menu,
   **Gore Settings** (`SETTINGS_LABEL`); "Mod Menu" is next to it when another mod has settings.

   What the game runs is still the Lua in this repository, through the game's own loader for scripts,
   models, sounds and levels, and that loader wants files. So at its first start the program writes the
   files out, to `realism64/Gore-Hardmode` in the folder with the saves, and loads them from there. Every
   later start looks whether they are all there and whether the scripts are still the program's, byte for
   byte; a missing file, an edited script, a file that was added, or a new version of the program has all
   of it written again. That folder is the program's: edit the mod in this repository and build, not there.
   A folder `Gore-Hardmode` in a mods folder (an old download, what an older build shipped) is not loaded.
   The game's error screens (a script error, a crash) still call the mod by its name.

   **The other built-in mods.** Every mod in the repository `MODS_REPO` (see "Adding a mod") is copied into
   the game's `mods` folder with a file `built-in.txt` in it. A host always runs them; the mods menu shows
   them ticked and greyed out. Mods that the game can't run together (they name the same thing in their
   `-- incompatible:` line: two romhacks) come with the game as well, but are ordinary mods in the menu, off
   until the host ticks one. A folder of the same name in the player's own mods folder is ignored, so an
   old download can't take the place of the one that came with the game.
3. **Its own name and lobbies.** The window title and the app names are `GAME_TITLE`. The version is
   `v1.5.1-gore1`. What the game tells CoopNet it is: `lumi64`, the same for all four builds and for every
   kind of lobby. These builds see each other and nobody else: not the official game, not the original VR or
   Android builds. That is on purpose, a different object limit is not compatible mid-game. Direct connection
   needs the same version on both sides too.
4. **No update checks.** All of them would install the original over this build.
5. **Android apps.** App ids `com.maniscat2.sm64coopdx.gore` and `com.fulldivegames.sm64coopdxvr.gore`, so
   they install next to the originals, with their own saves and settings. Both are signed with the key in
   `signing/`, so a new build installs over the last one. On start they replace the installed copy of a
   built-in mod when the app brings another version of it (the originals never overwrite a mod).

6. **VR and flat players together.** The VR fork keeps its players apart: "VR lobbies" are a list of their
   own, a flat game that joins one is kicked, and in ordinary public lobbies its power-ups and cheats are
   off. Here there is one list. A VR build never treats a lobby as VR-only or as ordinary: nobody is kicked,
   and the power-ups, special moves and the VR cheats menu work in every lobby. The "Public VR Lobbies"
   button, the warning before the public list and the "Public Lobby Type" choice when hosting are gone.
   See "VR players, as the others see them" below for what is shown of them.
7. **Voice chat on the flat builds**, compatible with the VR builds'. See "Voice chat" below.
8. **Third person while dead (VR builds).** In first person a VR player looks out of Mario's head and would
   see nothing of what the mod does to his body. While his Mario is dead the camera mode is third person,
   and it goes back to the mode he chose when he lives again. The mod says when he is dead
   (`vr_set_death_camera`, in `vrsync.lua`): no health left, one of the game's or the mod's death actions,
   a bubble, or the fade after a fall out of the level. His choice is what is written to the config file,
   and it comes back by itself after a second if the lobby is left with a dead Mario. Gore Settings, under
   VR PLAYERS: "VR: third person while you are dead" (on at first, each player's own).
9. **A VR player's Mario (all builds).** The game turns the arms of a VR player's Mario to where the mod
   says his hands are, and draws Mario's own hands there (`vr_remote_pose`; see "His arms and hands"
   below). It can turn his head too, and the mod no longer asks it to. The VR builds tell the mod where his
   eyes are and where they look (`vr_net_head`).
10. **First person at his character's eye height (VR builds).** The VR game put the camera at a height out
   of a table (167 above his feet for Mario, whose eyes are at about 118; more for the others; Mario's for
   every character a mod brings) and stretched the body it shows the player up to it: a player a third
   taller than the Mario everybody else sees. Now the height is read off the skeleton of the model he
   wears while it stands still: the joint his head sits on, and 30 above it. Any model, tall or short; it
   is measured again when he changes character, and the camera glides to a new value. The body isn't
   stretched any more. "First Person Height" in the VR Camera Settings counts from there: 100 is eye
   level, less is lower, more is higher (the heights saved before meant something else and go back to 100
   once).
11. **A VR punch hits where the glove is (VR builds).** In the headset 100 units are a metre. The VR game
   counted another player as hit inside a box 64 units around him and 225 high (his Mario is about 30
   around and 160 high), and let the fist reach 2.75 times its own height downwards: a fist half a metre
   from anybody hit him. Now another player is as big as his Mario (`PUNCH_BODY_RADIUS` around his middle;
   as high as the game says he stands, 160, or 100 while he ducks), and the fist is the glove that is
   seen, with nothing below it. For enemies and objects the reach below the glove is the VR setting
   "Punch Collider Length (%)": it now starts at 100, the glove itself (`PUNCH_COLLIDER_LENGTH`; whoever
   still had the old 275 gets 100 once, a number he chose himself stays). Enemies keep the game's own
   hitboxes, which are often wider than they look. Raise the slider again if short enemies are too hard
   to reach. A punch still has to be swung (grip closed, fast enough), and stays live for about a second.

The two Windows builds use the same settings and saves folder as the games they are made from.

Not in the PC VR zip: the `speech` folder (offline dictation for the chat box). The VR fork builds that on
the author's machine, with a 180 MB download.

## VR players, as the others see them

The VR fork shows a VR player's tracked hands, his power-ups and his special moves to nobody but himself;
it has no network code for them. That part is new here, and it is in the mod (`vrsync.lua`), not in the game:

- The two VR builds get four Lua functions, `vr_net_state()`, `vr_net_head()`, `vr_net_pop_hit()` and
  `vr_net_pop_event()`. The first says where the hands are, whether they are closed, whether one holds his
  hat, which power-ups run, and where his things in the level are: what he throws, the power-up items and
  caps waiting to be picked up, the hat he threw. The second says where his eyes are and where they look.
- `vrsync.lua` sends that to the lobby 15 times a second (19 bytes, 7 more for each thing, at most 47 of
  them, and 7 for the head) as an ordinary mod packet, and every build draws what it receives. A build
  without those functions never sends: the flat builds can show all of it and do none of it.
- All builds get one Lua function, `vr_remote_pose()`: the mod tells the game each frame where a VR
  player's hands are and where he looks, and the game draws his Mario that way (next section).
- A VR punch or special move that hits another player went out as a packet only VR builds know. It now goes
  through the mod to the player who was hit, and that player's game applies it with the game's own
  player-versus-player code. With the hit he sends where his hands are at that moment, and for a few
  frames everybody shows them exactly there instead of gliding to them: before, his fist was still on its
  way on the others' screens when the hit landed. (What stays: each player sees the others where they
  were a moment ago, so on the screen of whoever is hit the fist can still be beside him.)

What a flat build shows, with the models every build has (the VR fork's own models are only in the VR builds):

| On the VR player's side | On everybody else's screen |
|---|---|
| Tracked hands, open or closed | His Mario's arms reach to where his hands are, with Mario's own hands there, open or closed |
| Where his headset points (first person) | His Mario's body faces that way; his head is not turned on its own |
| Big hands | Mario's hands, as much bigger as his are |
| Fire flower | White cap and shirt, red overalls; his fireballs as red flames |
| Hammer suit | Black cap and shirt; his hammers as small metal balls |
| Sonic shoes | Red shoes |
| Power star | Sparkles around him |
| Rasengan, rasen shuriken | A blue flame in his hand, a bigger one flying |
| Propeller | Nothing of its own (his Mario flies, as the game sends it anyway) |
| A fire flower waiting to be picked up | A red flame with a shadow |
| A hammer suit, sonic shoes, big hands item | A metal ball, a blue coin, a white ball |
| A propeller mushroom | A 1-up mushroom |
| A power star item | A star, turning |
| A wing, metal or vanish cap out of his Spawn Menu | That cap, turning (the vanish cap as a plain cap) |
| His hat, taken off his head | The cap in that hand, and none on his head |
| His hat, thrown | The cap flying and landing; the one on his head is back |
| Level Select in his cheats menu | A chat line "*name* used the VR Level Select: *level*" |

Those items and caps are his: they come out of his boxes and his Spawn Menu, his game alone decides who
picks them up, and that is him. The others see them, and see them go when he takes them. A flat player
can't take one.

The host option "VR Level Select takes everybody along" (Gore Settings, under VR PLAYERS; off at first) makes
everybody follow him to the level he chose.

Still not shown: the propeller on his head, and the propeller and hammer helmets when it is one of those he
takes off (it is drawn as his cap).

### His arms and hands

A VR player's hands used to be two white balls, placed as far from his Mario's feet as his hands were in his
own game. His VR camera sat a good bit above Mario's eyes in first person, so they hung that much too high.
Now:

- **Where.** His game sends each hand as "this far from my eyes", and it is drawn that far from his Mario's
  eyes. A hand in front of his face is in front of Mario's face, in every camera mode. His eyes are where
  his own picture is drawn from: in first person on a PC headset that is at his character's eye height
  whatever height the headset is at, and the hands are measured from there (they used to be measured from
  the headset, and hung too low for a player who stood up after recentring).
- **Hands.** No balls. The upper arm and forearm of his Mario are turned so that Mario's own hand ends up at
  that place, with the elbow down and out. Mario's arms are short: past their reach both halves get longer,
  up to three times, and the hand is where it belongs either way. The hand is a fist while he squeezes or
  pulls the trigger and open otherwise. Which way it is turned is not sent: it follows the forearm.
- **Head: not turned.** For a few builds his Mario's head was turned the way his headset was. In a real
  headset it came out tilted and looking at the floor, and hardly moved with his own. So the mod no longer
  asks for it: his head is whatever the game animates. The game's part (`vr_remote_pose` with the head
  bit) is still there, unused, and where he looks is still sent, because the hands and the body need it.
- **Body.** In first person his Mario's body faces where his headset points, on everybody's screen, within
  a few frames (it used to wait until he had turned his head 40 degrees). In third person his Mario faces
  the way it runs, as the game has it.
- **Dead.** While his Mario is dead nothing of this is sent: the body lies the way it died.
- Packets come 15 times a second; what is drawn glides between them.

Works on whatever model the player wears, as long as its skeleton is built like Mario's (the arm lengths are
read off it). His reflection in the mirror room keeps the arms the game animates.

"VR players' hands: higher / lower" (Gore Settings, under VR PLAYERS; for your own screen) moves the others' VR
hands up or down from there, by up to 40 units (Mario is about 150 tall).

A game without `vr_remote_pose` (a build of this project from before it) still gets the white balls, at the
new places. A VR build from before `vr_net_head` is still understood: its hands are put where it says, and
its head isn't turned.

## Voice chat

The VR fork has voice chat between its own builds. The flat builds now have the other end of it
(`src/pc/network/fork_voice.c`, written by `apply.py`): the same two packets and the same sound format
(16 kHz mono, mu-law, 20 ms a packet), so all four builds hear each other. Options > Sound has three new
entries on the flat builds:

| Entry | At first | |
|---|---|---|
| Voice chat (hear the others) | on | Off: nothing is played, nothing is sent, the others' games stop sending to this one |
| Microphone on (the others hear you) | **off** | Opens the default microphone. Android asks for the permission the first time. On a Wii U it is the GamePad's |
| Voice volume | 100 | 0 to 200 percent |

A flat build sends nothing while the room is quiet (it stops 0.3 seconds after the last sound louder than
a whisper). What the flat builds don't have, and the VR builds do: a choice of microphone, a microphone
level, muting one player, and the "speaking" mark in the player list. The hit packet of the VR fork is known
to the flat builds and dropped; nothing sends it any more.

## Characters of Character Select

What is left of a player used to be Mario (or Luigi, Toad, Waluigi, Wario), whoever he had picked in
Character Select. Now:

- A body that stays in the level, and a cap that stays behind, remember which character and which
  costume they were (`g` and `j` of an entry in `persist.lua`: a number made from the name the character
  is saved under, and the costume's position) and are put back with that character's model and cap.
  It works for the other players' bodies too: Character Select already tells every game who is who.
  A game that does not have the character shows the plain one.
- A character with a model of its own has no headless and no bitten-through version. It used to turn
  into what is left of Mario; it stays itself (with its head). `GoreHMApi.get_char_models` decides.
- The helpers are in `api.lua` (`gore_cs_of_player`, `gore_cs_model`, `gore_cs_cap_model`,
  `gore_cs_own_model`).

Also in multiplayer: `spawn_sync_if_main` was called with a player's number for things that happen to
one player (the flames of the hell entrance, the Bob-omb at 100 coins, the smoke and explosions of
`on_interact`). It only ever said yes for the host's own Mario, so for everybody else these were never
made. They go through `spawn_sync_if_owner` now: the game of the player it happens to makes them.

### Hair, and whose looks a body borrows

A dead body is a player model, and a player model asks a player for its colours, its face and its
pose. The game has no way to draw one as "nobody", so a body is drawn as our own player: for the
instant it is drawn, our player gets its colours, dead eyes and limp hands ("Looks" in `persist.lua`).

- Characters with hair that swings (Hatsune Miku of the Triple Baka pack, and every character built
  on the same "physbones") remember per player where the hair was a frame ago, in
  `_G.physBoneMem[player]`. A body drawn as our player used our player's memory, so with a body of
  such a character in view the hair of the living one was told every frame that it had jumped to the
  body and back, and flew about. A body now has a number (`oBehParams2ndByte`) and a memory of its
  own, which is put in place of ours while it is drawn.
- What was borrowed used to be handed back before the next thing of ours was drawn, or at the end of
  the picture. Now a body (and a cap that stayed behind) asks the game to say when it is done with it
  (`hookProcess`, `HOOK_ON_GEO_PROCESS`), and everything is handed back right then. Nothing else that
  is drawn or looked up in between (another mod's hooks, the HUD, anything else the game draws in our
  colours) sees a body's colours, face or hair on our player.

### Whose save

Blood, caps and bodies that stay are kept in a save, and every game used to use its own: whoever
joined a game saw the bodies of his own save in it, and took home what happened there. Now what is
remembered in a game is the host's ("The host's stores" in `persist.lua`):

- A guest neither reads his save nor writes to it. It is there again, untouched, when he plays alone
  or hosts.
- When a guest comes into an area he asks the host for it, and the host sends what he has of it:
  bodies and caps first, then the blood (at most the newest 20000 stains, or the guest's own "Max
  stains per area"), a few packets a frame. The next time, only what is new since then.
- What happens in front of a guest he still notes himself, so it is there at once. If the host is not
  there to see it (another level, another act), the guest tells him, and it goes into the host's save.
- The host's "Wipe ALL saved blood, caps & bodies" clears his guests as well. A guest's only clears
  what his own game shows, until he comes into the area again.
- A body is not at exactly the same spot in two games. One that comes from the host is left out when
  this game has noted one itself close by, in the same colours.

`fork/tests/persist_net_test.lua` tries this without the game (a host and two guests side by side,
the network faked): `lua fork/tests/persist_net_test.lua` from the top of the repository.

### One of everything

The rule the mod follows now, for anything all players are meant to see or hear:

- **It happens to a player** (he splats, loses his head, hits a wall): his own game makes the shared
  object and sends the sound. Nobody else's does.
- **An enemy or a boss does it by itself** (it falls to its death, bursts, is eaten by the Chain Chomp):
  every game sees that happen, so every game makes its own blood, smoke and sound, not shared
  (`squishblood_local`, `spawn_non_sync_object`, `local_play`). A trophy is the exception: one game
  makes it for all (`spawn_sync_if_main`).

What did not follow it, and does now:

- `mario_update` in `main.lua` was hooked for every player and then worked on the local Mario, so it ran
  once per player in the level each frame. With four players, every timer in it (the splat, the gas, the
  penguin, the fire) went four times as fast. It runs once.
- The gas (`s.ishigh`) turned the stick of every player on the screen of the one who was in it.
- The blood pool that is left 14 frames after a splat, and the pool under a decapitated player, were made
  by the host only, and the host only ever saw its own Mario reach that moment.
- A wall splat (`act_ragdoll`) made its stain, its sound and its 50 bits in every game that could see the
  player: with four players, four stains, four sounds each and 200 shared bits.
- A PvP hit made blood and sound in every game that saw it.
- King Whomp, King Bob-omb, the Chain Chomp's meals and its release, Tuxie, Yoshi, Klepto, Hoot, the
  stopwatch, Chuckya: one shared object and one sent sound from every player, for one event. The goal
  post gave a trophy per player.

Not changed, known: two players dying in the same instant can count as one in the death counter (each
game adds one to the number it last heard).

## Adding a mod

Upload its zip to the repository named in `MODS_REPO` in `apply.py`
([lumifaye/mbjmnmnmnmn](https://github.com/lumifaye/mbjmnmnmnmn)), then build (a commit here with `[build]`
in its message). Every zip at the top of that repository is one mod: the zip holds the mod's folder, or the
mod's files themselves. A mod that is a single `.lua` file goes into a folder, named `main.lua`. A folder
with a `main.lua` in `fork/mods/` is built in the same way.

What a mod becomes is read from the `-- incompatible:` line at the top of its `main.lua`:

- nothing there, or nothing another built-in mod names too: **always on**, locked in the mods menu;
- the same word as another built-in mod (`romhack`): **the host's choice**. It is in the menu, off; the game
  lets the host tick one of them.

The build's first lines say which is which, and the build stops when a mod can't be used: no `main.lua`, a
folder or file name starting with `_` (Android leaves those out of an app), 35 MB or more (the game's
limit), or a mod that names `gore` as incompatible.

The build takes the newest state of that repository's `main` branch. To stay with one state, put a commit id
in `MODS_REF`. To build without the network: `MODS_DIR=<a checkout of it> python3 fork/apply.py pc game`.

Players of an older build can still join: they get the host's mods the usual way. Raise `VERSION_SUFFIX`
(`-gore2`) when old and new builds must not join each other.

### With the other built-in mods

- **Character Select** puts a player's own model back whenever something else is put on him. The mod's
  bodies without a head, bitten in half, and gold go on through `gore_set_body_model` (`!utils.lua`), which
  Character Select leaves alone. They are the bodies of the character the chosen one is based on: a
  decapitated Miku is Mario's body without a head, and so are the bodies that stay behind.
- **A romhack** changes the levels. The mod's own changes to the levels are off while "romhack
  compatibility" is on, which it is from the start.

## Changing the mod

Changes to the Lua files need a new build to reach players, like before they needed a new download. Players
of different builds can still join each other as long as `VERSION_SUFFIX` is the same: the host's copy of the
mod is sent to whoever doesn't have that exact one.

## Copies of the sources

Four folders at the top of this repository hold other people's games, without their history. `PC`, `VR` and
`Android` are copies: the files as they are at one commit, nothing in them changed. `WiiU` is a port joined
with a newer version of the game, which makes it this project's own work (see "The Wii U folder"). None of
the four is part of the mod (`fork/apply.py` and `site/build.mjs` leave them out).

| Folder | A copy of | At commit | Which is |
| --- | --- | --- | --- |
| `PC` | [coop-deluxe/sm64coopdx](https://github.com/coop-deluxe/sm64coopdx) | `8cd6e5977d9f920d51ca71f2c61801d019ed79c6` | v1.5.1; the `pc` base in `apply.py` |
| `VR` | [fulldivegames/sm64coopdx-VR-Standalone-Physics-based](https://github.com/fulldivegames/sm64coopdx-VR-Standalone-Physics-based) | `8bf8dd27e8f217bf146a4bda9c4d8922fb0e2e1e` | v0.9.26; the `vr` base (PC VR and Quest) |
| `Android` | [ManIsCat2/sm64coopdx](https://github.com/ManIsCat2/sm64coopdx) | `99c8d21abe4d24649b508d0f216c4359ed5d2a7a` | branch `android`, Av1.5.1; the `android` base |
| `WiiU` | [efsmert/sm64coopdx-wiiu](https://github.com/efsmert/sm64coopdx-wiiu) joined with coop-deluxe/sm64coopdx | `2e5ff1cec7b7d7c4a51134c756052ca9ae8a0956` and `8cd6e5977d9f920d51ca71f2c61801d019ed79c6` | sm64coopdx v1.5.1 for the Wii U; built by `build-wiiu.yml` |

The first three are what the builds are made from: `python3 fork/apply.py pc game` copies `PC` to `game` and
changes the copy (`vr` takes `VR`, `android` takes `Android`), so the builds go on working if an original
disappears. Each build job checks out only the folder it needs. Where the folder isn't there, `apply.py`
fetches the same commit from the original instead; the line "the game's source is ..." on the run's page
says which it was.

Leave `PC`, `VR` and `Android` as they are: what this project changes in the game is written in `apply.py`, as text that
has to be found in the files exactly. `apply.py` knows what the files of each commit are (`tree` in `BASES`)
and a build whose folder is no longer that says so with a warning on the run's page, and builds from the
folder all the same. To move a base to a newer commit, replace the folder with the files of that commit and
put the commit and its tree (`git rev-parse <commit>^{tree}` in the original) into `BASES`.

### The Wii U folder

The port is sm64coopdx v1.4.1 made to run on a Wii U. `WiiU` is that port with everything the game gained up
to v1.5.1 put into it (206 commits of the game, 9 of the port, joined with `git merge`), so that it is the
version the players of the other builds have: `src/pc/network/version.h` says `v1.5.1`, number 42. Its files
are tree `f3c2baec04a00cd3703dc883a6fc1ec6b22915ec`.

**It builds with the real Wii U compiler. It has not been run**, not on a console and not in an emulator.
See "Building it" for how, and "What was checked" for what stands behind it.

The two sides had changed the same place in 34 files. Each was settled by hand, by one rule: the game's
v1.5.1 code, with what the port needs to run on the console kept (the parts under `TARGET_WII_U`). Where
that rule cost something, a Wii U player gets less than a PC player:

- **Name tags** are the game's v1.5.1 file. The port drew them with less work per frame; that is gone.
- **Screen effects a mod sets** (hue, saturation and the like, new in v1.5) are not drawn. The game does
  them in its OpenGL shader, and the port's shaders have nothing for them.
- **A surface with two textures** gets the coordinates of its first texture for both. v1.5 sends a pair per
  texture; the port's shaders take one.
- **Sounds and music from mods** take another way out than on a PC. The port left them silent: it compiled
  a stand-in (`smlua_audio_utils_wiiu_stub.c`) in place of the game's mod audio, because that plays through
  a library (miniaudio) which opens a sound device of its own, and it has no way to open one on a Wii U. The
  stand-in is gone. miniaudio is now built without a device and without threads, at the rate of the game's
  own sound (32 kHz, stereo), and each time the game has made its sound for a frame it asks miniaudio for
  what the mods are playing and adds it (`smlua_audio_custom_mix`, called from `buffer_audio` in
  `pc_main.c`). A mod's own sequences (`.m64`) go the game's way and are loaded again as well.
  miniaudio keeps some positions as 64-bit numbers that must change in one step; this processor cannot do
  that itself and the compiler hands it to functions somebody has to bring, which `src/pc/wiiu_atomic64.c`
  does.
- **No updater** and no mouse; the port had neither.

Outside those 34 files, some things no longer fitted and were made to. A function the port's level reader
calls and v1.5.1 had removed (`smlua_is_behavior_hooked`) is back. The port's own report of where the player
is now says who it is for, as v1.5.1 wants. The port's files use v1.5.1's names for the window and the
renderer, and its renderer has the name v1.5.1 asks every renderer for. The `Makefile` no longer lists the
files v1.5.1 renamed or dropped. Two files include a header they had only been getting by luck.

**What was checked, before the real compiler.** The machine the joining was done on has no Wii U compiler, so a stand-in was used: clang for the same kind of
processor (32-bit, big-endian PowerPC; `zig cc` 0.13 with its own C library), with the headers of the
Wii U library `wut`, of SDL2 and of zlib. With it the port's own `Makefile` compiled every source file a
Wii U build compiles, about 600. The port as it was before went through the same, to tell what the joining
broke from what the stand-in cannot do.

- Four files fail the same way in the port as it was, and the joining did not touch them. Two need the real
  compiler's C library and were not compiled at all: `src/pc/wiiu_pthread_shim.c`,
  `src/pc/wiiu_reent_shim.c`. Two compile once a complaint that comes from the stand-in's headers is
  switched off: `src/pc/pc_diag_wiiu.c`, `src/pc/gfx/gfx_gx2_window.cpp`.
- Everything else compiles. What the compiled files ask for and nobody provides was compared with the port:
  six names more, all of them from the C and C++ libraries or SDL2 (`fmodf`, `SDL_GetKeyName`, ...).
  Nothing is defined twice.
- The same tree also compiles for Linux with gcc 12, apart from two files whose headers (curl, OpenGL ES)
  this machine lacks.

That finds what does not fit together. It does not find what compiles and is wrong, and a console is where
that shows. The real compiler has since said the same: the two shim files were the only ones of the game it
refused (see below).

#### Building it

`.github/workflows/build-wiiu.yml` ("Build Wii U"). It starts from the Actions tab, or on a push whose commit
message contains `[wiiu]`. It runs in devkitPro's container (devkitPPC r51 with gcc 16.2, wut 1.9.2, SDL2
2.32 for the Wii U) and builds twice, side by side, about five minutes:

| Build | What it is | What comes out |
| --- | --- | --- |
| Realism64 | `WiiU` with `python3 fork/apply.py pc WiiU` run on it: the same changes as on the PC. The mod is compiled in, the other mods are in the mods folder, 30,000 objects, `lumi64` on CoopNet, version `v1.5.1-gore1` | `Realism64-WiiU.zip` |
| SM64 CoopDX | `WiiU` as it is, nothing of this project in it | `SM64CoopDX-WiiU.zip` |

Both become a pre-release, "Wii U test build <number>" with the tag `wiiu-<number>`
(`fork/ci-release-wiiu.sh`). It never becomes the repository's latest release. The compiler's errors, the
last lines of the build and the sizes of what was built are put on the commit as checks ("Wii U (...):
errors" and so on, `fork/ci_report.py`), where they can be read without opening a log.

A zip is the SD card's folders. Unpacked onto the card of a Wii U with Aroma it gives
`wiiu/apps/sm64coopdx/<name>.wuhb`, which is the game with its mods, languages and palettes inside. The
player's own ROM goes to `wiiu/apps/sm64coopdx/roms/baserom.us.z64` (`fork/wiiu-readme.txt` is in the zip
and says so). The game keeps its saves and settings in `wiiu/apps/sm64coopdx/` too, and the Realism64 build
writes its built-in mod there at the first start (181 files, 27 MB; that start takes longer).

The port did not build as it came. Three things it needs were not in its repository, and three more did not
fit today's compiler. All six are settled inside `WiiU`, so the build needs nothing from anywhere else:

- **The sound data.** The port took it from a build of another project (`sm64wiiu`) that needs a ROM. The
  game's repository already has the same data, packed, in `sound/`; the samples and instruments are in the
  form the Wii U wants, the sequences and their bank lists are in the PC's. `tools/wiiu_sound_data.py`
  rewrites those two, and the `Makefile` uses them (`WIIU_SOUND=repo`, the default; `donor` and `assemble`
  are the port's two old ways).
- **CoopNet**, `third_party/coopnet`: the source of [djoslin0/coopnet](https://github.com/djoslin0/coopnet)
  at `187d19d`. What it sends was written for processors that store numbers lowest byte first, and the
  Wii U's stores them the other way round, so it could not have talked to the lobby server. Every number of
  every one of its 20 kinds of message is now turned on the way out and on the way in (`mpacket.cpp`; a
  table of the sizes, checked against the messages by the compiler). The part that asks the system for its
  network cards asks the console instead (`socket.cpp`).
- **libjuice**, `third_party/libjuice`: [paullouisageneau/libjuice](https://github.com/paullouisageneau/libjuice)
  v1.6.2, which CoopNet uses to connect two players directly. The Wii U has IPv4 only, no pipes and no list
  of network cards. `src/wiiu_compat.h` and `.c` give libjuice what is missing; the thread that waits for
  packets looks up every 10 ms instead of being woken through a pipe (`conn_poll.c`); a socket's port is
  chosen and remembered here instead of asked for afterwards, and the console's one address is its list of
  addresses (`udp.c`). Everything is under `__WIIU__`; on other machines the files compile to what they were.
- **Threads.** The port had its own `pthread` functions, written for an older compiler whose C library had
  none. Today's has them, the port's did not compile against it, and they are gone
  (`src/pc/wiiu_pthread_shim.c` is down to `pipe`).
- **The day-night skies.** On the Wii U the game draws the Day Night Cycle mod's 18 skies itself and wants
  them as pictures in `textures/skyboxes/`, which the port's repository does not have. They are inside the
  mod's model file; `tools/wiiu_dnc_skyboxes.py` takes them out when building.
- **One function's type** in `src/pc/pc_diag_wiiu.c`, which differs between versions of the Wii U headers.

What stands behind the network changes, since no console was at hand: CoopNet's messages were run through
the turning on a PC with the turning forced on, and came back as they went in. libjuice was built on Linux
with its Wii U paths switched on and an address as small as the console's, and two ends in one program
found each other and exchanged 20 packets each way, under the compiler's memory checker. Neither says that
a Wii U reaches the lobby server or another player.

Mod sounds and voice chat on the Wii U were written without a console to hear them on. For the sounds,
the same three files of the game were built for a 32-bit big-endian PowerPC (the Wii U's kind of processor),
run in an emulator of that processor, and gave the same samples as on a PC for the mod's `.ogg` files; that
the console then plays them is the part nobody has heard. For voice chat, SDL on the Wii U cannot record, so
`fork_voice.c` reads the GamePad's microphone through the console's own library (`mic`: 32 kHz mono, halved
to the 16 kHz the packets carry). How that library counts what is waiting is taken from how the Cemu
emulator answers it, not from a console; the code was run against a pretend microphone built that way, and
a tone that went in came out of the mixer at the other end. Until now the voices were not mixed into the
Wii U's sound at all (its sound takes another way out in `audio_sdl.c`); they are now.

What is not known about the Realism64 build on a Wii U is everything else: whether it starts, how it runs with 30,000 objects and this mod on that processor
(the program takes about 180 MB of memory before it has loaded anything; the plain port takes 100), and
whether a Wii U and a PC understand each other in one lobby. For the game's own messages the port turns
whatever is 2, 4 or 8 bytes long (`packet_read_write.c`), which is right for a number and wrong for
anything else of that length; nobody has gone through all the messages of v1.5.1 for that.

#### The picture on a console

The first report from a console: sound and controls, and a screen in one flat blue. That blue was the
colour `gfx_gx2_window.cpp` cleared the screen with, so frames were shown and nothing drawn in them
could be seen.

`gfx_gx2_window_start_frame` made the context current and *then* cleared colour and depth. On a console
`GX2ClearColor` and `GX2ClearDepthStencilEx` work with a state of their own and leave the GPU in it;
`GX2SetContextState` has to come after them (the Wii U port of sm64 this renderer comes from, and
libwhb's `WHBGfxClearColor`, both do it in that order). Cemu does not care, which is where this port was
made. The order is now clear, clear, context, render targets, viewport, scissor; and the clear is black.

That this was the cause is a conclusion from reading, not something seen: nobody here has a console. So
the renderer also counts what it does (shaders made and failed, textures, draws, triangles, the last
viewport and scissor) and writes `gfx-report.txt` next to the save file after 300 and after 3600
frames (`gfx_gx2_write_report` in `gfx_gx2.cpp`).

## The icon

`Untitled.png` in the top folder is the picture. `python3 fork/icon/make.py` (needs Pillow) makes every shape
of it into `fork/icon`, and `fork/apply.py` puts those over the game's own; a build only copies. After
changing the picture, run `make.py` again and commit what it wrote.

| Build | Where the icon is |
|---|---|
| Windows, VR Windows | the program (`res/icon.ico`), and its window with it |
| macOS | the app (`res/icon.icns`, a rounded square with a margin; `res/icon.icon` for macOS 26) |
| Linux | the window (64 x 64, built into the program; a Wayland desktop shows none without a `.desktop` file), and `icon.png` in the zip for a launcher of your own |
| Android | the launcher icons (square, round and "adaptive": the picture inside its own background colour) |
| Quest | a launcher icon; the app had none before |

The picture need not be square: it is centred on a square of the colour of its top left corner. It is not
part of the mod (`fork/apply.py` and `site/build.mjs` leave it out).

## The signing key

`signing/gore-fork.p12` (alias and both passwords `gorefork`) is in the repository on purpose: Android only
installs an update over an app signed with the same key, and this way every build has it without a secret
to set up. It also means anyone who can read this repository can sign an app that installs over yours.
For sideloading among friends that is the usual trade; before handing the APKs to strangers, make a new key
and keep it in a repository secret.

## Whose work this is

GORE / Hard-Mode! is by the GORE Team: IncredibleHolc, Cooliokid956, Blocky.cmd, Birdekek, Saniky, Tilly,
Isaac, Frijoles, ProfeJavix and I'mYourCat. In the official game the list of mods says so (the description
at the top of `main.lua`). These builds have no such list, and the names are not shown anywhere in them:
the lines that were at the end of Gore Settings have been taken out. This file is where they are.

The game is SM64 Coop DX by the Coop DX team; the VR builds are fulldivegames' unofficial fork (which calls
itself experimental, tested on Quest 3); the Android build is ManIsCat2's port. None of the three states a
license. The lobby server these builds use by default (`net.coop64.us`) is run by the Coop DX team for the
official game; a build with its own name doesn't show up in their list, but it is their server. Another one
can be set with `coopnet_ip` in the game's config.

The Wii U port is efsmert's (no license stated). Compiled into the Wii U builds, and only those, from source
in this repository: CoopNet by djoslin0, under the GNU AGPL v3, and libjuice by Paul-Louis Ageneau, under
the MPL 2.0. Both are changed for the Wii U as "The Wii U folder" says; their license texts are in
`WiiU/third_party/coopnet/LICENSE` and `WiiU/third_party/libjuice/LICENSE`. (The other builds link the
ready-made CoopNet and libjuice that come with the game.)
