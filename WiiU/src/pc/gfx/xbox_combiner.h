/* Compile a Fast3D program once, not once per fragment. Emit a small Vulkan
 * SPIR-V module using the game's actual batch layout. xSDK's native compiler
 * lowers it to a Xenos shader container (no GLSL compiler on the console). */
#ifndef XBOX_COMBINER_H
#define XBOX_COMBINER_H
#include <xsdk/xsc.h>
#include <xsdk/shader.h>
#include <string.h>
#include "gfx_cc.h"

typedef struct {
    unsigned words[2048], n, next;
    XsdkVertexElement layout[16];
    unsigned elements, stride;
} XboxModule;
static void xb_emit(XboxModule *m, unsigned op, const unsigned *args, unsigned n) {
    m->words[m->n++] = ((n + 1) << 16) | op;
    memcpy(&m->words[m->n], args, n * sizeof(*args));
    m->n += n;
}
#define INST(op, ...)                                                                                  \
    xb_emit(m, op, (const unsigned[]) { __VA_ARGS__ },                                                 \
            sizeof((const unsigned[]) { __VA_ARGS__ }) / sizeof(unsigned))
// Fixed type/constant IDs; variables and SSA results are allocated above these.
enum {
    XB_VOID = 1,
    XB_FN,
    XB_FLOAT,
    XB_V2,
    XB_V3,
    XB_V4,
    XB_BOOL,
    XB_IMAGE,
    XB_SAMP,
    XB_PSAMP,
    XB_ZERO,
    XB_ONE,
    XB_ZERO4,
    XB_ONE4,
    XB_THRESHOLD,
    XB_MAIN,
    XB_GLSL,
    XB_INPUT = 20,
    XB_OUTPUT = 24,
    XB_FIRST = 32
};
static unsigned xb_var(XboxModule *m, unsigned ptr, unsigned storage, unsigned id) {
    INST(59, ptr, id, storage);
    return id;
}
static unsigned xb_load(XboxModule *m, unsigned type, unsigned var) {
    unsigned id = m->next++;
    INST(61, type, id, var);
    return id;
}
static unsigned xb_math(XboxModule *m, unsigned op, unsigned type, unsigned a, unsigned b) {
    unsigned id = m->next++;
    INST(op, type, id, a, b);
    return id;
}
static unsigned xb_alpha(XboxModule *m, unsigned v) {
    unsigned id = m->next++;
    INST(79, XB_V4, id, v, v, 3, 3, 3, 3);
    return id;
}
static void xb_const(XboxModule *m, unsigned id, float value) {
    unsigned bits;
    memcpy(&bits, &value, 4);
    INST(43, XB_FLOAT, id, bits);
}
static void xb_module(XboxModule *m, const struct CCFeatures *f, bool ps) {
    // Every input location is tightly packed in the same order as gfx_sp_tri1.
    unsigned size[16] = { 4 }, n = 1, uv[2] = { 0 }, fog = 0, lm = 0, colors[9] = { 0 };
    for (unsigned i = 0; i < 2; i++)
        if (f->used_textures[i]) {
            uv[i] = n;
            size[n++] = 2;
        }
    if (f->opt_fog) {
        fog = n;
        size[n++] = 4;
    }
    if (f->opt_light_map) {
        lm = n;
        size[n++] = 2;
    }
    for (int i = 1; i <= f->num_inputs; i++) {
        colors[i] = n;
        size[n++] = 3 + f->opt_alpha;
    }
    memset(m, 0, sizeof(*m));
    m->n = 5;
    m->next = XB_FIRST;
    m->words[0] = 0x07230203;
    m->words[1] = 0x00010000;
    unsigned in[16] = { 0 }, out[16] = { 0 }, v[16] = { 0 }, tex[2] = { 0 }, coord = 0;
    unsigned entry[48] = { ps ? 4 : 0, XB_MAIN, 0x6e69616d, 0 }, e = 4;
    for (unsigned i = 0; i < n; i++) {
        m->layout[i] = (XsdkVertexElement) { .usage = i == 0   ? XSDK_USAGE_POSITION
                                                      : i == 1 ? XSDK_USAGE_COLOR
                                                               : XSDK_USAGE_TEXCOORD,
                                             .usage_index = i > 2 ? i - 2 : 0,
                                             .format = XSDK_VERTEX_FLOAT1 + size[i] - 1,
                                             .offset_bytes = m->stride };
        m->stride += 4 * size[i];
        if (!ps || i)
            entry[e++] = in[i] = m->next++;
        if (!ps || !i)
            entry[e++] = out[i] = m->next++;
    }
    m->elements = n;
    if (ps && f->opt_noise)
        entry[e++] = coord = m->next++;
    INST(17, 1);
    INST(11, XB_GLSL, 0x4c534c47, 0x6474732e, 0x3035342e, 0); // GLSL.std.450
    INST(14, 0, 1);
    xb_emit(m, 15, entry, e);
    if (ps)
        INST(16, XB_MAIN, 7);
    for (unsigned i = 0; i < n; i++) {
        if (in[i])
            INST(71, in[i], 30, ps ? i - 1 : i);
        if (out[i]) {
            if (!ps && !i) {
                INST(71, out[i], 11, 0);
            } else {
                INST(71, out[i], 30, ps ? 0 : i - 1);
            }
        }
    }
    if (coord)
        INST(71, coord, 11, 15);
    for (unsigned i = 0; i < 2; i++)
        if (ps && uv[i]) {
            tex[i] = m->next++;
            INST(71, tex[i], 34, 0);
            INST(71, tex[i], 33, i);
        }
    // Lightmap ambient multiplier is dynamic, not part of the shader key.
    unsigned block = m->next++, pblock = m->next++, pvec = m->next++, amb = m->next++, it = m->next++,
             iz = m->next++;
    if (ps && lm) {
        INST(71, block, 2);
        INST(72, block, 0, 35, 0);
    }
    INST(19, XB_VOID);
    INST(33, XB_FN, XB_VOID);
    INST(22, XB_FLOAT, 32);
    INST(20, XB_BOOL);
    for (unsigned k = 2; k <= 4; k++) {
        INST(23, XB_V2 + k - 2, XB_FLOAT, k);
        INST(32, XB_INPUT + k - 2, 1, XB_V2 + k - 2);
        INST(32, XB_OUTPUT + k - 2, 3, XB_V2 + k - 2);
    }
    INST(25, XB_IMAGE, XB_FLOAT, 1, 0, 0, 0, 1, 0);
    INST(27, XB_SAMP, XB_IMAGE);
    INST(32, XB_PSAMP, 0, XB_SAMP);
    xb_const(m, XB_ZERO, 0);
    xb_const(m, XB_ONE, 1);
    xb_const(m, XB_THRESHOLD, 0.3f);
    INST(44, XB_V4, XB_ZERO4, XB_ZERO, XB_ZERO, XB_ZERO, XB_ZERO);
    INST(44, XB_V4, XB_ONE4, XB_ONE, XB_ONE, XB_ONE, XB_ONE);
    unsigned noiseX = m->next++, noiseY = m->next++;
    if (coord) {
        xb_const(m, noiseX, 73.0f / 256);
        xb_const(m, noiseY, 97.0f / 256);
    }
    if (ps && lm) {
        INST(30, block, XB_V4);
        INST(32, pblock, 9, block);
        INST(32, pvec, 9, XB_V4);
        INST(21, it, 32, 1);
        INST(43, it, iz, 0);
        xb_var(m, pblock, 9, amb);
    }
    for (unsigned i = 0; i < n; i++) {
        if (in[i])
            xb_var(m, XB_INPUT + size[i] - 2, 1, in[i]);
        if (out[i])
            xb_var(m, XB_OUTPUT + size[i] - 2, 3, out[i]);
    }
    if (coord)
        xb_var(m, XB_INPUT + 2, 1, coord);
    for (unsigned i = 0; i < 2; i++)
        if (tex[i])
            xb_var(m, XB_PSAMP, 0, tex[i]);
    INST(54, XB_VOID, XB_MAIN, 0, XB_FN);
    INST(248, m->next++);
    for (unsigned i = 0; i < n; i++)
        if (in[i]) {
            v[i] = xb_load(m, XB_V2 + size[i] - 2, in[i]);
            if (!ps)
                INST(62, out[i], v[i]);
        }
    if (ps) {
        unsigned reg[SHADER_NOISE + 1];
        for (unsigned i = 0; i <= SHADER_NOISE; i++)
            reg[i] = XB_ZERO4;
        reg[SHADER_1] = XB_ONE4;
        for (int i = 1; i <= f->num_inputs; i++) {
            reg[i] = v[colors[i]];
            if (!f->opt_alpha) {
                unsigned id = m->next++;
                INST(80, XB_V4, id, reg[i], XB_ONE);
                reg[i] = id;
            }
        }
        for (unsigned i = 0; i < 2; i++)
            if (tex[i]) {
                unsigned s = xb_load(m, XB_SAMP, tex[i]), t = m->next++;
                INST(87, XB_V4, t, s, v[i && lm ? lm : uv[i]]);
                unsigned slot = i ? SHADER_TEXEL1 : SHADER_TEXEL0;
                reg[slot] = t;
                reg[slot + 1] = xb_alpha(m, t);
            }
        if (lm && tex[1]) {
            unsigned addr = m->next++;
            INST(65, pvec, addr, amb, iz);
            unsigned light = xb_load(m, XB_V4, addr);
            reg[SHADER_TEXEL0] = xb_math(m, 133, XB_V4, reg[SHADER_TEXEL0], light);
            unsigned t = reg[SHADER_TEXEL1], boost = xb_math(m, 129, XB_V4, XB_ONE4, t);
            unsigned scaled = xb_math(m, 133, XB_V4, t, boost), rgb = m->next++;
            INST(79, XB_V4, rgb, scaled, t, 0, 1, 2, 7);
            reg[SHADER_TEXEL1] = rgb;
        }
        if (coord) {
            unsigned c = xb_load(m, XB_V4, coord), x = m->next++, y = m->next++;
            INST(81, XB_FLOAT, x, c, 0);
            INST(81, XB_FLOAT, y, c, 1);
            unsigned a = xb_math(m, 133, XB_FLOAT, x, noiseX), b = xb_math(m, 133, XB_FLOAT, y, noiseY);
            unsigned sum = xb_math(m, 129, XB_FLOAT, a, b), fr = m->next++, nv = m->next++;
            INST(12, XB_FLOAT, fr, XB_GLSL, 10, sum);
            INST(80, XB_V4, nv, fr, fr, fr, fr);
            reg[SHADER_NOISE] = nv;
        }
        unsigned color = XB_ZERO4;
        for (int cy = 0; cy <= f->opt_2cycle; cy++) {
            unsigned result[2] = { 0, XB_ONE4 };
            for (int k = 0; k <= f->opt_alpha; k++) {
                const uint8_t *cmd = f->shader_cmds + cy * 8 + k * 4;
                unsigned val = reg[cmd[3]];
                if (cmd[2] && cmd[0] != cmd[1]) {
                    unsigned diff = reg[cmd[0]];
                    if (cmd[1])
                        diff = xb_math(m, 131, XB_V4, diff, reg[cmd[1]]);
                    val = xb_math(m, 133, XB_V4, diff, reg[cmd[2]]);
                    if (cmd[3])
                        val = xb_math(m, 129, XB_V4, val, reg[cmd[3]]);
                }
                unsigned cl = m->next++;
                INST(12, XB_V4, cl, XB_GLSL, 43, val, XB_ZERO4, XB_ONE4);
                result[k] = cl;
            }
            color = m->next++;
            INST(79, XB_V4, color, result[0], result[1], 0, 1, 2, 7);
            reg[SHADER_COMBINED] = color;
            reg[SHADER_COMBINEDA] = xb_alpha(m, color);
        }
        if (f->opt_alpha && f->opt_texture_edge) {
            unsigned a = m->next++, cond = m->next++, kill = m->next++, done = m->next++;
            INST(81, XB_FLOAT, a, color, 3);
            INST(188, XB_BOOL, cond, a, XB_THRESHOLD);
            INST(247, done, 0);
            INST(250, cond, kill, done);
            INST(248, kill);
            INST(252);
            INST(248, done);
            unsigned opaque = m->next++;
            INST(79, XB_V4, opaque, color, XB_ONE4, 0, 1, 2, 7);
            color = opaque;
        }
        if (fog) {
            unsigned mix = m->next++, alpha = xb_alpha(m, v[fog]);
            INST(12, XB_V4, mix, XB_GLSL, 46, color, v[fog], alpha);
            unsigned rgb = m->next++;
            INST(79, XB_V4, rgb, mix, color, 0, 1, 2, 7);
            color = rgb;
        }
        INST(62, out[0], color);
    }
    INST(253);
    INST(56);
    m->words[3] = m->next;
}
#undef INST
#endif
