Wii U build - how to use it
===========================

This is for a Wii U that runs homebrew with Aroma. Nobody has started this build on a console yet:
it was built by a machine and has not been tried. If it does not start, nothing on the console is
changed by it; delete the folder from the SD card and it is gone.

1. Unpack this zip onto the SD card of the Wii U, so that the folder "wiiu" of the zip goes into the
   folder "wiiu" that is already on the card. Afterwards the card has

       wiiu/apps/sm64coopdx/<name>.wuhb     the game
       wiiu/apps/sm64coopdx/roms/           your ROM goes here
       wiiu/apps/sm64coopdx/mods/           more mods can go here

2. Put your own Super Mario 64 ROM (US version) into wiiu/apps/sm64coopdx/roms/ as

       baserom.us.z64

   None is included. The game does not start without it; it says so on the screen.

3. Put the card back, start the Wii U. The game is in the Wii U menu.

What is different from the PC version
-------------------------------------
- Sounds and music that a mod brings itself are played through a different path than on the PC. That
  path was built for this version and has not been heard on a console yet.
- Voice chat (Realism64 only): you hear the others. To be heard, switch on "Microphone on" in Options,
  Sound; the microphone is the one in the GamePad. It has not been tried on a console yet either.
- Playing online goes through CoopNet as on the PC, and has not been tried from a Wii U.

If the picture is wrong
-----------------------
The people who work on this version have no Wii U. Five seconds after it starts, and again after about
a minute, the game writes a small text file,

       wiiu/apps/sm64coopdx/gfx-report.txt

with counts of what it drew. If the screen stays one colour (or anything else looks wrong), that file
says which part did not happen: please send it along.

Licenses of what is in it
-------------------------
CoopNet (GNU AGPL v3) and libjuice (MPL 2.0) are compiled into the game. Their source, with the changes
made for the Wii U, and the source of everything else is at
https://github.com/lumifaye/Gore-Hardmode (folders WiiU/third_party/coopnet and WiiU/third_party/libjuice).
