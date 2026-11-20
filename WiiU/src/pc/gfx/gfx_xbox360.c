/* Fast3D software rasterizer for the xSDK tiled scanout. Coordinates passed by
 * gfx_pc use GL's bottom-left viewport origin; scanout rows run top-down. */
#ifdef TARGET_XBOX360
#include "gfx_rendering_api.h"
#include "gfx_cc.h"
#include "gfx_xbox360_window.h"
#include <xsdk/present.h>
#include <xsdk/log.h>
#include <xsdk/texture.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

enum { W = 320, H = 180 };
static uint32_t pixels[H][W]; /* bytes B,G,R,A on Xenon's big endian CPU */
static float depth[H][W];
static int vp[4], sc[4];
static float scale_x, scale_y;
static bool test_z, write_z, decal, blend;
struct ShaderProgram {
    struct CCFeatures f;
    uint64_t hash;
    struct ShaderProgram *next;
};
static struct ShaderProgram *programs, *active;
struct Texture {
    uint8_t *data;
    int w, h;
    unsigned wrap[2];
    bool linear;
};
static struct Texture *textures;
static unsigned count, selected[2], tile;
extern void xbox_set_scanout(void (*fn)(uint32_t, uint32_t, uint32_t));
static void scanout(uint32_t addr, uint32_t w, uint32_t h) {
    XsdkTexture dst;
    if (!w || !h || w > XSDK_TEXTURE_MAX_SIZE || h > XSDK_TEXTURE_MAX_SIZE
        || !NT_SUCCESS(xsdk_texture_init(&dst, XSDK_FORMAT_A8R8G8B8, w, h, 1, true)))
        return;
    xsdk_texture_attach(&dst, xsdk_present_pixels(addr));
    if (w == 1280 && h == 720) {
        static uint32_t rows[4][1280];
        for (int y = 0; y < H; y++) {
            for (int x = 0; x < 1280; x++) rows[0][x] = pixels[y][x / 4];
            for (int r = 1; r < 4; r++) memcpy(rows[r], rows[0], sizeof rows[0]);
            xsdk_texture_upload_rows(&dst, 0, y * 4, 4, rows, sizeof rows[0]);
        }
    } else {
        // The kernel display mode may be 640x480 on an interlaced output.
        static uint32_t row[XSDK_TEXTURE_MAX_SIZE];
        unsigned prev_y = H;
        for (unsigned y = 0; y < h; ++y) {
            unsigned src_y = y * H / h;
            if (src_y != prev_y) {
                for (unsigned x = 0; x < w; ++x) row[x] = pixels[src_y][x * W / w];
                prev_y = src_y;
            }
            xsdk_texture_upload_rows(&dst, 0, y, 1, row, w * sizeof(*row));
        }
    }
    // Distinguish an empty game frame from a presentation problem on the host.
    static unsigned frame;
    static bool saw_color;
    if (!saw_color && ++frame && !(frame & (frame - 1))) {
        for (unsigned y = 0; y < H && !saw_color; ++y)
            for (unsigned x = 0; x < W; ++x)
                if (pixels[y][x] >> 8) { saw_color = true; break; }
        xsdk_log_write("xbox scanout: frame %u uploaded (%ux%u, %s)", frame, w, h,
                       saw_color ? "contains color" : "black");
    }
}
static bool zero_one(void) {
    return true;
}
static void load(struct ShaderProgram *p) {
    active = p;
}
static void unload(struct ShaderProgram *p) {
    if (active == p)
        active = NULL;
}
static struct ShaderProgram *lookup(struct ColorCombiner *c) {
    for (struct ShaderProgram *p = programs; p; p = p->next)
        if (p->hash == c->hash)
            return p;
    return NULL;
}
static struct ShaderProgram *create(struct ColorCombiner *c) {
    struct ShaderProgram *p = calloc(1, sizeof *p);
    if (!p)
        abort();
    gfx_cc_get_features(c, &p->f);
    p->hash = c->hash;
    p->next = programs;
    return active = programs = p;
}
static void info(struct ShaderProgram *p, uint8_t *n, bool t[2]) {
    *n = p->f.num_inputs;
    memcpy(t, p->f.used_textures, sizeof p->f.used_textures);
}
static uint32_t alloc_tex(void) {
    struct Texture *p = realloc(textures, (count + 1) * sizeof *p);
    if (!p)
        abort();
    textures = p;
    textures[count] = (struct Texture) { 0 };
    return count++;
}
static void select_tex(int t, uint32_t id) {
    tile = t;
    selected[t] = id;
}
static void upload(const uint8_t *buf, int w, int h) {
    if (selected[tile] >= count || w <= 0 || h <= 0 || (size_t) w > SIZE_MAX / 4 / h)
        return;
    struct Texture *t = textures + selected[tile];
    size_t len = (size_t) w * h * 4;
    uint8_t *p = realloc(t->data, len);
    if (!p)
        abort();
    memcpy(p, buf, len);
    t->data = p; t->w = w; t->h = h;
}
static void sampler(int t, bool l, uint32_t s, uint32_t v) {
    if (selected[t] >= count) return;
    struct Texture *tex = &textures[selected[t]];
    tex->linear = l;
    tex->wrap[0] = s;
    tex->wrap[1] = v;
}
static int address(int i, int n, unsigned mode) {
    if (mode & 2)
        return i < 0 ? 0 : i >= n ? n - 1 : i;
    int period = mode & 1 ? n * 2 : n;
    i %= period;
    if (i < 0)
        i += period;
    return i < n ? i : period - 1 - i;
}
static void sample(int slot, float u, float v, float out[4]) {
    if (selected[slot] >= count)
        return;
    struct Texture *t = textures + selected[slot];
    if (!t->data)
        return;
    u = u * t->w - (t->linear ? 0.5f : 0);
    v = v * t->h - (t->linear ? 0.5f : 0);
    int i = floorf(u), j = floorf(v);
    float fx = u - i, fy = v - j;
    int steps = t->linear ? 2 : 1;
    for (int y = 0; y < steps; y++)
        for (int x = 0; x < steps; x++) {
            int ix = address(i + x, t->w, t->wrap[0]), iy = address(j + y, t->h, t->wrap[1]);
            float weight = steps == 1 ? 1 : (x ? fx : 1 - fx) * (y ? fy : 1 - fy);
            for (int k = 0; k < 4; k++)
                out[k] += t->data[4 * (iy * t->w + ix) + k] * (weight / 255.f);
        }
}
static float sat(float a) {
    return fmaxf(0, fminf(1, a));
}
extern uint8_t gVertexColor[3]; // gfx_pc: ambient light-map modulation

static bool shade(int x, int y, const float *vary) {
    struct CCFeatures *f = &active->f;
    float reg[SHADER_NOISE + 1][4] = { { 0 } };
    const float *light_uv = vary + 2 * (f->used_textures[0] + f->used_textures[1]) + 4 * f->opt_fog;
    for (int i = 0; i < 2; i++)
        if (f->used_textures[i]) {
            int id = i ? SHADER_TEXEL1 : SHADER_TEXEL0;
            const float *uv = (i == 1 && f->opt_light_map) ? light_uv : vary;
            sample(i, uv[0], uv[1], reg[id]);
            if (i == 1 && f->opt_light_map) {
                for (int k = 0; k < 3; k++) {
                    reg[SHADER_TEXEL0][k] *= gVertexColor[k] / 255.0f;
                    reg[id][k] *= 1.0f + reg[id][k];
                }
            }
            vary += 2;
            for (int k = 0; k < 4; k++)
                reg[id + 1][k] = reg[id][3];
        }
    const float *fog = vary;
    if (f->opt_fog)
        vary += 4;
    if (f->opt_light_map)
        vary += 2;
    for (int i = 1; i <= f->num_inputs; i++) {
        for (int k = 0; k < 3; k++)
            reg[i][k] = *vary++;
        reg[i][3] = f->opt_alpha ? *vary++ : 1;
    }
    for (int k = 0; k < 4; k++) {
        reg[SHADER_1][k] = 1;
        reg[SHADER_NOISE][k] = ((x * 73 + y * 97) & 255) / 255.f;
    }
    float color[4];
    for (int cycle = 0; cycle <= f->opt_2cycle; cycle++) {
        for (int k = 0; k < 4; k++) {
            const uint8_t *cmd = f->shader_cmds + 8 * cycle + (k == 3 ? 4 : 0);
            color[k] = sat((reg[cmd[0]][k] - reg[cmd[1]][k]) * reg[cmd[2]][k] + reg[cmd[3]][k]);
        }
        for (int k = 0; k < 4; k++) {
            reg[SHADER_COMBINED][k] = color[k];
            reg[SHADER_COMBINEDA][k] = color[3];
        }
    }
    float a = f->opt_alpha ? color[3] : 1;
    if (f->opt_texture_edge && f->opt_alpha) {
        if (a <= 0.3f) return false;
        a = 1.0f;
    }
    uint32_t old = pixels[y][x], result = 255;
    for (int k = 0; k < 3; k++) {
        float c = color[k];
        if (f->opt_fog)
            c += (fog[k] - c) * fog[3];
        int shift = 8 * (k + 1);
        if (blend)
            c = c * a + ((old >> shift) & 255) * ((1 - a) / 255.f);
        result |= (uint32_t) (sat(c) * 255.f) << shift;
    }
    pixels[y][x] = result;
    return true;
}
static void rasterize(const float *buf, size_t stride) {
    float x[3], y[3], q[3], z[3];
    for (int i = 0; i < 3; i++) {
        const float *v = buf + i * stride;
        if (v[3] <= 0)
            return;
        q[i] = 1 / v[3];
        z[i] = v[2] * q[i];
        x[i] = (vp[0] + (1 + v[0] * q[i]) * vp[2] * .5f) * scale_x;
        y[i] = H - (vp[1] + (1 + v[1] * q[i]) * vp[3] * .5f) * scale_y;
    }
    float area = (x[1] - x[0]) * (y[2] - y[0]) - (y[1] - y[0]) * (x[2] - x[0]);
    if (!area)
        return;
    int left = fmaxf(fmaxf(0, sc[0] * scale_x), floorf(fminf(x[0], fminf(x[1], x[2]))));
    int right = fminf(fminf(W, (sc[0] + sc[2]) * scale_x), ceilf(fmaxf(x[0], fmaxf(x[1], x[2]))));
    int top = fmaxf(fmaxf(0, H - (sc[1] + sc[3]) * scale_y), floorf(fminf(y[0], fminf(y[1], y[2]))));
    int bottom = fminf(fminf(H, H - sc[1] * scale_y), ceilf(fmaxf(y[0], fmaxf(y[1], y[2]))));
    for (int j = top; j < bottom; j++)
        for (int i = left; i < right; i++) {
            float dx = i + .5f - x[0], dy = j + .5f - y[0];
            float b = (dx * (y[2] - y[0]) - dy * (x[2] - x[0])) / area,
                  c = ((x[1] - x[0]) * dy - (y[1] - y[0]) * dx) / area, a = 1 - b - c;
            if (a < 0 || b < 0 || c < 0)
                continue;
            float d = a * z[0] + b * z[1] + c * z[2] - (decal ? .0001f : 0);
            if (d < 0 || d > 1 || (test_z && d > depth[j][i]))
                continue;
            a *= q[0];
            b *= q[1];
            c *= q[2];
            float norm = 1 / (a + b + c), vary[44];
            for (size_t k = 4; k < stride; k++)
                vary[k - 4] = (a * buf[k] + b * buf[stride + k] + c * buf[stride * 2 + k]) * norm;
            if (shade(i, j, vary) && test_z && write_z)
                depth[j][i] = d;
        }
}

static void draw(float *buf, size_t len, size_t tris) {
    if (!active || !tris)
        return;
    const struct CCFeatures *f = &active->f;
    const size_t stride = 4 + 2 * (f->used_textures[0] + f->used_textures[1]) + 4 * f->opt_fog
                          + 2 * f->opt_light_map + (3 + f->opt_alpha) * f->num_inputs;
    if (stride > 48 || len / stride / 3 != tris || len % (stride * 3))
        return;
    for (size_t t = 0; t < tris; t++, buf += 3 * stride) {
        if (buf[2] >= 0 && buf[stride + 2] >= 0 && buf[2 * stride + 2] >= 0) {
            rasterize(buf, stride);
            continue;
        }
        // Clip against z=0 in homogeneous space before dividing by w. A
        // crossing triangle becomes either one triangle or a four-vertex fan.
        float poly[4 * 48];
        unsigned n = 0;
        const float *prev = buf + 2 * stride;
        for (int i = 0; i < 3; i++) {
            const float *v = buf + i * stride;
            if ((v[2] >= 0) != (prev[2] >= 0)) {
                float blend = prev[2] / (prev[2] - v[2]);
                for (size_t k = 0; k < stride; k++)
                    poly[n * stride + k] = prev[k] + blend * (v[k] - prev[k]);
                poly[n++ * stride + 2] = 0;
            }
            if (v[2] >= 0)
                memcpy(poly + n++ * stride, v, stride * sizeof(float));
            prev = v;
        }
        if (n >= 3)
            rasterize(poly, stride);
        if (n == 4) {
            memcpy(poly + stride, poly, stride * sizeof(float));
            rasterize(poly + stride, stride);
        }
    }
}
static void viewport(int x, int y, int w, int h) {
    memcpy(vp, (int[]) { x, y, w, h }, sizeof vp);
}
static void scissor(int x, int y, int w, int h) {
    memcpy(sc, (int[]) { x, y, w, h }, sizeof sc);
}
static void resize(void) {
    uint32_t w, h;
    gfx_xbox360_window.get_dimensions(&w, &h);
    if (!w || !h) return;
    scale_x = (float)W / w;
    scale_y = (float)H / h;
    viewport(0, 0, w, h);
    scissor(0, 0, w, h);
}
static void init(void) {
    resize();
    xbox_set_scanout(scanout);
}
static void start(void) {
    memset(pixels, 0, sizeof pixels);
    for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++)
            depth[y][x] = 1;
}
static void shutdown(void) {
    xbox_set_scanout(NULL);
    while (count)
        free(textures[--count].data);
    free(textures);
    textures = NULL;
    while (programs) {
        active = programs->next;
        free(programs);
        programs = active;
    }
}
static void set_test(bool v) {
    test_z = v;
}
static void set_write(bool v) {
    write_z = v;
}
static void set_decal(bool v) {
    decal = v;
}
static void set_blend(bool v) {
    blend = v;
}
static void noop(void) {
}
static const char *name(void) {
    return "Xbox 360 software";
}
struct GfxRenderingAPI gfx_xbox360_api = { zero_one,  unload,    load,       create,   lookup,
                                           info,      alloc_tex, select_tex, upload,   sampler,
                                           set_test,  set_write, set_decal,  viewport, scissor,
                                           set_blend, draw,      init,       resize,   start,
                                           noop,      noop,      name,       shutdown };
#endif
