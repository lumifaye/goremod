#ifndef GFX_EXPERIMENTAL_SUN_H
#define GFX_EXPERIMENTAL_SUN_H
#include <math.h>
#include <stdbool.h>
/* Project the same fixed world-space light used by enhanced scene lighting.
 * This is a screen-space approximation, not a depth-aware volumetric sun. */
static inline bool gfx_experimental_sun_position(const float eye[3], const float focus[3], float fov, float aspect, float uv[2]) {
    float f[3]={focus[0]-eye[0],focus[1]-eye[1],focus[2]-eye[2]};
    float len=sqrtf(f[0]*f[0]+f[1]*f[1]+f[2]*f[2]);
    if (!isfinite(len) || len<0.0001f || !isfinite(fov) || fov<5.0f || fov>150.0f || !isfinite(aspect) || aspect<=0.0f) return false;
    for (int i=0;i<3;i++) f[i]/=len;
    float horizontal=sqrtf(f[0]*f[0]+f[2]*f[2]);
    if (horizontal<0.0001f) return false;
    float right[3]={-f[2]/horizontal,0.0f,f[0]/horizontal};
    float up[3]={right[1]*f[2]-right[2]*f[1],right[2]*f[0]-right[0]*f[2],right[0]*f[1]-right[1]*f[0]};
    const float sun[3]={-0.35f,0.80f,0.48f};
    float forward=sun[0]*f[0]+sun[1]*f[1]+sun[2]*f[2];
    if (forward<=0.001f) return false;
    float tanhalf=tanf(fov*0.00872664626f);
    uv[0]=0.5f+0.5f*(sun[0]*right[0]+sun[1]*right[1]+sun[2]*right[2])/(forward*tanhalf*aspect);
    uv[1]=0.5f+0.5f*(sun[0]*up[0]+sun[1]*up[1]+sun[2]*up[2])/(forward*tanhalf);
    return isfinite(uv[0]) && isfinite(uv[1]) && uv[0]>0.0f && uv[0]<1.0f && uv[1]>0.0f && uv[1]<1.0f;
}
#endif
