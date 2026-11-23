#ifndef GFX_EXPERIMENTAL_POST_H
#define GFX_EXPERIMENTAL_POST_H
/* Single-frame OpenGL post process. The caller must flush all batched draws
 * first and supply the current target's full dimensions. Multisampled targets
 * cannot be copied portably on GLES2, so leave them untouched. */
static struct { GLuint program, texture, buffer; int width, height, failedWidth, failedHeight; bool attempted; } sExperimentalPost;
static GLuint experimental_post_shader(GLenum type, const char *src) {
    GLuint shader=glCreateShader(type); GLint ok=0;
    if (!shader) return 0;
    glShaderSource(shader,1,&src,NULL); glCompileShader(shader);
    glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if (!ok) { glDeleteShader(shader); return 0; }
    return shader;
}
static bool experimental_post_init(void) {
    if (sExperimentalPost.attempted) return sExperimentalPost.program && sExperimentalPost.texture && sExperimentalPost.buffer;
    sExperimentalPost.attempted=true;
#if defined(USE_GLES) || defined(__ANDROID__)
    const char *vs = "#version 100\nattribute vec2 position; varying vec2 uv; void main(){uv=position*0.5+0.5;gl_Position=vec4(position,0.0,1.0);}";
    const char *fs = "#version 100\nprecision mediump float;\n"
#else
    const char *vs = "#version 120\nattribute vec2 position; varying vec2 uv; void main(){uv=position*0.5+0.5;gl_Position=vec4(position,0.0,1.0);}";
    const char *fs = "#version 120\n"
#endif
        "uniform sampler2D image; uniform vec2 pixel; uniform float phase; uniform float underwater; uniform vec2 sun; uniform float sunVisible; varying vec2 uv;"
        "vec3 bright(vec2 p){vec3 c=texture2D(image,clamp(p,0.0,1.0)).rgb; return max(c-vec3(0.72),0.0);}"
        "void main(){vec2 p=uv;"
        "p += underwater*vec2(sin(uv.y*34.0+phase)*0.0025,sin(uv.x*29.0+phase*0.8)*0.0020);"
        "p=clamp(p,0.0,1.0); vec4 base=texture2D(image,p); vec2 d=pixel*5.0;"
        "vec3 glow=bright(p+vec2(d.x,0.0))+bright(p-vec2(d.x,0.0))+bright(p+vec2(0.0,d.y))+bright(p-vec2(0.0,d.y));"
        "glow+=bright(p+d)+bright(p-d)+bright(p+vec2(d.x,-d.y))+bright(p+vec2(-d.x,d.y));"
        "vec2 wide=pixel*15.0; vec3 wideGlow=bright(p+vec2(wide.x,0.0))+bright(p-vec2(wide.x,0.0))+bright(p+vec2(0.0,wide.y))+bright(p-vec2(0.0,wide.y));"
        "vec3 rays=vec3(0.0); vec2 stepRay=(sun-p)*0.115; vec2 rp=p;"
        "for(int i=0;i<7;i++){rp+=stepRay; rays+=bright(rp);}"
        "float sunGate=smoothstep(0.05,0.25,dot(bright(sun),vec3(0.333)));"
        "gl_FragColor=vec4(min(base.rgb+glow*0.085+wideGlow*0.025+rays*0.08*sunVisible*sunGate*vec3(1.0,0.9,0.7),vec3(1.0)),base.a);}";
    GLuint v=experimental_post_shader(GL_VERTEX_SHADER,vs), f=experimental_post_shader(GL_FRAGMENT_SHADER,fs);
    if (!v || !f) { if(v) glDeleteShader(v); if(f) glDeleteShader(f); return false; }
    GLuint p=glCreateProgram(); glAttachShader(p,v); glAttachShader(p,f); glBindAttribLocation(p,0,"position"); glLinkProgram(p);
    glDeleteShader(v); glDeleteShader(f); GLint ok=0; glGetProgramiv(p,GL_LINK_STATUS,&ok);
    if (!ok) { glDeleteProgram(p); return false; }
    sExperimentalPost.program=p; glGenTextures(1,&sExperimentalPost.texture); glGenBuffers(1,&sExperimentalPost.buffer);
    return sExperimentalPost.texture && sExperimentalPost.buffer;
}
// The default Android framebuffer is not guaranteed to be copy-compatible
// with RGBA textures, and allocations can fail on memory-constrained GPUs.
// A failed copy must never be drawn over the valid scene as a black texture.
// The texture is already bound; this helper touches no other GL state.
static bool experimental_post_copy(int width, int height) {
    if (sExperimentalPost.failedWidth == width && sExperimentalPost.failedHeight == height) return false;
    if (sExperimentalPost.width != width || sExperimentalPost.height != height) {
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,width,height,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL);
        if (glGetError() != GL_NO_ERROR) {
            sExperimentalPost.failedWidth=width; sExperimentalPost.failedHeight=height;
            sExperimentalPost.width=0; sExperimentalPost.height=0;
            return false;
        }
        sExperimentalPost.width=width; sExperimentalPost.height=height;
    }
    glCopyTexSubImage2D(GL_TEXTURE_2D,0,0,0,0,0,width,height);
    if (glGetError() != GL_NO_ERROR) {
        sExperimentalPost.failedWidth=width; sExperimentalPost.failedHeight=height;
        return false;
    }
    sExperimentalPost.failedWidth=0; sExperimentalPost.failedHeight=0;
    return true;
}
static void experimental_post_render(int width, int height, bool underwater, float phase, const float sun[2], bool sunVisible) {
    if (width <= 0 || height <= 0) return;
    GLint samples=0, maxTexture=0;
    glGetIntegerv(GL_SAMPLE_BUFFERS,&samples); glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maxTexture);
    if (samples || width>maxTexture || height>maxTexture || !experimental_post_init()) return;
    GLint program,buffer,active,texture,viewport[4]; GLboolean depthMask,colors[4];
    glGetIntegerv(GL_CURRENT_PROGRAM,&program); glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&buffer);
    glGetIntegerv(GL_ACTIVE_TEXTURE,&active); glActiveTexture(GL_TEXTURE0); glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);
    glGetIntegerv(GL_VIEWPORT,viewport); glGetBooleanv(GL_DEPTH_WRITEMASK,&depthMask); glGetBooleanv(GL_COLOR_WRITEMASK,colors);
    GLboolean depth=glIsEnabled(GL_DEPTH_TEST), blend=glIsEnabled(GL_BLEND), cull=glIsEnabled(GL_CULL_FACE), scissor=glIsEnabled(GL_SCISSOR_TEST);
    GLint enabled,size,type,normalized,stride,attribBuffer; void *pointer=NULL;
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_ENABLED,&enabled); glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_SIZE,&size);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_TYPE,&type); glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_NORMALIZED,&normalized);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_STRIDE,&stride); glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_BUFFER_BINDING,&attribBuffer);
    glGetVertexAttribPointerv(0,GL_VERTEX_ATTRIB_ARRAY_POINTER,&pointer);
    // Ignore earlier rendering errors, but never draw if our own setup or
    // copy fails. Bound the drain to handle a lost context without hanging.
    bool glReady = false;
    for (int i=0; i<16; ++i) {
        if (glGetError() == GL_NO_ERROR) { glReady = true; break; }
    }
    if (!glReady) { glActiveTexture(active); return; }
    glBindTexture(GL_TEXTURE_2D,sExperimentalPost.texture);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR); glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE); glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    if (glGetError() != GL_NO_ERROR) {
        sExperimentalPost.failedWidth=width; sExperimentalPost.failedHeight=height;
        glBindTexture(GL_TEXTURE_2D,texture);
        glActiveTexture(active);
        return;
    }
    if (!experimental_post_copy(width,height)) {
        glBindTexture(GL_TEXTURE_2D,texture);
        glActiveTexture(active);
        return;
    }
    glDisable(GL_DEPTH_TEST); glDisable(GL_BLEND); glDisable(GL_CULL_FACE); glDisable(GL_SCISSOR_TEST);
    glDepthMask(GL_FALSE); glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE); glViewport(0,0,width,height);
    glUseProgram(sExperimentalPost.program);
    glUniform1i(glGetUniformLocation(sExperimentalPost.program,"image"),0);
    glUniform2f(glGetUniformLocation(sExperimentalPost.program,"pixel"),1.0f/width,1.0f/height);
    glUniform1f(glGetUniformLocation(sExperimentalPost.program,"phase"),phase);
    glUniform1f(glGetUniformLocation(sExperimentalPost.program,"underwater"),underwater ? 1.0f : 0.0f);
    glUniform2f(glGetUniformLocation(sExperimentalPost.program,"sun"),sun[0],sun[1]);
    glUniform1f(glGetUniformLocation(sExperimentalPost.program,"sunVisible"),sunVisible && !underwater ? 1.0f : 0.0f);
    static const GLfloat quad[]={-1,-1, 1,-1, -1,1, 1,1};
    glBindBuffer(GL_ARRAY_BUFFER,sExperimentalPost.buffer); glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STREAM_DRAW);
    glEnableVertexAttribArray(0); glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,0,(void *)0); glDrawArrays(GL_TRIANGLE_STRIP,0,4);
    glBindBuffer(GL_ARRAY_BUFFER,attribBuffer); glVertexAttribPointer(0,size,type,normalized,stride,pointer);
    if (enabled) glEnableVertexAttribArray(0); else glDisableVertexAttribArray(0);
    glBindBuffer(GL_ARRAY_BUFFER,buffer); glBindTexture(GL_TEXTURE_2D,texture); glActiveTexture(active); glUseProgram(program);
    glViewport(viewport[0],viewport[1],viewport[2],viewport[3]); glDepthMask(depthMask); glColorMask(colors[0],colors[1],colors[2],colors[3]);
    if(depth) glEnable(GL_DEPTH_TEST);
    if(blend) glEnable(GL_BLEND);
    if(cull) glEnable(GL_CULL_FACE);
    if(scissor) glEnable(GL_SCISSOR_TEST);
}
static void experimental_post_destroy(void) {
    if(sExperimentalPost.program) glDeleteProgram(sExperimentalPost.program);
    if(sExperimentalPost.texture) glDeleteTextures(1,&sExperimentalPost.texture);
    if(sExperimentalPost.buffer) glDeleteBuffers(1,&sExperimentalPost.buffer);
    memset(&sExperimentalPost,0,sizeof(sExperimentalPost));
}
#endif
