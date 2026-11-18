import os, subprocess, tempfile
from pathlib import Path
root = Path(__file__).resolve().parents[2]
src = (root / 'WiiU/src/pc/djui/djui_interactable.c').read_text()
hit = src[src.index('static void djui_interactable_cursor_update_active('):src.index('\nbool djui_interactable_is_binding', src.index('static void djui_interactable_cursor_update_active('))]
update = src[src.index('void djui_interactable_update(void) {'):src.index('\nvoid djui_interactable_hook_hover', src.index('void djui_interactable_update(void) {'))]
pre = r'''#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <assert.h>
#define TARGET_WII_U 1
#define L_MOUSE_BUTTON 1
#define R_MOUSE_BUTTON 2
#define PAD_BUTTON_A 1
#define PAD_BUTTON_B 2
#define PAD_BUTTON_Z 4
#define PAD_BUTTON_START 8
#define SOUND_MENU_MESSAGE_NEXT_PAGE 0
typedef uint16_t u16;
typedef struct { u16 button; } OSContPad;
struct DjuiBase;
struct Child { struct DjuiBase *base; struct Child *next; };
struct DjuiInteractable { int enabled; };
struct DjuiBase { bool visible, enabled; struct DjuiInteractable *interactable; struct Child *child; float x,y,w,h; };
#define DjuiBaseChild Child
struct Root { struct DjuiBase base; };
static struct Root root, *gDjuiRoot=&root;
static struct DjuiBase *gDjuiHovered, *gDjuiCursorDownOn, *gInteractableFocus, *gInteractableBinding, *gInteractableMouseDown;
static OSContPad gInteractablePad,sLastInteractablePad;
static int sLastMouseButtons,mouse_window_buttons;
static bool sIgnoreAllInputsWhenBinding,sIgnoreInteractableUntilCursorReleased,gDjuiChatBoxFocus,gDjuiPanelPauseCreated;
static bool panel=true,touch=false,kbd=false; static float x,y; static int begun, held, clicked, back;
static void *gGlobalSoundSource;
static bool wiiu_keyboard_active(void){return kbd;}
static bool djui_panel_is_active(void){return panel;}
static bool controller_wiiu_touch_state(float *a,float *b){(void)a;(void)b;return touch;}
static bool djui_cursor_inside_base(struct DjuiBase *b){return x>=b->x && y>=b->y && x<=b->x+b->w && y<=b->y+b->h;}
static void djui_interactable_update_pad(void){}
static void djui_interactable_on_hover_end(struct DjuiBase *b){(void)b;}
static void djui_interactable_on_hover(struct DjuiBase *b){(void)b;}
static void djui_interactable_set_input_focus(struct DjuiBase *b){gInteractableFocus=b;}
static void djui_interactable_on_focus(struct DjuiBase *b){(void)b;}
static void djui_panel_back(void){++back;}
static void djui_panel_shutdown(void){}
static void djui_interactable_on_bind(struct DjuiBase *b){(void)b;}
static void djui_interactable_on_cursor_down_begin(struct DjuiBase *b,bool input){assert(b);assert(!input || !touch);++begun;gDjuiCursorDownOn=b;}
static void djui_interactable_on_cursor_down(struct DjuiBase *b){if(b) ++held;}
static void djui_interactable_on_cursor_down_end(struct DjuiBase *b){if(djui_cursor_inside_base(b)) ++clicked;gDjuiCursorDownOn=NULL;}
static void djui_bind_unbind(struct DjuiBase *b){(void)b;}
static void play_sound(int i,void *p){(void)i;(void)p;}
'''
checks = r'''
int main(void) {
 struct DjuiInteractable target={1};
 struct DjuiBase a={.visible=true,.enabled=true,.interactable=&target,.x=0,.y=0,.w=40,.h=40};
 struct DjuiBase b={.visible=true,.enabled=true,.interactable=&target,.x=50,.y=0,.w=40,.h=40};
 struct Child cb={&b,NULL},ca={&a,&cb};
 root.base=(struct DjuiBase){.visible=true,.enabled=true,.child=&ca,.w=100,.h=100};
 gDjuiHovered=&a; x=70;y=20;touch=true;djui_interactable_update();
 assert(gInteractableMouseDown==&b && begun==1);
 djui_interactable_update(); assert(held==1);
 touch=false;djui_interactable_update();assert(clicked==1 && !gInteractableMouseDown);
 // Sliding out before release does not click.
 x=20;touch=true;djui_interactable_update();x=70;touch=false;djui_interactable_update();assert(clicked==1);
 // Touches while the keyboard is open do not reach the menu.
 kbd=true; touch=true;djui_interactable_update();assert(begun==2);kbd=false;touch=false;
 // Controller back still works when the keyboard is closed.
 gInteractablePad.button=PAD_BUTTON_B;djui_interactable_update();assert(back==1);
}
'''
with tempfile.TemporaryDirectory() as d:
    c=Path(d)/'test.c'; b=Path(d)/'test'; c.write_text(pre+hit+update+checks)
    subprocess.run([os.environ.get('CC','cc'),'-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(b)],check=True)
    subprocess.run([str(b)],check=True)
print('Wii U UI touch tests passed')
