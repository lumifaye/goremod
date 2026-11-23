#ifndef GFX_SHADOW_RANGE_H
#define GFX_SHADOW_RANGE_H
#include <stdbool.h>
// Conservative caster filtering: keep a triangle if its bounding box can
// intersect the capture volume, including very large level polygons whose
// vertices are all outside but whose interior crosses the volume.
static inline bool gfx_shadow_triangle_in_range(const float a[3], const float b[3],
                                                const float c[3], const float center[3], float radius) {
    for (int axis = 0; axis < 3; ++axis) {
        float low = center[axis] - radius, high = center[axis] + radius;
        if ((a[axis] < low && b[axis] < low && c[axis] < low) ||
            (a[axis] > high && b[axis] > high && c[axis] > high)) return false;
    }
    return true;
}
#endif
