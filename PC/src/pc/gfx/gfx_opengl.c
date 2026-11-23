#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#ifndef _LANGUAGE_C
# define _LANGUAGE_C
#endif
#include <PR/gbi.h>

#ifdef __MINGW32__
# define FOR_WINDOWS 1
#else
# define FOR_WINDOWS 0
#endif

#if FOR_WINDOWS || defined(OSX_BUILD)
# define GLEW_STATIC
# include <GL/glew.h>
#endif

#define GL_GLEXT_PROTOTYPES 1

#include <SDL2/SDL.h>
#ifdef USE_GLES
#include <SDL2/SDL_opengles2.h>
#else
#include <SDL2/SDL_opengl.h>
#endif

#include "../platform.h"
#include "../configfile.h"
#include "gfx_cc.h"
#include "gfx_normal_maps.h"
#include "gfx_rendering_api.h"
#include "gfx_experimental_post.h"
#include "gfx_shadow_map.h"
#include "gfx_pc.h"

#define TEX_CACHE_STEP 512

struct ShaderProgram {
    uint64_t hash;
    GLuint opengl_program_id;
    uint8_t num_inputs;
    bool used_textures[2];
    uint8_t num_floats;
    GLint attrib_locations[8];
    GLint uniform_locations[9];
    uint8_t attrib_sizes[8];
    uint8_t num_attribs;
    bool used_noise;
    bool used_lightmap;
    bool world_geometry;
    GLint shadow_sampler, shadow_center;
    GLint environment_eye_location, environment_state_location;
    GLint normal_sampler[2], normal_enabled[2], normal_strength, normal_gloss, normal_better;
};

struct GLTexture {
    GLuint gltex;
    GLuint normal_gltex;
    bool has_normal, normal_clamp_edges;
    GLenum wrap_s, wrap_t;
    GLfloat size[2];
    bool filter;
};

static struct ShaderProgram shader_program_pool[CC_MAX_SHADERS];
static uint8_t shader_program_pool_size = 0;
static uint8_t shader_program_pool_index = 0;
static GLuint opengl_vbo;
static GLuint opengl_vao;

static int tex_cache_size = 0;
static int num_textures = 0;
static struct GLTexture *tex_cache = NULL;

static struct ShaderProgram *opengl_prg = NULL;
static struct GLTexture *opengl_tex[2];
static int opengl_curtex = 0;

static uint32_t frame_count;
static float sEnvironmentEye[3];
static float sEnvironmentWater, sEnvironmentTime;
static bool sEnvironmentUnderwater;
void gfx_opengl_set_environment(const float eye[3], float waterLevel, bool underwater, float time) {
    memcpy(sEnvironmentEye,eye,sizeof(sEnvironmentEye));
    sEnvironmentWater=waterLevel; sEnvironmentUnderwater=underwater; sEnvironmentTime=time;
}


static bool gfx_opengl_z_is_from_0_to_1(void) {
    return false;
}

static void gfx_opengl_vertex_array_set_attribs(struct ShaderProgram *prg) {
    size_t num_floats = prg->num_floats;
    size_t pos = 0;

    for (int i = 0; i < prg->num_attribs; i++) {
        glEnableVertexAttribArray(prg->attrib_locations[i]);
        glVertexAttribPointer(prg->attrib_locations[i], prg->attrib_sizes[i], GL_FLOAT, GL_FALSE, num_floats * sizeof(float), (void *) (pos * sizeof(float)));
        pos += prg->attrib_sizes[i];
    }
}

static inline void gfx_opengl_set_shader_uniforms(struct ShaderProgram *prg) {
    if (prg->used_noise) { glUniform1f(prg->uniform_locations[4], (float)frame_count); }
    if (prg->used_lightmap) { glUniform3f(prg->uniform_locations[5], gVertexColor[0] / 255.0f, gVertexColor[1] / 255.0f, gVertexColor[2] / 255.0f); }
    if (prg->world_geometry) {
        glUniform1iv(prg->uniform_locations[6], SHADER_FLAG_MAX, gShaderFlags);
        glUniform1fv(prg->uniform_locations[7], SHADER_FLAG_MAX, gShaderFlagValues);
    }

    glUniform1i(prg->uniform_locations[8], configFiltering);
}

static bool gfx_opengl_normal_map_has_discontinuous_edges(
    const uint8_t *rgba,
    int width,
    int height
) {
    if (rgba == NULL || width < 2 || height < 2) return false;

    double error = 0.0;
    size_t samples = 0;
    for (int x = 0; x < width; x++) {
        const size_t top = (size_t)x * 4;
        const size_t bottom = ((size_t)(height - 1) * (size_t)width + (size_t)x) * 4;
        for (int channel = 0; channel < 3; channel++) {
            const double delta = (double)rgba[top + channel] - (double)rgba[bottom + channel];
            error += delta * delta;
            samples++;
        }
    }
    for (int y = 0; y < height; y++) {
        const size_t left = ((size_t)y * (size_t)width) * 4;
        const size_t right = ((size_t)y * (size_t)width + (size_t)(width - 1)) * 4;
        for (int channel = 0; channel < 3; channel++) {
            const double delta = (double)rgba[left + channel] - (double)rgba[right + channel];
            error += delta * delta;
            samples++;
        }
    }
    if (samples == 0) return false;
    // A repeated normal texture whose opposite borders differ by more than
    // roughly 32 intensity levels per channel will produce a visible seam
    // when bilinear filtering crosses the wrap boundary. Clamp only those
    // authored discontinuities; tileable maps retain their requested wrap.
    return (error / (double)samples) > (32.0 * 32.0);
}

static inline void gfx_opengl_set_texture_uniforms(struct ShaderProgram *prg, const int tile) {
    if (prg && prg->used_textures[tile] && opengl_tex[tile]) {
        glUniform2f(prg->uniform_locations[tile*2 + 0], opengl_tex[tile]->size[0], opengl_tex[tile]->size[1]);
        glUniform1i(prg->uniform_locations[tile*2 + 1], opengl_tex[tile]->filter);
        if (prg->normal_sampler[tile] >= 0) {
            bool enabled = configBetterGraphics && opengl_tex[tile]->has_normal;
            GLint active; glGetIntegerv(GL_ACTIVE_TEXTURE, &active);
            glActiveTexture(GL_TEXTURE3 + tile);
            glBindTexture(GL_TEXTURE_2D, enabled ? opengl_tex[tile]->normal_gltex : 0);
            glUniform1i(prg->normal_sampler[tile], 3 + tile);
            glUniform1i(prg->normal_enabled[tile], enabled);
            glActiveTexture(active);
        }
    }
}

static void gfx_opengl_unload_shader(struct ShaderProgram *old_prg) {
    if (old_prg != NULL) {
        for (int i = 0; i < old_prg->num_attribs; i++)
            glDisableVertexAttribArray(old_prg->attrib_locations[i]);
        if (old_prg == opengl_prg)
            opengl_prg = NULL;
    } else {
        opengl_prg = NULL;
    }
}

static void gfx_opengl_load_shader(struct ShaderProgram *new_prg) {
    opengl_prg = new_prg;
    glUseProgram(new_prg->opengl_program_id);
    gfx_opengl_vertex_array_set_attribs(new_prg);
    gfx_opengl_set_shader_uniforms(new_prg);
    if (new_prg->normal_strength >= 0) glUniform1f(new_prg->normal_strength, 0.75f);
    if (new_prg->normal_gloss >= 0) glUniform1f(new_prg->normal_gloss, 0.425f);
    if (new_prg->normal_better >= 0) glUniform1i(new_prg->normal_better, 1);
    gfx_opengl_set_texture_uniforms(new_prg, 0);
    gfx_opengl_set_texture_uniforms(new_prg, 1);
    if (new_prg->shadow_sampler >= 0 && sShadowMap.valid) {
        GLint active; glGetIntegerv(GL_ACTIVE_TEXTURE,&active);
        glActiveTexture(GL_TEXTURE2); glBindTexture(GL_TEXTURE_2D,sShadowMap.texture);
        glUniform1i(new_prg->shadow_sampler,2);
        glUniform3f(new_prg->shadow_center,sShadowMap.center[0],sShadowMap.center[1],sShadowMap.center[2]);
        glUniform3f(new_prg->environment_eye_location,sEnvironmentEye[0],sEnvironmentEye[1],sEnvironmentEye[2]);
        glUniform3f(new_prg->environment_state_location,sEnvironmentTime,sEnvironmentUnderwater ? 1.0f : 0.0f,sEnvironmentWater);
        glActiveTexture(active);
    }
}

static void append_str(char *buf, size_t *len, const char *str) {
    while (*str != '\0') buf[(*len)++] = *str++;
}

static void append_line(char *buf, size_t *len, const char *str) {
    while (*str != '\0') buf[(*len)++] = *str++;
    buf[(*len)++] = '\n';
}

#define NORMAL_SAMPLE "texture2D"
static void append_normal_map_shader(char *fs_buf, size_t *fs_len,
                                     int tile, bool first) {
    char line[512];
    snprintf(line, sizeof(line), "%s (uNormalMap%d) {",
             first ? "if" : "else if", tile);
    append_line(fs_buf, fs_len, line);
    // Normal vectors use a dedicated linear/trilinear sampler. Reusing the
    // base texture's point/three-point reconstruction creates high-frequency
    // static on stretched UVs and makes the relief unstable at close range.
    snprintf(line, sizeof(line),
             "vec3 mapNormal = " NORMAL_SAMPLE "(uNormalTex%d, vTexCoord%d).xyz * 2.0 - 1.0;",
             tile, tile);
    append_line(fs_buf, fs_len, line);
    append_line(fs_buf, fs_len, "float mapNormalLength2 = dot(mapNormal, mapNormal);");
    append_line(fs_buf, fs_len, "if (mapNormalLength2 > 0.000001) mapNormal *= inversesqrt(mapNormalLength2); else mapNormal = vec3(0.0, 0.0, 1.0);");
    // Keep the authored tangent-space map in a stable UV basis. Reconstructing
    // tangents from clip-space derivatives makes the response depend on
    // camera distance and interpolation, creating bands on stretched or
    // mirrored N64 polygons.
    append_line(fs_buf, fs_len, "vec3 normalMapLight = normalize(vec3(-0.45, 0.65, 0.85));");
    append_line(fs_buf, fs_len, "float baseLight = normalMapLight.z;");
    append_line(fs_buf, fs_len, "float mappedLight = max(dot(mapNormal, normalMapLight), 0.0);");
    // Preserve the existing combiner brightness. Relief and gloss are
    // intentionally independent: strength controls the diffuse normal
    // response, while gloss controls only a restrained specular sheen. The
    // previous implementation multiplied relief by gloss, which made the
    // normal-map slider appear dead at low gloss and made its highlights rise
    // together with relief instead of behaving like a material control.
    append_line(fs_buf, fs_len, "float normalMapDetail = mappedLight - baseLight;");
    append_line(fs_buf, fs_len, "float normalMapStrength = uNormalMapStrength;");
    append_line(fs_buf, fs_len, "float normalMapGloss = clamp(uNormalMapGloss, 0.0, 1.0);");
    // Keep strength as a restrained diffuse relief term. A large multiplier
    // here was the source of the wet/over-bright look users saw when raising
    // strength; gloss must remain an independent material control.
    /* The uniform is already normalized for the UI range. The previous attenuation and clamp made normal-map strength nearly invisible. */
    // Restore the bounded relief response from the last tested strong-strength pass.
    // It preserves visible contrast at 230 while preventing extreme map texels
    // from turning into a dark or over-bright wash.
    append_line(fs_buf, fs_len, "float normalMapRelief = clamp(1.0 + normalMapDetail * normalMapStrength * 0.45, 0.85, 1.15);");
    // Gloss controls highlight sharpness with a small bounded intensity.
    // This keeps it independent from relief strength and avoids white additive
    // bloom on stone, sand, and other bright N64 textures.
    append_line(fs_buf, fs_len, "float normalMapGlossPower = mix(48.0, 8.0, normalMapGloss);");
    append_line(fs_buf, fs_len, "float normalMapSpecular = min(pow(mappedLight, normalMapGlossPower) * normalMapGloss * 0.10, 0.12);");

    // Experimental material response: three soft, colored lobes evaluated per
    // pixel from the authored tangent-space normal. Subtract each flat-normal
    // response so neutral maps do not repaint the original combiner. This is
    // texture-space material lighting, not world-space shadow casting.
    append_line(fs_buf, fs_len, "if (uBetterGraphics) {");
    append_line(fs_buf, fs_len, "vec3 key = normalize(vec3(-0.45, 0.65, 0.85));");
    append_line(fs_buf, fs_len, "vec3 fill = normalize(vec3(0.70, 0.20, 0.75));");
    append_line(fs_buf, fs_len, "vec3 bounce = normalize(vec3(0.10, -0.80, 0.55));");
    append_line(fs_buf, fs_len, "float k = max(dot(mapNormal, key), 0.0) - key.z;");
    append_line(fs_buf, fs_len, "float f = max(dot(mapNormal, fill), 0.0) - fill.z;");
    append_line(fs_buf, fs_len, "float b = max(dot(mapNormal, bounce), 0.0) - bounce.z;");
    append_line(fs_buf, fs_len, "vec3 detail = vec3(0.48, 0.39, 0.29) * k + vec3(0.13, 0.20, 0.31) * f + vec3(0.12, 0.09, 0.06) * b;");
    append_line(fs_buf, fs_len, "vec3 materialLight = clamp(vec3(1.0) + detail * normalMapStrength, vec3(0.68), vec3(1.30));");
    append_line(fs_buf, fs_len, "float sheen = max(pow(max(dot(mapNormal, normalize(key + vec3(0.0, 0.0, 1.0))), 0.0), 24.0) - pow(normalize(key + vec3(0.0, 0.0, 1.0)).z, 24.0), 0.0);");
    append_line(fs_buf, fs_len, "texel.rgb = texel.rgb * materialLight + vec3(1.0, 0.88, 0.72) * sheen * normalMapGloss * 0.12;");
    append_line(fs_buf, fs_len, "} else {");
    append_line(fs_buf, fs_len, "texel.rgb *= normalMapRelief;");
    append_line(fs_buf, fs_len, "texel.rgb += vec3(normalMapSpecular);");
    append_line(fs_buf, fs_len, "}");
    // Close the uNormalMap block.
    append_line(fs_buf, fs_len, "}");
}


static const char *shader_item_to_str(uint32_t item, bool with_alpha, bool only_alpha, bool inputs_have_alpha, bool hint_single_element) {
    if (!only_alpha) {
        switch (item) {
            case SHADER_0:
                return with_alpha ? "vec4(0.0, 0.0, 0.0, 0.0)" : "vec3(0.0, 0.0, 0.0)";
            case SHADER_1:
                return with_alpha ? "vec4(1.0, 1.0, 1.0, 1.0)" : "vec3(1.0, 1.0, 1.0)";
            case SHADER_INPUT_1:
                return with_alpha || !inputs_have_alpha ? "vInput1" : "vInput1.rgb";
            case SHADER_INPUT_2:
                return with_alpha || !inputs_have_alpha ? "vInput2" : "vInput2.rgb";
            case SHADER_INPUT_3:
                return with_alpha || !inputs_have_alpha ? "vInput3" : "vInput3.rgb";
            case SHADER_INPUT_4:
                return with_alpha || !inputs_have_alpha ? "vInput4" : "vInput4.rgb";
            case SHADER_INPUT_5:
                return with_alpha || !inputs_have_alpha ? "vInput5" : "vInput5.rgb";
            case SHADER_INPUT_6:
                return with_alpha || !inputs_have_alpha ? "vInput6" : "vInput6.rgb";
            case SHADER_INPUT_7:
                return with_alpha || !inputs_have_alpha ? "vInput7" : "vInput7.rgb";
            case SHADER_INPUT_8:
                return with_alpha || !inputs_have_alpha ? "vInput8" : "vInput8.rgb";
            case SHADER_TEXEL0:
                return with_alpha ? "texVal0" : "texVal0.rgb";
            case SHADER_TEXEL0A:
                return hint_single_element ? "texVal0.a" :
                    (with_alpha ? "vec4(texVal0.a, texVal0.a, texVal0.a, texVal0.a)" : "vec3(texVal0.a, texVal0.a, texVal0.a)");
            case SHADER_TEXEL1:
                return with_alpha ? "texVal1" : "texVal1.rgb";
            case SHADER_TEXEL1A:
                return hint_single_element ? "texVal1.a" :
                    (with_alpha ? "vec4(texVal1.a, texVal1.a, texVal1.a, texVal1.a)" : "vec3(texVal1.a, texVal1.a, texVal1.a)");
            case SHADER_COMBINED:
                return with_alpha ? "texel" : "texel.rgb";
            case SHADER_COMBINEDA:
                return hint_single_element ? "texel.a" :
                    (with_alpha ? "vec4(texel.a, texel.a, texel.a, texel.a)" : "vec3(texel.a, texel.a, texel.a)");
            case SHADER_NOISE:
                return with_alpha ? "vec4(noise)" : "vec3(noise)";
        }
    } else {
        switch (item) {
            case SHADER_0:
                return "0.0";
            case SHADER_1:
                return "1.0";
            case SHADER_INPUT_1:
                return "vInput1.a";
            case SHADER_INPUT_2:
                return "vInput2.a";
            case SHADER_INPUT_3:
                return "vInput3.a";
            case SHADER_INPUT_4:
                return "vInput4.a";
            case SHADER_INPUT_5:
                return "vInput5.a";
            case SHADER_INPUT_6:
                return "vInput6.a";
            case SHADER_INPUT_7:
                return "vInput7.a";
            case SHADER_INPUT_8:
                return "vInput8.a";
            case SHADER_TEXEL0:
                return "texVal0.a";
            case SHADER_TEXEL0A:
                return "texVal0.a";
            case SHADER_TEXEL1:
                return "texVal1.a";
            case SHADER_TEXEL1A:
                return "texVal1.a";
            case SHADER_COMBINED:
                return "texel.a";
            case SHADER_COMBINEDA:
                return "texel.a";
            case SHADER_NOISE:
                return "noise.a";
        }
    }
    return "unknown";
}

static void append_formula(char *buf, size_t *len, uint8_t* cmd, bool do_single, bool do_multiply, bool do_mix, bool with_alpha, bool only_alpha, bool opt_alpha) {
    if (do_single) {
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 3], with_alpha, only_alpha, opt_alpha, false));
    } else if (do_multiply) {
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 0], with_alpha, only_alpha, opt_alpha, false));
        append_str(buf, len, " * ");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 2], with_alpha, only_alpha, opt_alpha, true));
    } else if (do_mix) {
        append_str(buf, len, "mix(");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 1], with_alpha, only_alpha, opt_alpha, false));
        append_str(buf, len, ", ");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 0], with_alpha, only_alpha, opt_alpha, false));
        append_str(buf, len, ", ");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 2], with_alpha, only_alpha, opt_alpha, true));
        append_str(buf, len, ")");
    } else {
        append_str(buf, len, "(");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 0], with_alpha, only_alpha, opt_alpha, false));
        append_str(buf, len, " - ");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 1], with_alpha, only_alpha, opt_alpha, false));
        append_str(buf, len, ") * ");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 2], with_alpha, only_alpha, opt_alpha, true));
        append_str(buf, len, " + ");
        append_str(buf, len, shader_item_to_str(cmd[only_alpha * 4 + 3], with_alpha, only_alpha, opt_alpha, false));
    }
}

static struct ShaderProgram *gfx_opengl_create_and_load_new_shader(struct ColorCombiner* cc) {
    struct CCFeatures ccf = { 0 };
    gfx_cc_get_features(cc, &ccf);

    bool opt_alpha = cc->cm.use_alpha;
    bool opt_fog = cc->cm.use_fog;
    bool opt_texture_edge = cc->cm.texture_edge;
    bool opt_2cycle = cc->cm.use_2cycle;
    bool opt_light_map = cc->cm.light_map;
    bool world_geometry = cc->cm.world_geometry;
    bool shadow_receiver = cc->cm.shadow_receiver;
    bool enhanced_lighting = cc->cm.enhanced_lighting;
    bool normal_mapping = cc->cm.normal_mapping && (ccf.used_textures[0] || ccf.used_textures[1]);

#ifdef USE_GLES
    bool opt_dither = false;
#else
    bool opt_dither = cc->cm.use_dither;
#endif

    char vs_buf[8192];
    char fs_buf[16384];
    size_t vs_len = 0;
    size_t fs_len = 0;
    size_t num_floats = 4;

    // Vertex shader
#ifdef USE_GLES
    append_line(vs_buf, &vs_len, "#version 100");
#else
    append_line(vs_buf, &vs_len, "#version 120");
#endif
    append_line(vs_buf, &vs_len, "attribute vec4 aVtxPos;");
    if (enhanced_lighting) {
        append_line(vs_buf, &vs_len, "attribute  vec3 aWorldNormal;");
#ifdef USE_GLES
        append_line(vs_buf, &vs_len, "varying  mediump vec3 vWorldNormal;");
#else
        append_line(vs_buf, &vs_len, "varying  vec3 vWorldNormal;");
#endif
        num_floats += 3;
    }
    if (shadow_receiver) {
        append_line(vs_buf, &vs_len, "attribute vec3 aShadowWorld;");
#ifdef USE_GLES
        append_line(vs_buf, &vs_len, "varying highp vec3 vShadowWorld;");
#else
        append_line(vs_buf, &vs_len, "varying vec3 vShadowWorld;");
#endif
        num_floats += 3;
    }
    for (int t = 0; t < 2; t++) {
        if (ccf.used_textures[t]) {
            vs_len += sprintf(vs_buf + vs_len, "attribute vec2 aTexCoord%d;\n", t);
            vs_len += sprintf(vs_buf + vs_len, "varying vec2 vTexCoord%d;\n", t);
            num_floats += 2;
        }
    }
    if (opt_fog) {
        append_line(vs_buf, &vs_len, "attribute vec4 aFog;");
        append_line(vs_buf, &vs_len, "varying vec4 vFog;");
        num_floats += 4;
    }
    if (opt_light_map) {
        append_line(vs_buf, &vs_len, "attribute vec2 aLightMap;");
        append_line(vs_buf, &vs_len, "varying vec2 vLightMap;");
        num_floats += 2;
    }
    for (int i = 0; i < ccf.num_inputs; i++) {
        vs_len += sprintf(vs_buf + vs_len, "attribute vec%d aInput%d;\n", opt_alpha ? 4 : 3, i + 1);
        vs_len += sprintf(vs_buf + vs_len, "varying vec%d vInput%d;\n", opt_alpha ? 4 : 3, i + 1);
        num_floats += opt_alpha ? 4 : 3;
    }
    append_line(vs_buf, &vs_len, "void main() {");
    if (enhanced_lighting) append_line(vs_buf, &vs_len, "vWorldNormal=aWorldNormal;");
    if (shadow_receiver) append_line(vs_buf, &vs_len, "vShadowWorld=aShadowWorld;");
    for (int t = 0; t < 2; t++) {
        if (ccf.used_textures[t]) {
            vs_len += sprintf(vs_buf + vs_len, "vTexCoord%d = aTexCoord%d;\n", t, t);
        }
    }
    if (opt_fog) {
        append_line(vs_buf, &vs_len, "vFog = aFog;");
    }
    if (opt_light_map) {
        append_line(vs_buf, &vs_len, "vLightMap = aLightMap;");
    }
    for (int i = 0; i < ccf.num_inputs; i++) {
        vs_len += sprintf(vs_buf + vs_len, "vInput%d = aInput%d;\n", i + 1, i + 1);
    }
    append_line(vs_buf, &vs_len, "gl_Position = aVtxPos;");
    append_line(vs_buf, &vs_len, "}");

    // Fragment shader
#ifdef USE_GLES
    append_line(fs_buf, &fs_len, "#version 100");
    append_line(fs_buf, &fs_len, shadow_receiver ? "precision highp float;" : "precision mediump float;");
#else
    append_line(fs_buf, &fs_len, "#version 120");
#endif

    if (enhanced_lighting) {
#ifdef USE_GLES
        append_line(fs_buf, &fs_len, "varying  mediump vec3 vWorldNormal;");
#else
        append_line(fs_buf, &fs_len, "varying  vec3 vWorldNormal;");
#endif
    }
    if (shadow_receiver) {
#ifdef USE_GLES
        append_line(fs_buf, &fs_len, "varying highp vec3 vShadowWorld;");
#else
        append_line(fs_buf, &fs_len, "varying vec3 vShadowWorld;");
#endif
        append_line(fs_buf, &fs_len, "uniform sampler2D uShadowMap; uniform vec3 uShadowCenter;");
        append_line(fs_buf, &fs_len, "uniform vec3 uEnvironmentEye; uniform vec3 uEnvironmentState;");
    }
    for (int t = 0; t < 2; t++) {
        if (ccf.used_textures[t]) {
            fs_len += sprintf(fs_buf + fs_len, "varying vec2 vTexCoord%d;\n", t);
        }
    }
    if (opt_fog) {
        append_line(fs_buf, &fs_len, "varying vec4 vFog;");
    }
    if (opt_light_map) {
        append_line(fs_buf, &fs_len, "varying vec2 vLightMap;");
    }
    for (int i = 0; i < ccf.num_inputs; i++) {
        fs_len += sprintf(fs_buf + fs_len, "varying vec%d vInput%d;\n", opt_alpha ? 4 : 3, i + 1);
    }

    for (int t = 0; t < 2; t++) {
        if (ccf.used_textures[t]) {
            fs_len += sprintf(fs_buf + fs_len, "uniform sampler2D uTex%d;\n", t);
            fs_len += sprintf(fs_buf + fs_len, "uniform vec2 uTex%dSize;\n", t);
            fs_len += sprintf(fs_buf + fs_len, "uniform bool uTex%dFilter;\n", t);
        }
    }

    if (normal_mapping) {
        for (int t=0; t<2; ++t) if (ccf.used_textures[t]) {
            fs_len += sprintf(fs_buf + fs_len, "uniform sampler2D uNormalTex%d; uniform bool uNormalMap%d;\n", t, t);
        }
        append_line(fs_buf, &fs_len, "uniform float uNormalMapStrength; uniform float uNormalMapGloss; uniform bool uBetterGraphics;");
    }

    // 3 point texture filtering
    // Original author: ArthurCarvalho
    // Modified GLSL implementation by twinaphex, mupen64plus-libretro project.
    if (ccf.used_textures[0] || ccf.used_textures[1]) {
        append_line(fs_buf, &fs_len, "#define TEX_OFFSET(off) texture2D(tex, texCoord - (off)/texSize)");
        append_line(fs_buf, &fs_len, "vec4 filter3point(in sampler2D tex, in vec2 texCoord, in vec2 texSize) {");
        append_line(fs_buf, &fs_len, "    vec2 offset = fract(texCoord*texSize - vec2(0.5));");
        append_line(fs_buf, &fs_len, "    offset -= step(1.0, offset.x + offset.y);");
        append_line(fs_buf, &fs_len, "    vec4 c0 = TEX_OFFSET(offset);");
        append_line(fs_buf, &fs_len, "    vec4 c1 = TEX_OFFSET(vec2(offset.x - sign(offset.x), offset.y));");
        append_line(fs_buf, &fs_len, "    vec4 c2 = TEX_OFFSET(vec2(offset.x, offset.y - sign(offset.y)));");
        append_line(fs_buf, &fs_len, "    return c0 + abs(offset.x)*(c1-c0) + abs(offset.y)*(c2-c0);");
        append_line(fs_buf, &fs_len, "}");
        append_line(fs_buf, &fs_len, "vec4 sampleTex(in sampler2D tex, in vec2 uv, in vec2 texSize, in bool dofilter, in int filterMode) {");
        append_line(fs_buf, &fs_len, "    if (dofilter && filterMode == 2)");
        append_line(fs_buf, &fs_len, "        return filter3point(tex, uv, texSize);");
        append_line(fs_buf, &fs_len, "    else");
        append_line(fs_buf, &fs_len, "        return texture2D(tex, uv);");
        append_line(fs_buf, &fs_len, "}");
    }

    if (world_geometry) {
        append_line(fs_buf, &fs_len, "float dither4x4(vec2 position, float brightness) {");
        append_line(fs_buf, &fs_len, "    int x = int(mod(position.x, 4.0));");
        append_line(fs_buf, &fs_len, "    int y = int(mod(position.y, 4.0));");
        append_line(fs_buf, &fs_len, "    int index = x + y * 4;");
        append_line(fs_buf, &fs_len, "    float limit = 0.0;");
        append_line(fs_buf, &fs_len, "    if (x < 8) {");
        append_line(fs_buf, &fs_len, "        if (index == 0) limit = 0.0625;");
        append_line(fs_buf, &fs_len, "        if (index == 1) limit = 0.5625;");
        append_line(fs_buf, &fs_len, "        if (index == 2) limit = 0.1875;");
        append_line(fs_buf, &fs_len, "        if (index == 3) limit = 0.6875;");
        append_line(fs_buf, &fs_len, "        if (index == 4) limit = 0.8125;");
        append_line(fs_buf, &fs_len, "        if (index == 5) limit = 0.3125;");
        append_line(fs_buf, &fs_len, "        if (index == 6) limit = 0.9375;");
        append_line(fs_buf, &fs_len, "        if (index == 7) limit = 0.4375;");
        append_line(fs_buf, &fs_len, "        if (index == 8) limit = 0.25;");
        append_line(fs_buf, &fs_len, "        if (index == 9) limit = 0.75;");
        append_line(fs_buf, &fs_len, "        if (index == 10) limit = 0.125;");
        append_line(fs_buf, &fs_len, "        if (index == 11) limit = 0.625;");
        append_line(fs_buf, &fs_len, "        if (index == 12) limit = 1.0;");
        append_line(fs_buf, &fs_len, "        if (index == 13) limit = 0.5;");
        append_line(fs_buf, &fs_len, "        if (index == 14) limit = 0.875;");
        append_line(fs_buf, &fs_len, "        if (index == 15) limit = 0.375;");
        append_line(fs_buf, &fs_len, "    }");
        append_line(fs_buf, &fs_len, "    return brightness < limit ? 0.0 : 1.0;");
        append_line(fs_buf, &fs_len, "}");

        append_line(fs_buf, &fs_len, "vec3 rgb2hsv(vec3 c) {");
        append_line(fs_buf, &fs_len, "    vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0);");
        append_line(fs_buf, &fs_len, "    vec4 p = mix(vec4(c.bg, K.wz),");
        append_line(fs_buf, &fs_len, "                 vec4(c.gb, K.xy),");
        append_line(fs_buf, &fs_len, "                 step(c.b, c.g));");
        append_line(fs_buf, &fs_len, "    vec4 q = mix(vec4(p.xyw, c.r),");
        append_line(fs_buf, &fs_len, "                 vec4(c.r, p.yzx),");
        append_line(fs_buf, &fs_len, "                 step(p.x, c.r));");
        append_line(fs_buf, &fs_len, "    float d = q.x - min(q.w, q.y);");
        append_line(fs_buf, &fs_len, "    float e = 1.0e-10;");
        append_line(fs_buf, &fs_len, "    return vec3(");
        append_line(fs_buf, &fs_len, "        abs(q.z + (q.w - q.y) / (6.0 * d + e)), // hue");
        append_line(fs_buf, &fs_len, "        d / (q.x + e),                          // saturation");
        append_line(fs_buf, &fs_len, "        q.x                                     // value");
        append_line(fs_buf, &fs_len, "    );");
        append_line(fs_buf, &fs_len, "}");
        append_line(fs_buf, &fs_len, "");
        append_line(fs_buf, &fs_len, "vec3 hsv2rgb(vec3 c) {");
        append_line(fs_buf, &fs_len, "    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);");
        append_line(fs_buf, &fs_len, "    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);");
        append_line(fs_buf, &fs_len, "}");
    }

    if ((opt_alpha && opt_dither) || ccf.do_noise) {
        append_line(fs_buf, &fs_len, "uniform float uFrameCount;");

        append_line(fs_buf, &fs_len, "float random(in vec3 value) {");
        append_line(fs_buf, &fs_len, "    float random = dot(sin(value), vec3(12.9898, 78.233, 37.719));");
        append_line(fs_buf, &fs_len, "    return fract(sin(random) * 143758.5453);");
        append_line(fs_buf, &fs_len, "}");
    }

    if (opt_light_map) {
        append_line(fs_buf, &fs_len, "uniform vec3 uLightmapColor;");
    }

    if (world_geometry) {
        fs_len += sprintf(fs_buf + fs_len, "uniform int uShaderFlags[%d];\n", SHADER_FLAG_MAX);
        fs_len += sprintf(fs_buf + fs_len, "uniform float uShaderFlagValues[%d];\n", SHADER_FLAG_MAX);
    }

    append_line(fs_buf, &fs_len, "uniform int uFilter;");

    append_line(fs_buf, &fs_len, "void main() {");

    if ((opt_alpha && opt_dither) || ccf.do_noise) {
        append_line(fs_buf, &fs_len, "float noise = floor(random(floor(vec3(gl_FragCoord.xy, uFrameCount))) + 0.5);");
    }

    if (ccf.used_textures[0]) {
        append_line(fs_buf, &fs_len, "vec4 texVal0 = sampleTex(uTex0, vTexCoord0, uTex0Size, uTex0Filter, uFilter);");
    }
    if (ccf.used_textures[1]) {
        if (opt_light_map) {
            append_line(fs_buf, &fs_len, "vec4 texVal1 = sampleTex(uTex1, vLightMap, uTex1Size, uTex1Filter, uFilter);");
            append_line(fs_buf, &fs_len, "texVal0.rgb *= uLightmapColor.rgb;");
            append_line(fs_buf, &fs_len, "texVal1.rgb = texVal1.rgb * texVal1.rgb + texVal1.rgb;");
        } else {
            append_line(fs_buf, &fs_len, "vec4 texVal1 = sampleTex(uTex1, vTexCoord1, uTex1Size, uTex1Filter, uFilter);");
        }
    }

    append_str(fs_buf, &fs_len, (opt_alpha) ? "vec4 texel = " : "vec3 texel = ");
    for (int i = 0; i < (opt_2cycle + 1); i++) {
        u8* cmd = &cc->shader_commands[i * 8];
        if (!ccf.color_alpha_same[i] && opt_alpha) {
            append_str(fs_buf, &fs_len, "vec4(");
            append_formula(fs_buf, &fs_len, cmd, ccf.do_single[i*2+0], ccf.do_multiply[i*2+0], ccf.do_mix[i*2+0], false, false, true);
            append_str(fs_buf, &fs_len, ", ");
            append_formula(fs_buf, &fs_len, cmd, ccf.do_single[i*2+1], ccf.do_multiply[i*2+1], ccf.do_mix[i*2+1], true, true, true);
            append_str(fs_buf, &fs_len, ")");
        } else {
            append_formula(fs_buf, &fs_len, cmd, ccf.do_single[i*2+0], ccf.do_multiply[i*2+0], ccf.do_mix[i*2+0], opt_alpha, false, opt_alpha);
        }
        append_line(fs_buf, &fs_len, ";");

        if (i == 0 && opt_2cycle) {
            append_str(fs_buf, &fs_len, "texel = ");
        }
    }

    // Per-fragment world-space directional and hemisphere lighting. The
    // interpolated model normal is renormalized per pixel; multiplication
    // retains the authored lighting/colors and keeps true black black.
    if (enhanced_lighting) {
        append_line(fs_buf, &fs_len, "float normalLen2 = dot(vWorldNormal, vWorldNormal);");
        append_line(fs_buf, &fs_len, "if (normalLen2 > 0.000001) {");
        append_line(fs_buf, &fs_len, "vec3 N = vWorldNormal * inversesqrt(normalLen2);");
        append_line(fs_buf, &fs_len, "float sky = clamp(N.y * 0.5 + 0.5, 0.0, 1.0);");
        append_line(fs_buf, &fs_len, "float key = max(dot(N, normalize(vec3(-0.35, 0.80, 0.48))), 0.0);");
        append_line(fs_buf, &fs_len, "float fill = max(dot(N, normalize(vec3(0.65, 0.30, -0.55))), 0.0);");
        append_line(fs_buf, &fs_len, "float bounce = max(dot(N, normalize(vec3(0.15, -0.90, 0.25))), 0.0);");
        append_line(fs_buf, &fs_len, "vec3 lighting = vec3(0.91, 0.90, 0.89) + sky * vec3(0.06, 0.09, 0.15) + key * vec3(0.30, 0.23, 0.16) + fill * vec3(0.08, 0.10, 0.16) + bounce * vec3(0.12, 0.08, 0.04);");
        append_line(fs_buf, &fs_len, "texel.rgb *= clamp(lighting, vec3(0.85), vec3(1.35));");
        append_line(fs_buf, &fs_len, "}");
    }


    if (normal_mapping) {
        bool first_normal_branch = true;
        for (int t=0; t<2; ++t) if (ccf.used_textures[t]) {
            append_normal_map_shader(fs_buf, &fs_len, t, first_normal_branch);
            first_normal_branch = false;
        }
    }

    if (opt_texture_edge && opt_alpha) {
        append_line(fs_buf, &fs_len, "if (texel.a > 0.3) texel.a = 1.0; else discard;");
    }

    if (shadow_receiver) {
        append_line(fs_buf, &fs_len, "vec3 sp=vShadowWorld-uShadowCenter;");
        append_line(fs_buf, &fs_len, "vec3 sl=normalize(vec3(-0.35,0.80,0.48));");
        append_line(fs_buf, &fs_len, "vec3 sr=normalize(cross(vec3(0.0,1.0,0.0),sl));");
        append_line(fs_buf, &fs_len, "vec3 su=cross(sl,sr);");
        append_line(fs_buf, &fs_len, "vec3 sc=vec3(dot(sp,sr)/4800.0,dot(sp,su)/4800.0,-dot(sp,sl)/8000.0)*0.5+0.5;");
        append_line(fs_buf, &fs_len, "if (sc.x>0.001 && sc.y>0.001 && sc.x<0.999 && sc.y<0.999 && sc.z>0.0 && sc.z<1.0) {");
        append_line(fs_buf, &fs_len, "float visibility=0.0;");
        append_line(fs_buf, &fs_len, "for (int sy=-1; sy<=1; ++sy) for (int sx=-1; sx<=1; ++sx) {");
        append_line(fs_buf, &fs_len, "vec3 shadowPacked=texture2D(uShadowMap,sc.xy+vec2(float(sx),float(sy))/2048.0).rgb;");
        append_line(fs_buf, &fs_len, "float closest=dot(shadowPacked,vec3(1.0,1.0/255.0,1.0/65025.0));");
        append_line(fs_buf, &fs_len, "visibility += (sc.z-0.00125 <= closest) ? 1.0 : 0.0;");
        append_line(fs_buf, &fs_len, "}");
        append_line(fs_buf, &fs_len, "float shadowEdge=min(min(sc.x,1.0-sc.x),min(sc.y,1.0-sc.y));");
        append_line(fs_buf, &fs_len, "float shadowFade=smoothstep(0.001,0.035,shadowEdge)*smoothstep(0.0,0.025,min(sc.z,1.0-sc.z));");
        append_line(fs_buf, &fs_len, "texel.rgb *= mix(1.0,mix(0.75,1.0,visibility/9.0),shadowFade);");
        append_line(fs_buf, &fs_len, "}");
    }

    // Restrained distance haze and animated water-light caustics. Only the
    // opaque world-position path is eligible; never affect HUD/fullbright.
    if (shadow_receiver) {
        append_line(fs_buf, &fs_len, "float envDistance=length(vShadowWorld-uEnvironmentEye);");
        append_line(fs_buf, &fs_len, "float aerial=smoothstep(3200.0,16000.0,envDistance)*0.10;");
        append_line(fs_buf, &fs_len, "texel.rgb=mix(texel.rgb,vec3(0.66,0.73,0.80),aerial);");
        append_line(fs_buf, &fs_len, "if(uEnvironmentState.y>0.5 && vShadowWorld.y<uEnvironmentState.z) {");
        append_line(fs_buf, &fs_len, "float causticWave=sin(vShadowWorld.x*0.018+uEnvironmentState.x)*sin(vShadowWorld.z*0.021-uEnvironmentState.x*2.0);");
        append_line(fs_buf, &fs_len, "float caustic=pow(max(causticWave,0.0),4.0)*(1.0-smoothstep(0.0,1800.0,uEnvironmentState.z-vShadowWorld.y));");
        append_line(fs_buf, &fs_len, "texel.rgb+=texel.rgb*vec3(0.14,0.19,0.16)*caustic;");
        append_line(fs_buf, &fs_len, "float underwaterFog=smoothstep(300.0,8000.0,envDistance)*0.22;");
        append_line(fs_buf, &fs_len, "texel.rgb=mix(texel.rgb,vec3(0.14,0.34,0.42),underwaterFog);");
        append_line(fs_buf, &fs_len, "}");
    }


    // TODO discard if alpha is 0?

    if (world_geometry) {
        // hue
        append_line(fs_buf, &fs_len, "if (uShaderFlags[0] == 1) {");
        append_line(fs_buf, &fs_len, "vec3 hsv = rgb2hsv(texel.rgb);");
        append_line(fs_buf, &fs_len, "hsv.x = fract(hsv.x + uShaderFlagValues[0]);");
        append_line(fs_buf, &fs_len, "vec3 finalColor = hsv2rgb(hsv);");
        append_line(fs_buf, &fs_len, "texel.rgb = finalColor;");
        append_line(fs_buf, &fs_len, "}");

        // saturation
        append_line(fs_buf, &fs_len, "if (uShaderFlags[1] == 1) {");
        append_line(fs_buf, &fs_len, "const vec3 w = vec3(0.2125, 0.7154, 0.0721);");
        append_line(fs_buf, &fs_len, "vec3 intensity = vec3(dot(texel.rgb, w));");
        append_line(fs_buf, &fs_len, "texel.rgb = mix(intensity, texel.rgb, uShaderFlagValues[1]);");
        append_line(fs_buf, &fs_len, "}");

        // brightness
        append_line(fs_buf, &fs_len, "if (uShaderFlags[2] == 1) {");
        append_line(fs_buf, &fs_len, "texel.rgb *= uShaderFlagValues[2];");
        append_line(fs_buf, &fs_len, "}");

        // contrast
        append_line(fs_buf, &fs_len, "if (uShaderFlags[3] == 1) {");
        append_line(fs_buf, &fs_len, "texel.rgb = 0.5 + uShaderFlagValues[3] * (texel.rgb - 0.5);");
        append_line(fs_buf, &fs_len, "}");

        // exposure
        append_line(fs_buf, &fs_len, "if (uShaderFlags[4] == 1) {");
        append_line(fs_buf, &fs_len, "texel.rgb = texel.rgb + (uShaderFlagValues[4] - 2.0) * texel.rgb + texel.rgb;");
        append_line(fs_buf, &fs_len, "}");

        // dithering
        append_line(fs_buf, &fs_len, "if (uShaderFlags[5] == 1) {");
        append_line(fs_buf, &fs_len, "texel.rgb *= dither4x4(gl_FragCoord.xy, dot(texel.rgb, vec3(0.299, 0.587, 0.114)));");
        append_line(fs_buf, &fs_len, "}");

        // posterization
        append_line(fs_buf, &fs_len, "if (uShaderFlags[6] == 1) {");
        append_line(fs_buf, &fs_len, "float levels = floor(max(1.0, uShaderFlagValues[6]));");
        append_line(fs_buf, &fs_len, "texel.rgb = floor(texel.rgb * levels) / levels;");
        append_line(fs_buf, &fs_len, "}");

        // scan lines
        append_line(fs_buf, &fs_len, "if (uShaderFlags[7] == 1) {");
        append_line(fs_buf, &fs_len, "float scan = sin(gl_FragCoord.y * 1.5) * 0.04;");
        append_line(fs_buf, &fs_len, "texel.rgb -= scan * uShaderFlagValues[7];");
        append_line(fs_buf, &fs_len, "}");
    }

    if (shadow_receiver && enhanced_lighting) {
        // A very small sky-colored Fresnel rim suggests material reflectance.
        append_line(fs_buf, &fs_len, "vec3 envView=uEnvironmentEye-vShadowWorld;");
        append_line(fs_buf, &fs_len, "float envViewLen=dot(envView,envView); float envNormalLen=dot(vWorldNormal,vWorldNormal);");
        append_line(fs_buf, &fs_len, "if(envViewLen>0.000001 && envNormalLen>0.000001){");
        append_line(fs_buf, &fs_len, "float envFacing=max(dot(envView*inversesqrt(envViewLen),vWorldNormal*inversesqrt(envNormalLen)),0.0);");
        append_line(fs_buf, &fs_len, "float envRim=pow(1.0-clamp(envFacing,0.0,1.0),4.0);");
        append_line(fs_buf, &fs_len, "texel.rgb+=texel.rgb*vec3(0.025,0.035,0.05)*envRim;");
        append_line(fs_buf, &fs_len, "}");
    }

    if (opt_fog) {
        if (opt_alpha) {
            append_line(fs_buf, &fs_len, "texel = vec4(mix(texel.rgb, vFog.rgb, vFog.a), texel.a);");
        } else {
            append_line(fs_buf, &fs_len, "texel = mix(texel, vFog.rgb, vFog.a);");
        }
    }

    if (opt_alpha && opt_dither) {
        append_line(fs_buf, &fs_len, "texel.a *= noise;");
    }

    if (opt_alpha) {
        append_line(fs_buf, &fs_len, "gl_FragColor = texel;");
    } else {
        append_line(fs_buf, &fs_len, "gl_FragColor = vec4(texel, 1.0);");
    }
    append_line(fs_buf, &fs_len, "}");

    vs_buf[vs_len] = '\0';
    fs_buf[fs_len] = '\0';

    /*puts("Vertex shader:");
    puts(vs_buf);
    puts("Fragment shader:");
    puts(fs_buf);
    puts("End");*/

    const GLchar *sources[2] = { vs_buf, fs_buf };
    const GLint lengths[2] = { vs_len, fs_len };
    GLint success;

    GLuint vertex_shader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertex_shader, 1, &sources[0], &lengths[0]);
    glCompileShader(vertex_shader);
    glGetShaderiv(vertex_shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        GLint max_length = 0;
        glGetShaderiv(vertex_shader, GL_INFO_LOG_LENGTH, &max_length);
        char error_log[1024];
        fprintf(stderr, "Vertex shader compilation failed\n");
        glGetShaderInfoLog(vertex_shader, max_length, &max_length, &error_log[0]);
        fprintf(stderr, "%s\n", &error_log[0]);
        sys_fatal("vertex shader compilation failed (see terminal)");
    }

    GLuint fragment_shader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragment_shader, 1, &sources[1], &lengths[1]);
    glCompileShader(fragment_shader);
    glGetShaderiv(fragment_shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        GLint max_length = 0;
        glGetShaderiv(fragment_shader, GL_INFO_LOG_LENGTH, &max_length);
        char error_log[1024];
        fprintf(stderr, "Fragment shader compilation failed\n");
        glGetShaderInfoLog(fragment_shader, max_length, &max_length, &error_log[0]);
        fprintf(stderr, "%s\n", &error_log[0]);
        sys_fatal("fragment shader compilation failed (see terminal)");
    }

    GLuint shader_program = glCreateProgram();
    glAttachShader(shader_program, vertex_shader);
    glAttachShader(shader_program, fragment_shader);
    glLinkProgram(shader_program);
    glDeleteShader(vertex_shader);
    glDeleteShader(fragment_shader);

    size_t cnt = 0;

    struct ShaderProgram *prg = &shader_program_pool[shader_program_pool_index];
    if (prg->opengl_program_id) glDeleteProgram(prg->opengl_program_id);
    shader_program_pool_index = (shader_program_pool_index + 1) % CC_MAX_SHADERS;
    if (shader_program_pool_size < CC_MAX_SHADERS) { shader_program_pool_size++; }

    prg->attrib_locations[cnt] = glGetAttribLocation(shader_program, "aVtxPos");
    prg->attrib_sizes[cnt] = 4;
    ++cnt;

    if (enhanced_lighting) {
        prg->attrib_locations[cnt] = glGetAttribLocation(shader_program, "aWorldNormal");
        prg->attrib_sizes[cnt] = 3; ++cnt;
    }
    if (shadow_receiver) {
        prg->attrib_locations[cnt] = glGetAttribLocation(shader_program, "aShadowWorld");
        prg->attrib_sizes[cnt] = 3; ++cnt;
    }
    for (int t = 0; t < 2; t++) {
        if (ccf.used_textures[t]) {
            char name[16];
            sprintf(name, "aTexCoord%d", t);
            prg->attrib_locations[cnt] = glGetAttribLocation(shader_program, name);
            prg->attrib_sizes[cnt] = 2;
            ++cnt;
        }
    }

    if (opt_fog) {
        prg->attrib_locations[cnt] = glGetAttribLocation(shader_program, "aFog");
        prg->attrib_sizes[cnt] = 4;
        ++cnt;
    }

    if (opt_light_map) {
        prg->attrib_locations[cnt] = glGetAttribLocation(shader_program, "aLightMap");
        prg->attrib_sizes[cnt] = 2;
        ++cnt;
    }

    for (int i = 0; i < ccf.num_inputs; i++) {
        char name[16];
        sprintf(name, "aInput%d", i + 1);
        prg->attrib_locations[cnt] = glGetAttribLocation(shader_program, name);
        prg->attrib_sizes[cnt] = opt_alpha ? 4 : 3;
        ++cnt;
    }

    prg->hash = cc->hash;
    prg->opengl_program_id = shader_program;
    prg->num_inputs = ccf.num_inputs;
    prg->used_textures[0] = ccf.used_textures[0];
    prg->used_textures[1] = ccf.used_textures[1];
    prg->num_floats = num_floats;
    prg->num_attribs = cnt;

    glUseProgram(shader_program);
    for (int t = 0; t < 2; t++) {
        if (ccf.used_textures[t]) {
            char name[16];
            sprintf(name, "uTex%d", t);
            GLint sampler_location = glGetUniformLocation(shader_program, name);
            sprintf(name, "uTex%dSize", t);
            prg->uniform_locations[t * 2] = glGetUniformLocation(shader_program, name);
            sprintf(name, "uTex%dFilter", t);
            prg->uniform_locations[t * 2 + 1] = glGetUniformLocation(shader_program, name);
            glUniform1i(sampler_location, t);
        }
    }

    if ((opt_alpha && opt_dither) || ccf.do_noise) {
        prg->uniform_locations[4] = glGetUniformLocation(shader_program, "uFrameCount");
        prg->used_noise = true;
    } else {
        prg->used_noise = false;
    }

    if (opt_light_map) {
        prg->uniform_locations[5] = glGetUniformLocation(shader_program, "uLightmapColor");
        prg->used_lightmap = true;
    } else {
        prg->used_lightmap = false;
    }

    if (world_geometry) {
        prg->uniform_locations[6] = glGetUniformLocation(shader_program, "uShaderFlags");
        prg->uniform_locations[7] = glGetUniformLocation(shader_program, "uShaderFlagValues");
        prg->world_geometry = true;
    } else {
        prg->world_geometry = false;
    }

    for (int t=0; t<2; ++t) {
        char name[32];
        snprintf(name, sizeof(name), "uNormalTex%d", t);
        prg->normal_sampler[t] = normal_mapping ? glGetUniformLocation(shader_program, name) : -1;
        snprintf(name, sizeof(name), "uNormalMap%d", t);
        prg->normal_enabled[t] = normal_mapping ? glGetUniformLocation(shader_program, name) : -1;
    }
    prg->normal_strength = normal_mapping ? glGetUniformLocation(shader_program, "uNormalMapStrength") : -1;
    prg->normal_gloss = normal_mapping ? glGetUniformLocation(shader_program, "uNormalMapGloss") : -1;
    prg->normal_better = normal_mapping ? glGetUniformLocation(shader_program, "uBetterGraphics") : -1;
    prg->uniform_locations[8] = glGetUniformLocation(shader_program, "uFilter");
    prg->shadow_sampler = shadow_receiver ? glGetUniformLocation(shader_program,"uShadowMap") : -1;
    prg->shadow_center = shadow_receiver ? glGetUniformLocation(shader_program,"uShadowCenter") : -1;
    prg->environment_eye_location = shadow_receiver ? glGetUniformLocation(shader_program,"uEnvironmentEye") : -1;
    prg->environment_state_location = shadow_receiver ? glGetUniformLocation(shader_program,"uEnvironmentState") : -1;

    gfx_opengl_load_shader(prg);

    return prg;
}

bool gfx_opengl_shader_matches(const struct ShaderProgram *program, const struct ColorCombiner *combiner) {
    return program && combiner && program->hash == combiner->hash;
}

static struct ShaderProgram *gfx_opengl_lookup_shader(struct ColorCombiner* cc) {
    for (size_t i = 0; i < shader_program_pool_size; i++) {
        if (shader_program_pool[i].hash == cc->hash) {
            return &shader_program_pool[i];
        }
    }
    return NULL;
}

static void gfx_opengl_shader_get_info(struct ShaderProgram *prg, uint8_t *num_inputs, bool used_textures[2]) {
    *num_inputs = prg->num_inputs;
    used_textures[0] = prg->used_textures[0];
    used_textures[1] = prg->used_textures[1];
}

static GLuint gfx_opengl_new_texture(void) {
    if (num_textures >= tex_cache_size) {
        tex_cache_size += TEX_CACHE_STEP;
        tex_cache = realloc(tex_cache, sizeof(struct GLTexture) * tex_cache_size);
        if (!tex_cache) sys_fatal("out of memory allocating texture cache");
        // invalidate these because they might be pointing to garbage now
        opengl_tex[0] = NULL;
        opengl_tex[1] = NULL;
    }
    memset(&tex_cache[num_textures], 0, sizeof(struct GLTexture));
    glGenTextures(1, &tex_cache[num_textures].gltex);
    return num_textures++;
}

static void gfx_opengl_select_texture(int tile, GLuint texture_id) {
    opengl_tex[tile] = tex_cache + texture_id;
    opengl_curtex = tile;
    glActiveTexture(GL_TEXTURE0 + tile);
    glBindTexture(GL_TEXTURE_2D, opengl_tex[tile]->gltex);
    gfx_opengl_set_texture_uniforms(opengl_prg, tile);
}

static void gfx_opengl_upload_texture(const uint8_t *rgba32_buf, int width, int height) {
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba32_buf);
    opengl_tex[opengl_curtex]->size[0] = width;
    opengl_tex[opengl_curtex]->size[1] = height;
    struct GLTexture *texture = opengl_tex[opengl_curtex];
    uint8_t *normal = NULL; int nw=0, nh=0;
    if (texture->normal_gltex) { glDeleteTextures(1, &texture->normal_gltex); texture->normal_gltex=0; }
    texture->has_normal = false;
    if (gfx_normal_maps_load_pending(&normal, &nw, &nh, width, height)) {
        GLint active; glGetIntegerv(GL_ACTIVE_TEXTURE, &active);
        glActiveTexture(GL_TEXTURE3 + opengl_curtex);
        glGenTextures(1, &texture->normal_gltex);
        glBindTexture(GL_TEXTURE_2D, texture->normal_gltex);
        texture->normal_clamp_edges = gfx_opengl_normal_map_has_discontinuous_edges(normal, nw, nh);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, texture->normal_clamp_edges ? GL_CLAMP_TO_EDGE : (texture->wrap_s ? texture->wrap_s : GL_REPEAT));
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, texture->normal_clamp_edges ? GL_CLAMP_TO_EDGE : (texture->wrap_t ? texture->wrap_t : GL_REPEAT));
        bool mip = nw > 0 && nh > 0 && !(nw & (nw-1)) && !(nh & (nh-1));
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, mip ? GL_LINEAR_MIPMAP_LINEAR : GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, nw, nh, 0, GL_RGBA, GL_UNSIGNED_BYTE, normal);
        if (mip) glGenerateMipmap(GL_TEXTURE_2D);
        texture->has_normal = texture->normal_gltex != 0 && glGetError() == GL_NO_ERROR;
        if (!texture->has_normal && texture->normal_gltex) { glDeleteTextures(1, &texture->normal_gltex); texture->normal_gltex=0; }
        glActiveTexture(active);
        free(normal);
        if (opengl_prg) gfx_opengl_set_texture_uniforms(opengl_prg, opengl_curtex);
    }
}

static uint32_t gfx_cm_to_opengl(uint32_t val) {
    if (val & G_TX_CLAMP) {
        return GL_CLAMP_TO_EDGE;
    }
    return (val & G_TX_MIRROR) ? GL_MIRRORED_REPEAT : GL_REPEAT;
}

static void gfx_opengl_set_sampler_parameters(int tile, bool linear_filter, uint32_t cms, uint32_t cmt) {
    const GLenum filter = linear_filter ? GL_LINEAR : GL_NEAREST;
    glActiveTexture(GL_TEXTURE0 + tile);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, gfx_cm_to_opengl(cms));
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, gfx_cm_to_opengl(cmt));
    opengl_curtex = tile;
    if (opengl_tex[tile]) {
        struct GLTexture *texture = opengl_tex[tile];
        texture->wrap_s = gfx_cm_to_opengl(cms);
        texture->wrap_t = gfx_cm_to_opengl(cmt);
        if (texture->normal_gltex) {
            glActiveTexture(GL_TEXTURE3 + tile);
            glBindTexture(GL_TEXTURE_2D, texture->normal_gltex);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, texture->normal_clamp_edges ? GL_CLAMP_TO_EDGE : texture->wrap_s);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, texture->normal_clamp_edges ? GL_CLAMP_TO_EDGE : texture->wrap_t);
            glActiveTexture(GL_TEXTURE0 + tile);
        }
        opengl_tex[tile]->filter = linear_filter;
        gfx_opengl_set_texture_uniforms(opengl_prg, tile);
    }
}

static void gfx_opengl_set_depth_test(bool depth_test) {
    if (depth_test) {
        glEnable(GL_DEPTH_TEST);
    } else {
        glDisable(GL_DEPTH_TEST);
    }
}

static void gfx_opengl_set_depth_mask(bool z_upd) {
    glDepthMask(z_upd ? GL_TRUE : GL_FALSE);
}

static void gfx_opengl_set_zmode_decal(bool zmode_decal) {
    if (zmode_decal) {
        glPolygonOffset(-2, -2);
        glEnable(GL_POLYGON_OFFSET_FILL);
    } else {
        glPolygonOffset(0, 0);
        glDisable(GL_POLYGON_OFFSET_FILL);
    }
}

static void gfx_opengl_set_viewport(int x, int y, int width, int height) {
    glViewport(x, y, width, height);
}

static void gfx_opengl_set_scissor(int x, int y, int width, int height) {
    glScissor(x, y, width, height);
}

static void gfx_opengl_set_use_alpha(bool use_alpha) {
    if (use_alpha) {
        glEnable(GL_BLEND);
    } else {
        glDisable(GL_BLEND);
    }
}

static void gfx_opengl_draw_triangles(float buf_vbo[], size_t buf_vbo_len, size_t buf_vbo_num_tris) {
    //printf("flushing %d tris\n", buf_vbo_num_tris);
    glBufferData(GL_ARRAY_BUFFER, sizeof(float) * buf_vbo_len, buf_vbo, GL_STREAM_DRAW);
    glDrawArrays(GL_TRIANGLES, 0, 3 * buf_vbo_num_tris);
}

static inline bool gl_version_is_supported(int major, int minor, bool is_es) {
    if (is_es) {
        return major >= 2;
    }
    return (major > 2) || (major == 2 && minor >= 1);
}

static inline bool gl_get_version(int *major, int *minor, bool *is_es) {
    const char *vstr = (const char *)glGetString(GL_VERSION);
    if (!vstr || !vstr[0]) return false;

    if (!strncmp(vstr, "OpenGL ES ", 10)) {
        vstr += 10;
        *is_es = true;
    } else if (!strncmp(vstr, "OpenGL ES-CM ", 13)) {
        vstr += 13;
        *is_es = true;
    }

    return (sscanf(vstr, "%d.%d", major, minor) == 2);
}

static void gfx_opengl_init(void) {
#if FOR_WINDOWS || defined(OSX_BUILD)
    GLenum err;
    if ((err = glewInit()) != GLEW_OK)
        sys_fatal("could not init GLEW:\n%s", glewGetErrorString(err));
#endif

    tex_cache_size = TEX_CACHE_STEP;
    tex_cache = calloc(tex_cache_size, sizeof(struct GLTexture));
    if (!tex_cache) sys_fatal("out of memory allocating texture cache");

    // check GL version
    int vmajor = 0;
    int vminor = 0;
    bool is_es = false;
    if (!gl_get_version(&vmajor, &vminor, &is_es) || !gl_version_is_supported(vmajor, vminor, is_es)) {
        sys_fatal("OpenGL 2.1+ is required.\nReported version: %s%d.%d", is_es ? "ES" : "", vmajor, vminor);
    }

    glGenBuffers(1, &opengl_vbo);

    glBindBuffer(GL_ARRAY_BUFFER, opengl_vbo);

    if (vmajor >= 3 && !is_es) {
        glGenVertexArrays(1, &opengl_vao);
        glBindVertexArray(opengl_vao);
    }

    glDepthFunc(GL_LEQUAL);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
}

bool gfx_opengl_check_compatibility(void) {
    // check GL version
    int vmajor = 0;
    int vminor = 0;
    bool is_es = false;
    if (!gl_get_version(&vmajor, &vminor, &is_es)) {
        return false;
    }
    return gl_version_is_supported(vmajor, vminor, is_es);
}

static void gfx_opengl_on_resize(void) {
}

static void gfx_opengl_start_frame(void) {
    frame_count++;

    glDisable(GL_SCISSOR_TEST);
    glDepthMask(GL_TRUE); // Must be set to clear Z-buffer
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_SCISSOR_TEST);
}

static void gfx_opengl_end_frame(void) {
}

static void gfx_opengl_finish_render(void) {
}

static const char* gfx_opengl_get_name(void) {
    return "OpenGL";
}

void gfx_opengl_experimental_post(int width, int height, bool underwater, const float sun[2], bool sunVisible) {
    experimental_post_render(width, height, underwater, (float)(frame_count % 10000) * 0.05f, sun, sunVisible);
}

void gfx_opengl_shadow_submit(const float *vertices, size_t count, const float center[3]) { gfx_shadow_map_render(vertices,count,center); }
bool gfx_opengl_shadow_ready(void) { return sShadowMap.valid; }

static void gfx_opengl_shutdown(void) {
    gfx_shadow_map_destroy();
    experimental_post_destroy();
    for (int i=0; i<num_textures; ++i) if (tex_cache[i].normal_gltex) glDeleteTextures(1, &tex_cache[i].normal_gltex);
}

struct GfxRenderingAPI gfx_opengl_api = {
    gfx_opengl_z_is_from_0_to_1,
    gfx_opengl_unload_shader,
    gfx_opengl_load_shader,
    gfx_opengl_create_and_load_new_shader,
    gfx_opengl_lookup_shader,
    gfx_opengl_shader_get_info,
    gfx_opengl_new_texture,
    gfx_opengl_select_texture,
    gfx_opengl_upload_texture,
    gfx_opengl_set_sampler_parameters,
    gfx_opengl_set_depth_test,
    gfx_opengl_set_depth_mask,
    gfx_opengl_set_zmode_decal,
    gfx_opengl_set_viewport,
    gfx_opengl_set_scissor,
    gfx_opengl_set_use_alpha,
    gfx_opengl_draw_triangles,
    gfx_opengl_init,
    gfx_opengl_on_resize,
    gfx_opengl_start_frame,
    gfx_opengl_end_frame,
    gfx_opengl_finish_render,
    gfx_opengl_get_name,
    gfx_opengl_shutdown
};
