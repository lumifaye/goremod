Wii U build - how to use it
===========================

You need a Wii U running homebrew with Aroma. Console testing is limited, so this build might not work.

1. Unzip it onto your SD card, merging the zip's "wiiu" folder with the one already on the card. You should have:

       wiiu/apps/sm64coopdx/<name>.wuhb     the game
       wiiu/apps/sm64coopdx/roms/           your ROM goes here
       wiiu/apps/sm64coopdx/mods/           more mods can go here

2. Put your own Super Mario 64 US ROM here:

       wiiu/apps/sm64coopdx/roms/baserom.us.z64

   No ROM is included. The game won't start without it.

3. Put the card back in the Wii U and start it. The game should be in the Wii U menu.

What is different from PC
-------------------------
- Mod sounds and music use a different path from PC. It hasn't been heard on a console yet.
- Voice chat (Realism64 only): you can hear other players. To talk, turn on "Microphone on" in Options > Sound. It uses the GamePad microphone and hasn't been tested on a console yet.
- Online play uses CoopNet like PC. That hasn't been tested from a Wii U either.

If the picture is wrong
-----------------------
About five seconds after starting, and again after about a minute, the game writes:

       wiiu/apps/sm64coopdx/gfx-report.txt

If the screen stays one colour or something else looks wrong, please send that file along so we can see what happened.

Licenses
--------
CoopNet (GNU AGPL v3) and libjuice (MPL 2.0) are compiled into the game. Their source and the Wii U changes, along with the rest of the source, are at https://github.com/lumifaye/Gore-Hardmode (WiiU/third_party/coopnet and WiiU/third_party/libjuice).
