/* Experimental GPU shadow map. Include after gfx_gl_submission.h and
 * gfx_menu_target.h. The caller drains its triangle batch before use. */
#ifndef GFX_SHADOW_MAP_H
#define GFX_SHADOW_MAP_H
#define GFX_SHADOW_MAP_SIZE 2048
static struct {
    GLuint framebuffer, texture, depth, program, vbo;
    GLint center_location;
    float center[3];
    bool valid, attempted;
} sShadowMap;

static bool gfx_shadow_map_init(void) {
    if (sShadowMap.attempted) return sShadowMap.program && sShadowMap.framebuffer;
    sShadowMap.attempted = true;
#ifdef USE_GLES
    GLint range[2], precision=0;
    glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER,GL_HIGH_FLOAT,range,&precision);
    if (precision == 0) return false;
#endif
#if FOR_WINDOWS || defined(OSX_BUILD)
    // OpenGL 2.1 implementations may not expose framebuffer objects.
    if (!glGenFramebuffers || !glBindFramebuffer || !glFramebufferTexture2D ||
        !glGenRenderbuffers || !glRenderbufferStorage || !glFramebufferRenderbuffer ||
        !glCheckFramebufferStatus) return false;
#endif
#if defined(USE_GLES) || defined(__ANDROID__)
    const char *version = "#version 100\nprecision highp float;\n";
#else
    const char *version = "#version 120\n";
#endif
    char vs[2048], fs[1024];
    snprintf(vs, sizeof(vs), "%s"
        "attribute vec3 position; uniform vec3 center;"
        "void main(){ vec3 p=position-center;"
        "vec3 L=normalize(vec3(-0.35,0.80,0.48));"
        "vec3 R=normalize(cross(vec3(0.0,1.0,0.0),L));"
        "vec3 U=cross(L,R);"
        "gl_Position=vec4(dot(p,R)/4800.0,dot(p,U)/4800.0,-dot(p,L)/8000.0,1.0);}",version);
    snprintf(fs, sizeof(fs), "%s"
        "void main(){float z=min(gl_FragCoord.z,0.999999);"
        "vec3 enc=fract(z*vec3(1.0,255.0,65025.0));"
        "enc-=enc.yzz*vec3(1.0/255.0,1.0/255.0,0.0);"
        "gl_FragColor=vec4(enc,1.0);}",version);
    GLuint vert=experimental_post_shader(GL_VERTEX_SHADER,vs), frag=experimental_post_shader(GL_FRAGMENT_SHADER,fs);
    if (!vert || !frag) { if(vert) glDeleteShader(vert); if(frag) glDeleteShader(frag); return false; }
    GLuint program=glCreateProgram();
    glAttachShader(program,vert); glAttachShader(program,frag);
    glBindAttribLocation(program,0,"position"); glLinkProgram(program);
    glDeleteShader(vert); glDeleteShader(frag);
    GLint ok=0; glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if (!ok) { glDeleteProgram(program); return false; }
    sShadowMap.program=program;
    sShadowMap.center_location=glGetUniformLocation(program,"center");
    glGenBuffers(1,&sShadowMap.vbo);
    glGenTextures(1,&sShadowMap.texture);
    glBindTexture(GL_TEXTURE_2D,sShadowMap.texture);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,GFX_SHADOW_MAP_SIZE,GFX_SHADOW_MAP_SIZE,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL);
    glGenRenderbuffers(1,&sShadowMap.depth);
    glBindRenderbuffer(GL_RENDERBUFFER,sShadowMap.depth);
    glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH_COMPONENT16,GFX_SHADOW_MAP_SIZE,GFX_SHADOW_MAP_SIZE);
    glGenFramebuffers(1,&sShadowMap.framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,sShadowMap.framebuffer);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,sShadowMap.texture,0);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,sShadowMap.depth);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) {
        glDeleteFramebuffers(1,&sShadowMap.framebuffer); sShadowMap.framebuffer=0; return false;
    }
    return true;
}

static void gfx_shadow_map_render(const float *vertices, size_t count, const float center[3]) {
    sShadowMap.valid=false;
    if (!vertices || count == 0) return;
    GLint fb,rb,tex,active,program,buffer,viewport[4],depthFunc;
    GLint attrEnabled,attrSize,attrType,attrNormalized,attrStride,attrBuffer;
    void *attrPointer=NULL;
    GLboolean depthMask,colorMask[4],blend=glIsEnabled(GL_BLEND),depth=glIsEnabled(GL_DEPTH_TEST);
    GLboolean scissor=glIsEnabled(GL_SCISSOR_TEST),cull=glIsEnabled(GL_CULL_FACE),poly=glIsEnabled(GL_POLYGON_OFFSET_FILL),dither=glIsEnabled(GL_DITHER);
    GLfloat clearColor[4];
    glGetIntegerv(GL_FRAMEBUFFER_BINDING,&fb); glGetIntegerv(GL_RENDERBUFFER_BINDING,&rb);
    glGetIntegerv(GL_ACTIVE_TEXTURE,&active); glGetIntegerv(GL_TEXTURE_BINDING_2D,&tex);
    glGetIntegerv(GL_CURRENT_PROGRAM,&program); glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&buffer);
    glGetIntegerv(GL_VIEWPORT,viewport); glGetIntegerv(GL_DEPTH_FUNC,&depthFunc);
    glGetBooleanv(GL_DEPTH_WRITEMASK,&depthMask); glGetBooleanv(GL_COLOR_WRITEMASK,colorMask);
    glGetFloatv(GL_COLOR_CLEAR_VALUE,clearColor);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_ENABLED,&attrEnabled);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_SIZE,&attrSize);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_TYPE,&attrType);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_NORMALIZED,&attrNormalized);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_STRIDE,&attrStride);
    glGetVertexAttribiv(0,GL_VERTEX_ATTRIB_ARRAY_BUFFER_BINDING,&attrBuffer);
    glGetVertexAttribPointerv(0,GL_VERTEX_ATTRIB_ARRAY_POINTER,&attrPointer);
    if (gfx_shadow_map_init()) {
        glBindFramebuffer(GL_FRAMEBUFFER,sShadowMap.framebuffer);
        glViewport(0,0,GFX_SHADOW_MAP_SIZE,GFX_SHADOW_MAP_SIZE);
        glDisable(GL_SCISSOR_TEST); glDisable(GL_BLEND); glDisable(GL_CULL_FACE); glDisable(GL_POLYGON_OFFSET_FILL); glDisable(GL_DITHER);
        glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LEQUAL); glDepthMask(GL_TRUE); glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
        glClearColor(1,1,1,1); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
        glUseProgram(sShadowMap.program); glUniform3f(sShadowMap.center_location,center[0],center[1],center[2]);
        glBindBuffer(GL_ARRAY_BUFFER,sShadowMap.vbo); glBufferData(GL_ARRAY_BUFFER,count*3*sizeof(float),vertices,GL_STREAM_DRAW);
        glEnableVertexAttribArray(0); glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,0,NULL);
        glDrawArrays(GL_TRIANGLES,0,(GLsizei)count);
        memcpy(sShadowMap.center,center,sizeof(sShadowMap.center)); sShadowMap.valid=true;
    }
    glBindFramebuffer(GL_FRAMEBUFFER,fb); glBindRenderbuffer(GL_RENDERBUFFER,rb);
    glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
    if (attrEnabled) {
        glBindBuffer(GL_ARRAY_BUFFER,attrBuffer);
        glVertexAttribPointer(0,attrSize,attrType,attrNormalized,attrStride,attrPointer);
    } else glDisableVertexAttribArray(0);
    glBindBuffer(GL_ARRAY_BUFFER,buffer); glUseProgram(program);
    glActiveTexture(active); glBindTexture(GL_TEXTURE_2D,tex);
    glDepthFunc(depthFunc); glDepthMask(depthMask); glColorMask(colorMask[0],colorMask[1],colorMask[2],colorMask[3]);
    glClearColor(clearColor[0],clearColor[1],clearColor[2],clearColor[3]);
    if(blend) glEnable(GL_BLEND); else glDisable(GL_BLEND);
    if(depth) glEnable(GL_DEPTH_TEST); else glDisable(GL_DEPTH_TEST);
    if(scissor) glEnable(GL_SCISSOR_TEST); else glDisable(GL_SCISSOR_TEST);
    if(cull) glEnable(GL_CULL_FACE); else glDisable(GL_CULL_FACE);
    if(poly) glEnable(GL_POLYGON_OFFSET_FILL); else glDisable(GL_POLYGON_OFFSET_FILL);
    if(dither) glEnable(GL_DITHER); else glDisable(GL_DITHER);
}

static void gfx_shadow_map_destroy(void) {
    if(sShadowMap.program) glDeleteProgram(sShadowMap.program);
    if(sShadowMap.framebuffer) glDeleteFramebuffers(1,&sShadowMap.framebuffer);
    if(sShadowMap.texture) glDeleteTextures(1,&sShadowMap.texture);
    if(sShadowMap.depth) glDeleteRenderbuffers(1,&sShadowMap.depth);
    if(sShadowMap.vbo) glDeleteBuffers(1,&sShadowMap.vbo);
    memset(&sShadowMap,0,sizeof(sShadowMap));
}
#endif
