Realism64 for Windows: flat screen and PC VR

Run sm64coopdx.exe. Flat screen is the default, and does not require a headset.
To use VR, connect an OpenXR headset and enable VR Mode in the in-game VR
settings; Launch in VR can make it start in VR next time. See VR-GUIDE.txt
for VR controls and troubleshooting. This combined build uses OpenGL, including
in flat mode; DirectX-only hardware is not supported.

Display settings include Experimental Better Graphics, off by default. It adds
per-pixel world-space lighting on normally lit 3D geometry, plus per-pixel
material lighting on textures with bundled normal maps. Normally lit player
models get an approximate wet sheen above and below water; this is not a true
scene reflection. Flat-screen OpenGL adds subtle screen-space bloom, approximate bright-pixel
sun rays and an underwater camera ripple (including the HUD); these are skipped on multisampled
targets and in VR. Fullbright and HUD
remain unchanged by scene lighting. Unusually complex materials may fall back
to the original scene lighting. A real-time GPU shadow map uses opaque scene geometry from the previous frame,
with filtered shadows in a bounded area. Transparent and cutout materials,
offscreen geometry, and unusually complex materials may not cast or receive
shadows. Compatible opaque geometry also has subtle distance haze, animated
underwater caustic highlights and tint, plus a view-dependent material sheen.
These are approximations, and need a working shadow map. Built-in contact shadow
decals are removed while this setting is on,
even if the GPU shadow map cannot initialize; turn it off to restore them. The
larger shadow map uses more GPU memory and bandwidth. This can cost performance,
especially in VR, and may show a one-frame delay on moving objects. Turn it off at any time. Existing normal-map
strength and gloss controls adjust the material lighting.

Keep the included files and folders next to the executable. You need your own
legally obtained Super Mario 64 US ROM; one is not included.
