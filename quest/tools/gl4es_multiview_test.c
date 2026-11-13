// Host test of the multiview copy-back slots in quest/gl4es.patch
// (src/gl/multiview.c): a 2D texture drawn into keeps a slot pointing at its
// gltexture_t; deleting the texture must give the slot back and delete the
// two-layer array (mv_texture_deleted), or mv_framebuffer_left reads freed
// memory, the array leaks and the 64 slots run out.
//
// The driver is a mock (proc_address below); multiview.c is compiled as it is,
// with AddressSanitizer:
//   sh quest/tools/gl4es_multiview_test.sh        (DEPS=../deps by default)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "multiview.h"
#include "../glx/hardext.h"
#include "gl4es.h"
#include "glstate.h"
#include "loader.h"

// what multiview.c takes from the rest of gl4es
glstate_t* glstate;
hardext_t hardext;
void* gles;
GLenum get_texture_min_filter(gltexture_t* t, glsampler_t* s) { (void)t; (void)s; return GL_LINEAR; }
GLenum get_texture_wrap_s(gltexture_t* t, glsampler_t* s) { (void)t; (void)s; return GL_REPEAT; }
GLenum get_texture_wrap_t(gltexture_t* t, glsampler_t* s) { (void)t; (void)s; return GL_REPEAT; }
static gltexture_t* registry[2];     // what gl4es_getTexture finds (copy_layers)
gltexture_t* gl4es_getTexture(GLenum target, GLuint texture)
{
    (void)target;
    for(int i = 0; i < 2; i++) if(registry[i] && registry[i]->texture == texture) return registry[i];
    return NULL;
}
char* gl4es_inplace_replace(char* b, int* n, const char* s, const char* d) { (void)n; (void)s; (void)d; return b; }
char* gl4es_inplace_replace_simple(char* b, int* n, const char* s, const char* d) { (void)n; (void)s; (void)d; return b; }

// the mock driver: texture names handed out and still alive
#define NAMES 100000
static unsigned char alive[NAMES];
static GLuint next_name = 1000;
static int live_count(void) { int n = 0; for(int i = 0; i < NAMES; i++) n += alive[i]; return n; }
static void m_GenTextures(GLsizei n, GLuint* t) { for(int i = 0; i < n; i++) { t[i] = next_name++; alive[t[i]] = 1; } }
static void m_DeleteTextures(GLsizei n, const GLuint* t)
{
    for(int i = 0; i < n; i++) {
        if(t[i] && !alive[t[i]]) { fprintf(stderr, "FAIL: texture %u deleted twice\n", t[i]); exit(1); }
        alive[t[i]] = 0;
    }
}
static GLint active = GL_TEXTURE0;
static void m_GetIntegerv(GLenum p, GLint* v) { *v = p == GL_ACTIVE_TEXTURE ? active : 0; }
static void m_ActiveTexture(GLenum u) { active = (GLint)u; }
static const GLubyte* m_GetString(GLenum e) { (void)e; return (const GLubyte*)"GL_OVR_multiview2 GL_EXT_clip_cull_distance"; }
static GLenum m_GetError(void) { return 0; }
static GLboolean m_IsEnabled(GLenum e) { (void)e; return 0; }
static int blits;
static void m_Blit(GLint a, GLint b, GLint c, GLint d, GLint e, GLint f, GLint g, GLint h, GLbitfield m, GLenum fl)
{ (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; (void)g; (void)h; (void)m; (void)fl; blits++; }
static int copies3d, copied_layer[2];
static void m_CopyTexSubImage3D(GLenum t, GLint lv, GLint x, GLint y, GLint z, GLint sx, GLint sy, GLsizei w, GLsizei h)
{ (void)t; (void)lv; (void)x; (void)y; (void)sx; (void)sy; (void)w; (void)h; copies3d++; if(z >= 0 && z < 2) copied_layer[z]++; }
static void nop(void) {}

void* proc_address(void* lib, const char* name)
{
    (void)lib;
    if(!strcmp(name, "glGenTextures")) return (void*)m_GenTextures;
    if(!strcmp(name, "glDeleteTextures")) return (void*)m_DeleteTextures;
    if(!strcmp(name, "glGetIntegerv")) return (void*)m_GetIntegerv;
    if(!strcmp(name, "glActiveTexture")) return (void*)m_ActiveTexture;
    if(!strcmp(name, "glGetString")) return (void*)m_GetString;
    if(!strcmp(name, "glGetError")) return (void*)m_GetError;
    if(!strcmp(name, "glIsEnabled")) return (void*)m_IsEnabled;
    if(!strcmp(name, "glBlitFramebuffer")) return (void*)m_Blit;
    if(!strcmp(name, "glCopyTexSubImage3D")) return (void*)m_CopyTexSubImage3D;
    return (void*)nop;      // every other entry point: nothing to check
}

static gltexture_t* new_tex(GLuint name, int w, int h)
{
    gltexture_t* t = calloc(1, sizeof *t);
    t->texture = name; t->glname = name; t->width = w; t->height = h;
    t->format = GL_RGBA; t->type = GL_UNSIGNED_BYTE;
    return t;
}
// what gl4es_glDeleteTextures does with it
static void delete_tex(gltexture_t* t) { mv_texture_deleted(t); free(t); }

#define CHECK(c, ...) do { if(!(c)) { fprintf(stderr, "FAIL line %d: ", __LINE__); fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); exit(1); } } while(0)

int main(void)
{
    glstate = calloc(1, sizeof *glstate);
    CHECK(gl4es_multiview_enable(), "multiview not enabled on the mock driver");

    // one texture drawn into, deleted, then its framebuffer left
    gltexture_t* t = new_tex(5, 64, 32);
    CHECK(mv_attach(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, t, 3, GL_TEXTURE_2D), "attach");
    CHECK(mv_copy_slots_used() == 1, "slot taken: %d", mv_copy_slots_used());
    CHECK(live_count() == 1, "array made: %d", live_count());
    mv_framebuffer_left(3);
    CHECK(blits == 1, "copied back once: %d", blits);
    delete_tex(t);
    CHECK(mv_copy_slots_used() == 0, "slot given back: %d", mv_copy_slots_used());
    CHECK(live_count() == 0, "array deleted: %d", live_count());
    mv_framebuffer_left(3);     // read the freed record before the fix (ASan: heap-use-after-free)
    CHECK(blits == 1, "no copy for the deleted texture: %d", blits);

    // stress: far more textures than slots, each attached (colour + depth on
    // varied framebuffers) and deleted, the framebuffers left in between
    for(int i = 0; i < 5000; i++) {
        gltexture_t* c = new_tex(10 + 2 * i, 128 + i % 7, 64);
        gltexture_t* d = new_tex(11 + 2 * i, 128 + i % 7, 64);
        d->format = GL_DEPTH_COMPONENT;
        GLuint fb = 20 + i % 13;
        CHECK(mv_attach(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, c, fb, GL_TEXTURE_2D), "attach colour %d (slots full?)", i);
        CHECK(mv_attach(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, d, fb, GL_TEXTURE_2D), "attach depth %d (slots full?)", i);
        mv_framebuffer_left(fb);
        if(i & 1) { delete_tex(c); delete_tex(d); }
        else { delete_tex(d); mv_framebuffer_left(fb); delete_tex(c); }
        mv_framebuffer_left(fb);
    }
    CHECK(mv_copy_slots_used() == 0, "slots after the stress: %d", mv_copy_slots_used());
    CHECK(live_count() == 0, "arrays leaked: %d", live_count());

    // a texture never multiview (no array, no slot): nothing to do, no crash
    gltexture_t* plain = new_tex(7, 16, 16);
    delete_tex(plain);
    mv_texture_deleted(NULL);

    // one still attached stays usable after another is deleted
    gltexture_t* a = new_tex(8, 32, 32), *b = new_tex(9, 32, 32);
    mv_attach(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, a, 40, GL_TEXTURE_2D);
    mv_attach(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, b, 41, GL_TEXTURE_2D);
    delete_tex(a);
    int before = blits;
    mv_framebuffer_left(41);
    CHECK(blits == before + 1 && mv_copy_slots_used() == 1 && live_count() == 1, "the other texture kept");
    delete_tex(b);
    CHECK(mv_copy_slots_used() == 0 && live_count() == 0, "all given back");

    // both eyes into a 2D texture's own array (the per-eye shadow mask): each
    // layer by glCopyTexSubImage3D, never a blit (a blit into layer 1 writes
    // nothing on the Quest's driver); the array goes when the texture does
    gltexture_t* eyes = new_tex(60, 200, 100), *twin = new_tex(61, 200, 100);
    mv_attach(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, eyes, 50, 0x84F5 /* GL_TEXTURE_RECTANGLE_ARB: no copy-back slot */);
    CHECK(eyes->mvarray && mv_copy_slots_used() == 0, "eyes' array");
    registry[0] = eyes; registry[1] = twin;
    before = blits;
    CHECK(gl4es_multiview_copy_layers(60, 61), "copy_layers");
    CHECK(blits == before && copies3d == 2 && copied_layer[0] == 1 && copied_layer[1] == 1, "layers copied by CopyTexSubImage3D: blits %d, copies %d", blits - before, copies3d);
    CHECK(twin->mvarray && twin->mv_layered, "twin's array");
    registry[0] = registry[1] = NULL;
    delete_tex(twin); delete_tex(eyes);
    CHECK(live_count() == 0, "arrays after copy_layers: %d", live_count());

    printf("gl4es multiview slots: OK (%d copy-backs)\n", blits);
    free(glstate);
    return 0;
}
