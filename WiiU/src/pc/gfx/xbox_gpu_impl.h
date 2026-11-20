/* Xenos backend implementation included by gfx_xbox360.c. CPU texture copies
 * also serve as backing store when recycling physical pages or falling back. */
enum { VB_BLOCK = 256 * 1024, VB_BLOCKS = 4, TEX_PAGE = 1024 * 1024, TEX_PAGES = 48 };
static volatile uint32_t *vertex_mem, *tex_pages[TEX_PAGES];
static uint32_t vertex_base;
static unsigned block, used, fences[VB_BLOCKS], pages, page_left, page_size, tex_bytes;
static bool native;
static unsigned target_w, target_h;
static struct ShaderProgram *bound;
static bool state_valid;
static int last_vp[4], last_sc[4];
static bool last_test, last_write, last_blend, last_decal;

static bool compile_program(struct ShaderProgram *p) {
    XboxModule m;
    XsdkXscOptions opts;
    xsdk_xsc_default_options(&opts);
    for (int ps = 0; ps < 2; ++ps) {
        xb_module(&m, &p->f, ps);
        XsdkXscShader *s = &p->compiled[ps];
        if (xsdk_xsc_compile(m.words, m.n, &opts, s) != XSDK_XSC_OK) {
            xsdk_log_write("xbox GPU: %s compiler: %s", ps ? "pixel" : "vertex", s->message);
            return false;
        }
        if (!NT_SUCCESS(
                xsdk_shader_load(&p->gpu[ps], (const uint32_t *) s->container, s->container_bytes)))
            return false;
        if (!ps
            && !NT_SUCCESS(xsdk_shader_set_vertex_layout(&p->gpu[0], m.layout, m.elements, &m.stride)))
            return false;
    }
    p->ready = true;
    return true;
}
static void set_program(struct ShaderProgram *p) {
    xsdk_gpu_set_shaders(&p->gpu[0], &p->gpu[1]);
    for (unsigned ps = 0; ps < 2; ++ps) {
        XsdkXscShader *s = &p->compiled[ps];
        for (unsigned i = 0; i < s->need_count; i++)
            if (s->needs[i].kind == XSDK_XSC_LITERAL) {
                float c[4];
                for (int k = 0; k < 4; k++)
                    c[k] = (float) s->needs[i].value[k];
                if (ps)
                    xsdk_gpu_set_pixel_constants(s->needs[i].reg, c, 1);
                else
                    xsdk_gpu_set_vertex_constants(s->needs[i].reg, c, 1);
            }
    }
    bound = p;
}
static bool retire_pages(void) {
    if (!NT_SUCCESS(xsdk_gpu_wait(xsdk_gpu_fence(), 1000)))
        return false;
    while (pages)
        xsdk_gpu_free(tex_pages[--pages]);
    page_left = page_size = tex_bytes = 0;
    for (unsigned i = 0; i < count; i++)
        textures[i].gpu.texels = NULL;
    return true;
}
static bool prepare_texture(struct Texture *t) {
    if (t->gpu.texels)
        return true;
    if (!t->data || !NT_SUCCESS(xsdk_texture_init(&t->gpu, XSDK_FORMAT_R8G8B8A8, t->w, t->h, 1, true)))
        return false;
    unsigned bytes = (t->gpu.size_bytes + 4095u) & ~4095u;
    if (bytes > page_left) {
        unsigned size = bytes > TEX_PAGE ? bytes : TEX_PAGE;
        if (size > TEX_PAGE * TEX_PAGES)
            return false;
        if ((pages == TEX_PAGES || tex_bytes + size > TEX_PAGE * TEX_PAGES) && !retire_pages())
            return false;
        volatile uint32_t *page = xsdk_gpu_alloc(size);
        if (!page)
            return false;
        tex_pages[pages++] = page;
        page_size = page_left = size;
        tex_bytes += size;
    }
    xsdk_texture_attach(&t->gpu, tex_pages[pages - 1] + (page_size - page_left) / 4);
    page_left -= bytes;
    xsdk_texture_upload(&t->gpu, 0, t->data, t->w * 4);
    xsdk_gpu_invalidate(t->gpu.address, t->gpu.size_bytes);
    return true;
}
static unsigned address_mode(unsigned mode) {
    return (mode & 2) ? XSDK_ADDRESS_CLAMP : (mode & 1) ? XSDK_ADDRESS_MIRROR : XSDK_ADDRESS_WRAP;
}
static bool gpu_draw_batch(const float *vertices, size_t len) {
    if (!active->ready && !compile_program(active))
        return false;
    if (bound != active)
        set_program(active);
    XsdkXscShader *ps = &active->compiled[1];
    // An allocation can recycle all texture pages. Prepare both before
    // binding either; if the second reset the pool, restore the first.
    for (int pass = 0; pass < 2; pass++)
        for (int i = 0; i < 2; i++)
            if (active->f.used_textures[i]) {
                if (selected[i] >= count || !prepare_texture(&textures[selected[i]]))
                    return false;
            }
    for (unsigned i = 0; i < ps->resource_count; i++) {
        XsdkXscResource *res = &ps->resources[i];
        if (res->kind == XSDK_XSC_PUSH_CONSTANTS) {
            float ambient[] = { gVertexColor[0] / 255.f, gVertexColor[1] / 255.f,
                                gVertexColor[2] / 255.f, 1 };
            xsdk_gpu_set_pixel_constants(res->reg, ambient, 1);
        } else if (res->kind == XSDK_XSC_SAMPLER) {
            if (res->binding > 1)
                return false;
            struct Texture *t = &textures[selected[res->binding]];
            if (!t->gpu.texels)
                return false;
            unsigned filter = t->linear ? XSDK_FILTER_LINEAR : XSDK_FILTER_POINT;
            XsdkSamplerState ss;
            xsdk_texture_sampler_state(&ss, &(XsdkSampler) { .min_filter = filter,
                                                             .mag_filter = filter,
                                                             .mip_filter = XSDK_FILTER_POINT,
                                                             .address_u = address_mode(t->wrap[0]),
                                                             .address_v = address_mode(t->wrap[1]) });
            xsdk_gpu_set_texture(res->reg, &t->gpu, &ss);
        }
    }
    size_t bytes = len * sizeof(float);
    if (bytes > VB_BLOCK)
        return false;
    if (used + bytes > VB_BLOCK) {
        fences[block] = xsdk_gpu_fence();
        block = (block + 1) % VB_BLOCKS;
        used = 0;
        if (fences[block] && !NT_SUCCESS(xsdk_gpu_wait(fences[block], 1000)))
            return false;
    }
    volatile uint32_t *dst = vertex_mem + (block * VB_BLOCK + used) / 4;
    for (size_t i = 0; i < len; i++) {
        uint32_t word;
        memcpy(&word, vertices + i, 4);
        dst[i] = word;
    }
    uint32_t addr = vertex_base + block * VB_BLOCK + used;
    xsdk_gpu_invalidate(addr, bytes);
    xsdk_gpu_set_vertices(0, addr, bytes);
    used += (bytes + 31u) & ~31u;
    if (!state_valid || memcmp(vp, last_vp, sizeof vp)) {
        xsdk_gpu_set_viewport(vp[0], (int) target_h - vp[1] - vp[3], vp[2], vp[3], 0, 1);
        memcpy(last_vp, vp, sizeof vp);
    }
    if (!state_valid || memcmp(sc, last_sc, sizeof sc)) {
        int x = sc[0], y = (int) target_h - sc[1] - sc[3], r = x + sc[2], b = y + sc[3];
        if (x < 0)
            x = 0;
        if (y < 0)
            y = 0;
        if (r > (int) target_w)
            r = target_w;
        if (b > (int) target_h)
            b = target_h;
        if (r <= x || b <= y)
            return true;
        xsdk_gpu_set_scissor(x, y, r - x, b - y);
        memcpy(last_sc, sc, sizeof sc);
    }
    if (!state_valid || last_test != test_z || last_write != write_z) {
        XsdkDepthStencilState ds;
        xsdk_gpu_depth_stencil_state(&ds,
                                     &(XsdkDepthStencil) { .depth_test = test_z,
                                                           .depth_write = test_z && write_z,
                                                           .depth_compare = XSDK_COMPARE_LESS_EQUAL });
        xsdk_gpu_set_depth_stencil(&ds);
        last_test = test_z;
        last_write = write_z;
    }
    if (!state_valid || last_blend != blend) {
        XsdkBlendState bs;
        xsdk_gpu_blend_state(
            &bs, &(XsdkBlend) { .write_mask = XSDK_WRITE_ALL,
                                .color_source = blend ? XSDK_BLEND_SRC_ALPHA : XSDK_BLEND_ONE,
                                .color_dest = blend ? XSDK_BLEND_ONE_MINUS_SRC_ALPHA : XSDK_BLEND_ZERO,
                                .alpha_source = XSDK_BLEND_ONE,
                                .alpha_dest = XSDK_BLEND_ZERO });
        xsdk_gpu_set_blend(&bs);
        last_blend = blend;
    }
    if (!state_valid || last_decal != decal) {
        XsdkRasterState rs;
        xsdk_gpu_raster_state(
            &rs, &(XsdkRaster) { .cull = XSDK_CULL_NONE, .depth_bias = decal ? -0.0001f : 0 });
        xsdk_gpu_set_raster(&rs);
        last_decal = decal;
    }
    state_valid = true;
    xsdk_gpu_draw(XSDK_PRIMITIVE_TRIANGLE_LIST, bytes / active->stride);
    return true;
}
