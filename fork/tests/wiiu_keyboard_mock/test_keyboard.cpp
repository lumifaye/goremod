#include <cassert>
#include <cstring>
#include <string>
#include <nn/swkbd.h>
#include <coreinit/dynload.h>
#include "wiiu_keyboard.h"
static nn::swkbd::State state=nn::swkbd::State::Hidden;
static bool ok=false,cancelled=false,created=false, hidden=false; static int draws=0, forwarded=0;
static std::u16string native_text, initial;
static bool emulate=false; static int releases=0;
static void hle_create(void*,nn::swkbd::RegionType,uint32_t,FSClient*) { created=true; }
OSDynLoad_Error OSDynLoad_Acquire(const char *,OSDynLoad_Module *m) { *m=(void*)1; return 0; }
void OSDynLoad_Release(OSDynLoad_Module) { ++releases; }
OSDynLoad_Error OSDynLoad_FindExport(OSDynLoad_Module,int,const char *name,void **out) {
    *out=nullptr;
    if (!emulate && std::strstr(name,"SetVersion")) { *out=(void*)1; return 0; }
    if (!emulate) return -1;
    if (std::strstr(name,"SwkbdCreate")) *out=(void*)&hle_create;
    else if (std::strstr(name,"SwkbdAppearInputForm")) *out=(void*)&nn::swkbd::AppearInputForm;
    else if (std::strstr(name,"SwkbdDisappearInputForm")) *out=(void*)&nn::swkbd::DisappearInputForm;
    else if (std::strstr(name,"SwkbdGetStateInputForm")) *out=(void*)&nn::swkbd::GetStateInputForm;
    else if (std::strstr(name,"SwkbdCalc__")) *out=(void*)&nn::swkbd::Calc;
    else if (std::strstr(name,"SwkbdIsDecideOkButton")) *out=(void*)&nn::swkbd::IsDecideOkButton;
    else if (std::strstr(name,"SwkbdGetInputFormString")) *out=(void*)&nn::swkbd::GetInputFormString;
    return *out ? 0 : -1;
}
int FSAddClient(FSClient*,int){return 0;} int FSDelClient(FSClient*,int){return 0;}
namespace nn { namespace swkbd {
unsigned GetWorkMemorySize(unsigned){return 64;} bool Create(const CreateArg &a){assert(a.fsClient && a.workMemory);created=true;return true;} void Destroy(){created=false;}
State GetStateInputForm(){return state;} bool AppearInputForm(const AppearArg &a){ assert(a.keyboardArg.configArg.disableNewLine);initial=a.inputFormArg.initialText; hidden=a.inputFormArg.passwordMode==PasswordMode::Hide; state=State::Visible;return true;} bool DisappearInputForm(){state=State::Hidden;return true;} void SetEnableOkButton(bool b){assert(b);} void Calc(const ControllerInfo &c){if(c.vpad->tpNormal.touched) ++forwarded;}
bool IsNeedCalcSubThreadFont(){return false;} void CalcSubThreadFont(){} bool IsNeedCalcSubThreadPredict(){return false;} void CalcSubThreadPredict(){} bool IsDecideOkButton(bool*){return ok;} bool IsDecideCancelButton(bool*){return cancelled;} const char16_t *GetInputFormString(){return native_text.c_str();} void DrawDRC(){++draws;}
} }
int main(){
 VPADStatus pad{}; char out[64];
 assert(wiiu_keyboard_open("hello \xc3\xa9 \xf0\x9f\x98\x80",64,true));assert(created && hidden); assert(initial==u"hello \u00e9 \U0001f600");
 pad.tpNormal.touched=1; assert(wiiu_keyboard_input(&pad)); assert(!forwarded);wiiu_keyboard_draw_drc();assert(draws==1);
 pad.tpNormal.touched=0;wiiu_keyboard_input(&pad);pad.tpNormal.touched=1;native_text=u"\u00e9\U0001f600!";ok=true;wiiu_keyboard_input(&pad);
 assert(wiiu_keyboard_take_result(out,sizeof(out))==1);assert(std::string(out)=="\xc3\xa9\xf0\x9f\x98\x80!");assert(!wiiu_keyboard_active());ok=false;
 assert(wiiu_keyboard_open("",4,false));pad.tpNormal.touched=0;wiiu_keyboard_input(&pad);native_text=u"A\u00e9Z";ok=true;wiiu_keyboard_input(&pad);char shortbuf[3];assert(wiiu_keyboard_take_result(shortbuf,sizeof(shortbuf))==1);assert(std::string(shortbuf)=="A");ok=false;
 assert(wiiu_keyboard_open("original",20,false));wiiu_keyboard_input(&pad);cancelled=true;wiiu_keyboard_input(&pad);assert(wiiu_keyboard_take_result(out,sizeof(out))==-1);cancelled=false;
 assert(wiiu_keyboard_open("x",20,false)); wiiu_keyboard_cancel();assert(!wiiu_keyboard_active() && !wiiu_keyboard_take_result(out,sizeof(out)));
 wiiu_keyboard_shutdown(); assert(!created);
 emulate=true; created=false; int before=draws;
 assert(wiiu_keyboard_open("emulated",64,false)); assert(created); wiiu_keyboard_draw_drc(); assert(draws==before);
 pad.tpNormal.touched=0; pad.hold=0; pad.trigger=0; wiiu_keyboard_input(&pad); native_text=u"Cemu"; ok=true; wiiu_keyboard_input(&pad);
 assert(wiiu_keyboard_take_result(out,sizeof(out))==1 && std::string(out)=="Cemu"); ok=false;
 assert(wiiu_keyboard_open("cancel",64,false)); wiiu_keyboard_input(&pad); pad.trigger=VPAD_BUTTON_MINUS; wiiu_keyboard_input(&pad); assert(wiiu_keyboard_take_result(out,sizeof(out))==-1); pad.trigger=0;
 wiiu_keyboard_shutdown(); assert(releases==2);
}
