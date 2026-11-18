Realism64 for Linux (64-bit Intel or AMD)

Start it:   ./sm64coopdx
(If it says "Permission denied":   chmod +x sm64coopdx)

Keep the files of this folder together; the folder itself can be anywhere.
(icon.png is the game's icon, for a launcher or menu entry of your own. The window has it by itself.)

It uses these from your system: SDL2, OpenGL, libcurl and zlib. Most desktop systems have them. If the game
says a library can't be found:

    Debian, Ubuntu, Mint:   sudo apt install libsdl2-2.0-0 libcurl4 libgl1 zlib1g
    Fedora:                 sudo dnf install SDL2 libcurl mesa-libGL zlib
    Arch, Manjaro:          sudo pacman -S sdl2 curl libglvnd zlib

It was built on Ubuntu 22.04, so it needs a system of that age or newer (glibc 2.35).

At the first start the game asks for your own Super Mario 64 ROM (US version): drag the file onto its window.
None is included.

Saves, settings and your own mods are in ~/.local/share/sm64coopdx, the same place the official game uses.
