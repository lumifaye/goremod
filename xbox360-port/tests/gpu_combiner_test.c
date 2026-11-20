/* Exercise the actual xSDK shader compiler, including its register allocation,
 * on host. No console or ROM needed. Location and stride must match gfx_pc.c.
 */
#include "../../WiiU/src/pc/gfx/xbox_combiner.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
  unsigned cases = 0;
  for (unsigned mask = 0; mask < 128; mask++) {
    struct CCFeatures f = {.used_textures = {mask & 1, mask & 2},
                           .opt_alpha = mask & 4,
                           .opt_texture_edge = mask & 8,
                           .opt_fog = mask & 16,
                           .opt_light_map = mask & 32,
                           .opt_2cycle = mask & 64,
                           .num_inputs = 2,
                           .opt_noise = true};
    unsigned seed = f.used_textures[0] ? SHADER_TEXEL0 : SHADER_INPUT_1;
    unsigned second = f.used_textures[1] ? SHADER_TEXEL1 : SHADER_INPUT_2;
    uint8_t cmds[] = {seed,
                      0,
                      SHADER_INPUT_1,
                      0,
                      seed,
                      0,
                      SHADER_INPUT_1,
                      0,
                      SHADER_COMBINED,
                      0,
                      second,
                      0,
                      SHADER_COMBINEDA,
                      0,
                      SHADER_INPUT_2,
                      SHADER_NOISE};
    memcpy(f.shader_cmds, cmds, sizeof(cmds));
    for (int ps = 0; ps < 2; ps++) {
      XboxModule m;
      xb_module(&m, &f, ps);
      assert(m.n < sizeof(m.words) / sizeof(*m.words));
      assert(m.stride ==
             4u * (4 + 2 * (f.used_textures[0] + f.used_textures[1]) +
                   4 * f.opt_fog + 2 * f.opt_light_map +
                   (3 + f.opt_alpha) * f.num_inputs));
      XsdkXscOptions o;
      xsdk_xsc_default_options(&o);
      XsdkXscShader s = {0};
      if (xsdk_xsc_compile(m.words, m.n, &o, &s) != XSDK_XSC_OK) {
        fprintf(stderr, "case %u stage %d: %s\n", mask, ps, s.message);
        return 1;
      }
      assert(s.container && s.container_bytes);
      xsdk_xsc_free(&s);
      cases++;
    }
  }
  printf("%u native shader stage compilations passed\n", cases);
}
