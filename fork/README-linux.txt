Realism64 for Linux (64-bit Intel or AMD)

Run ./sm64coopdx. If you get permission denied, run chmod +x sm64coopdx first. Keep the files together.

You need SDL2, OpenGL, libcurl and zlib:

Debian/Ubuntu/Mint: sudo apt install libsdl2-2.0-0 libcurl4 libgl1 zlib1g
Fedora: sudo dnf install SDL2 libcurl mesa-libGL zlib
Arch/Manjaro: sudo pacman -S sdl2 curl libglvnd zlib

You need glibc 2.35 or newer. The game asks for your own Super Mario 64 US ROM on first start; no ROM is included.

Saves, settings and mods are in ~/.local/share/sm64coopdx. icon.png is for a launcher if you want one.
