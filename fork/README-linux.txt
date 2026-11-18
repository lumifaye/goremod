Realism64 for linux (64-bit intel or amd)

run ./sm64coopdx. if you get permission denied run chmod +x sm64coopdx first. keep the files together

you need SDL2, OpenGL, libcurl and zlib:

Debian/Ubuntu/Mint: sudo apt install libsdl2-2.0-0 libcurl4 libgl1 zlib1g
Fedora: sudo dnf install SDL2 libcurl mesa-libGL zlib
Arch/Manjaro: sudo pacman -S sdl2 curl libglvnd zlib

you need glibc 2.35 or newer. the game asks for your own Super Mario 64 US ROM the first time you start it because no ROM is included

saves, settings and mods are in ~/.local/share/sm64coopdx. icon.png is there if you want a launcher
