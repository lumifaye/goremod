#ifndef GFX_OPENGL_H
#define GFX_OPENGL_H

#include "gfx_rendering_api.h"

extern struct GfxRenderingAPI gfx_opengl_api;

bool gfx_opengl_check_compatibility(void);
void gfx_opengl_shadow_submit(const float *vertices, size_t count, const float center[3]);
bool gfx_opengl_shadow_ready(void);
void gfx_opengl_experimental_post(int width, int height, bool underwater, const float sun[2], bool sunVisible);

#endif
