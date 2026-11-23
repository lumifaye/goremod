"""Exercise the real combiner revalidation against a recycled shader slot."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
for platform in ('PC','Android'):
    path=root/platform/'src/pc/gfx/gfx_pc.c'
    source=path.read_text()
    start=source.index('static struct ColorCombiner *gfx_revalidate_combiner(')
    end=source.index('\nstatic struct ColorCombiner *gfx_lookup_or_create_color_combiner(',start)
    block=source[start:end]
    lookup=source[end:source.index('\nvoid gfx_texture_cache_clear(',end)]
    assert lookup.count('gfx_revalidate_combiner(prev_combiner)') == 2
    gl=(root/platform/'src/pc/gfx/gfx_opengl.c').read_text()
    assert 'program->hash == combiner->hash' in gl
    assert 'if (prg->opengl_program_id) glDeleteProgram(prg->opengl_program_id);' in gl
    test=r'''
#include <assert.h>
#include <stdbool.h>
struct ShaderProgram { int hash; };
struct ColorCombiner { int hash; struct ShaderProgram *prg; };
struct Api { int unused; } gfx_opengl_api, other_api, *gfx_rapi=&gfx_opengl_api;
static int flushed, lookedup;
static struct ShaderProgram replacement={42};
static bool gfx_opengl_shader_matches(const struct ShaderProgram *p, const struct ColorCombiner *c) { return p && p->hash==c->hash; }
static void gfx_flush(void) { assert(!lookedup); ++flushed; }
static struct ShaderProgram *gfx_lookup_or_create_shader_program(struct ColorCombiner *c) { assert(flushed && c->hash==42); ++lookedup; return &replacement; }
BLOCK
int main(void) {
    struct ShaderProgram slot={42}; struct ColorCombiner c={42,&slot};
    assert(gfx_revalidate_combiner(&c)==&c && !flushed && !lookedup);
    slot.hash=99; assert(gfx_revalidate_combiner(&c)==&c);
    assert(flushed==1 && lookedup==1 && c.prg==&replacement);
    gfx_rapi=&other_api; slot.hash=99; c.prg=&slot;
    gfx_revalidate_combiner(&c); assert(flushed==1 && lookedup==1 && c.prg==&slot);
}
'''.replace('BLOCK',block)
    with tempfile.TemporaryDirectory() as tmp:
        exe=str(Path(tmp)/'test')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-x','c','-','-o',exe],input=test.encode(),check=True)
        subprocess.run([exe],check=True)
    print(platform, 'recycled shader cache slot revalidation: ok')
