Realism64 for Windows: flat screen and PC VR

Run sm64coopdx.exe. Flat screen is the default, and does not require a headset.
To use VR, connect an OpenXR headset and enable VR Mode in the in-game VR
settings; Launch in VR can make it start in VR next time. See VR-GUIDE.txt
for VR controls and troubleshooting. This combined build uses OpenGL, including
in flat mode; DirectX-only hardware is not supported.

Display settings include Experimental Better Graphics, off by default. It adds
per-pixel world-space lighting on normally lit 3D geometry, plus per-pixel
material lighting on textures with bundled normal maps. Fullbright and HUD
remain unchanged by scene lighting. Unusually complex materials may fall back
to the original scene lighting. Circular contact shadows shift with height
and light direction, but are projected decals rather than object silhouettes.
This can cost performance, especially in VR. Turn it off at any time. Existing normal-map
strength and gloss controls adjust the material lighting.

Keep the included files and folders next to the executable. You need your own
legally obtained Super Mario 64 US ROM; one is not included.
