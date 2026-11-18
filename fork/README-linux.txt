Realism64 for Linux (64-bit Intel or AMD)

To start the game, run:

    ./sm64coopdx

If you get "Permission denied", run chmod +x sm64coopdx first. Keep everything in this folder together, but you can put the folder wherever you want. icon.png is there if you want to make a launcher or menu entry; the game window already has the icon.

You need SDL2, OpenGL, libcurl and zlib installed. If the game says a library is missing:

    Debian, Ubuntu, Mint:   sudo apt install libsdl2-2.0-0 libcurl4 libgl1 zlib1g
    Fedora:                 sudo dnf install SDL2 libcurl mesa-libGL zlib
    Arch, Manjaro:          sudo pacman -S sdl2 curl libglvnd zlib

This was built on Ubuntu 22.04, so you need a system at least that new (glibc 2.35).

The first time you start the game, drag your own Super Mario 64 US ROM onto the window. There isn't a ROM included.

Your saves, settings and mods are in ~/.local/share/sm64coopdx, the same place the official game uses.
