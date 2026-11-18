#ifdef TARGET_WII_U
#include "wiiu_keyboard.h"
#include <vpad/input.h>
#include <nn/swkbd.h>
#include <coreinit/filesystem.h>
#include <coreinit/dynload.h>
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <string>

namespace {
bool initialized = false, showing = false, waiting_release = false;
FSClient *client = nullptr;
void *work = nullptr;
std::u16string initial_text;
std::string result;
int result_status = 0;
// Cemu's built-in swkbd HLE exports only a subset of the real RPL. The WUT
// wrapper assumes every export exists, so use the available exports directly
// when that subset is detected; Cemu draws its own keyboard overlay.
bool hle = false;
OSDynLoad_Module hle_module = nullptr;
void (*hle_create)(void *, nn::swkbd::RegionType, uint32_t, FSClient *) = nullptr;
bool (*hle_appear)(const nn::swkbd::AppearArg &) = nullptr;
bool (*hle_disappear)() = nullptr;
nn::swkbd::State (*hle_state)() = nullptr;
void (*hle_calc)(const nn::swkbd::ControllerInfo &) = nullptr;
bool (*hle_ok)(bool *) = nullptr;
const char16_t *(*hle_text)() = nullptr;
void (*hle_font)() = nullptr, (*hle_predict)() = nullptr;
bool (*hle_need_font)() = nullptr, (*hle_need_predict)() = nullptr;

template<typename T> bool find_export(OSDynLoad_Module module, const char *name, T &function) {
    void *addr = nullptr;
    if (OSDynLoad_FindExport(module, OS_DYNLOAD_EXPORT_FUNC, name, &addr) != OS_DYNLOAD_OK || !addr) return false;
    function = reinterpret_cast<T>(addr);
    return true;
}
static nn::swkbd::State state() { return hle ? hle_state() : nn::swkbd::GetStateInputForm(); }
static bool appear(const nn::swkbd::AppearArg &a) { return hle ? hle_appear(a) : nn::swkbd::AppearInputForm(a); }
static void disappear() { if (hle) hle_disappear(); else nn::swkbd::DisappearInputForm(); }
static void calc(const nn::swkbd::ControllerInfo &i) { if (hle) hle_calc(i); else nn::swkbd::Calc(i); }
static bool ok() { return hle ? hle_ok(nullptr) : nn::swkbd::IsDecideOkButton(nullptr); }
static const char16_t *text() { return hle ? hle_text() : nn::swkbd::GetInputFormString(); }
static void auxiliary() {
    if (hle) {
        if (hle_need_font && hle_font && hle_need_font()) hle_font();
        if (hle_need_predict && hle_predict && hle_need_predict()) hle_predict();
    } else {
        if (nn::swkbd::IsNeedCalcSubThreadFont()) nn::swkbd::CalcSubThreadFont();
        if (nn::swkbd::IsNeedCalcSubThreadPredict()) nn::swkbd::CalcSubThreadPredict();
    }
}


// Convert UTF-8 without relying on the system locale. Invalid sequences are
// replaced rather than letting an incomplete character into the result.
std::u16string from_utf8(const char *s) {
    std::u16string out;
    if (!s) return out;
    const auto *p = reinterpret_cast<const unsigned char *>(s);
    while (*p) {
        unsigned c = *p++, n = 0, min = 0;
        if (c < 0x80) { out.push_back((char16_t)c); continue; }
        if ((c & 0xe0) == 0xc0) { c &= 0x1f; n = 1; min = 0x80; }
        else if ((c & 0xf0) == 0xe0) { c &= 0x0f; n = 2; min = 0x800; }
        else if ((c & 0xf8) == 0xf0) { c &= 7; n = 3; min = 0x10000; }
        else { out.push_back(u'\ufffd'); continue; }
        const unsigned char *q = p;
        unsigned i = 0;
        for (; i < n && q[i] && (q[i] & 0xc0) == 0x80; ++i) c = (c << 6) | (q[i] & 0x3f);
        if (i != n || c < min || c > 0x10ffff || (c >= 0xd800 && c <= 0xdfff)) {
            out.push_back(u'\ufffd'); continue;
        }
        p += n;
        if (c < 0x10000) out.push_back((char16_t)c);
        else { c -= 0x10000; out.push_back((char16_t)(0xd800 + (c >> 10))); out.push_back((char16_t)(0xdc00 + (c & 1023))); }
    }
    return out;
}
std::string to_utf8(const char16_t *p) {
    std::string out;
    if (!p) return out;
    while (*p) {
        unsigned c = *p++;
        if (c >= 0xd800 && c <= 0xdbff && *p >= 0xdc00 && *p <= 0xdfff) c = 0x10000 + ((c - 0xd800) << 10) + (*p++ - 0xdc00);
        else if (c >= 0xd800 && c <= 0xdfff) c = 0xfffd;
        if (c < 0x80) out.push_back((char)c);
        else if (c < 0x800) { out.push_back((char)(0xc0 | (c >> 6))); out.push_back((char)(0x80 | (c & 63))); }
        else if (c < 0x10000) { out.push_back((char)(0xe0 | (c >> 12))); out.push_back((char)(0x80 | ((c >> 6) & 63))); out.push_back((char)(0x80 | (c & 63))); }
        else { out.push_back((char)(0xf0 | (c >> 18))); out.push_back((char)(0x80 | ((c >> 12) & 63))); out.push_back((char)(0x80 | ((c >> 6) & 63))); out.push_back((char)(0x80 | (c & 63))); }
    }
    return out;
}
bool init() {
    if (initialized) return true;
    client = (FSClient *)std::malloc(sizeof(FSClient));
    work = std::malloc(nn::swkbd::GetWorkMemorySize(0));
    if (!client || !work) { std::free(client); std::free(work); client = nullptr; work = nullptr; return false; }
    if (FSAddClient(client, FS_ERROR_FLAG_NONE) < 0) { std::free(client); std::free(work); client = nullptr; work = nullptr; return false; }
    OSDynLoad_Module probe = nullptr;
    if (OSDynLoad_Acquire("swkbd.rpl", &probe) != OS_DYNLOAD_OK) {
        FSDelClient(client, FS_ERROR_FLAG_NONE); std::free(client); std::free(work); client = nullptr; work = nullptr; return false;
    }
    void *version = nullptr;
    if (OSDynLoad_FindExport(probe, OS_DYNLOAD_EXPORT_FUNC, "SwkbdSetVersion__3RplFi", &version) != OS_DYNLOAD_OK || !version) {
        bool complete =
            find_export(probe, "SwkbdCreate__3RplFPUcQ3_2nn5swkbd10RegionTypeUiP8FSClient", hle_create) &&
            find_export(probe, "SwkbdAppearInputForm__3RplFRCQ3_2nn5swkbd9AppearArg", hle_appear) &&
            find_export(probe, "SwkbdDisappearInputForm__3RplFv", hle_disappear) &&
            find_export(probe, "SwkbdGetStateInputForm__3RplFv", hle_state) &&
            find_export(probe, "SwkbdCalc__3RplFRCQ3_2nn5swkbd14ControllerInfo", hle_calc) &&
            find_export(probe, "SwkbdIsDecideOkButton__3RplFPb", hle_ok) &&
            find_export(probe, "SwkbdGetInputFormString__3RplFv", hle_text);
        if (!complete) {
            OSDynLoad_Release(probe); FSDelClient(client, FS_ERROR_FLAG_NONE);
            std::free(client); std::free(work); client = nullptr; work = nullptr; return false;
        }
        find_export(probe, "SwkbdIsNeedCalcSubThreadFont__3RplFv", hle_need_font);
        find_export(probe, "SwkbdCalcSubThreadFont__3RplFv", hle_font);
        find_export(probe, "SwkbdIsNeedCalcSubThreadPredict__3RplFv", hle_need_predict);
        find_export(probe, "SwkbdCalcSubThreadPredict__3RplFv", hle_predict);
        hle = true; hle_module = probe;
        hle_create(work, nn::swkbd::RegionType::USA, 0, client);
        initialized = true;
        return true;
    }
    OSDynLoad_Release(probe);
    nn::swkbd::CreateArg args;
    args.workMemory = work;
    args.fsClient = client;
    args.regionType = nn::swkbd::RegionType::USA;
    if (!nn::swkbd::Create(args)) {
        FSDelClient(client, FS_ERROR_FLAG_NONE); std::free(client); std::free(work); client = nullptr; work = nullptr; return false;
    }
    initialized = true;
    return true;
}
}

extern "C" bool wiiu_keyboard_open(const char *initial, size_t max_bytes, bool password) {
    if (!max_bytes || !init() || state() != nn::swkbd::State::Hidden) return false;
    initial_text = from_utf8(initial);
    nn::swkbd::AppearArg args;
    args.keyboardArg.configArg.disableNewLine = true;
    args.inputFormArg.initialText = initial_text.c_str();
    args.inputFormArg.maxTextLength = (int32_t)std::min(max_bytes - 1, (size_t)4095);
    args.inputFormArg.passwordMode = password ? nn::swkbd::PasswordMode::Hide : nn::swkbd::PasswordMode::Clear;
    result.clear(); result_status = 0;
    if (!appear(args)) return false;
    showing = true; waiting_release = true;
    if (!hle) nn::swkbd::SetEnableOkButton(true);
    return true;
}
extern "C" bool wiiu_keyboard_active(void) {
    return initialized && (showing || state() != nn::swkbd::State::Hidden);
}
extern "C" bool wiiu_keyboard_input(const VPADStatus *status) {
    if (!wiiu_keyboard_active()) return false;
    VPADStatus clean = *status;
    if (waiting_release) {
        if (!status->tpNormal.touched && !status->hold) waiting_release = false;
        std::memset(&clean, 0, sizeof(clean));
    }
    nn::swkbd::ControllerInfo info;
    info.vpad = &clean;
    calc(info);
    auxiliary();
    if (showing && !waiting_release && ok()) {
        result = to_utf8(text()); result_status = 1;
        showing = false; disappear();
    } else if (showing && !waiting_release && (hle ? (status->trigger & VPAD_BUTTON_MINUS) != 0 : nn::swkbd::IsDecideCancelButton(nullptr))) {
        result.clear(); result_status = -1;
        showing = false; disappear();
    }
    return true;
}
extern "C" int wiiu_keyboard_take_result(char *out, size_t capacity) {
    int status = result_status;
    if (!status) return 0;
    if (out && capacity) {
        size_t n = std::min(result.size(), capacity - 1);
        // Do not leave an incomplete UTF-8 sequence at the end of the buffer.
        if (n < result.size()) while (n && ((unsigned char)result[n] & 0xc0) == 0x80) --n;
        std::memcpy(out, result.data(), n); out[n] = 0;
    }
    result.clear(); result_status = 0;
    return status;
}
extern "C" void wiiu_keyboard_cancel(void) {
    result_status = 0; result.clear();
    if (initialized && showing) { showing = false; disappear(); }
}
extern "C" void wiiu_keyboard_draw_drc(void) {
    if (!hle && wiiu_keyboard_active()) nn::swkbd::DrawDRC();
}
extern "C" void wiiu_keyboard_shutdown(void) {
    if (!initialized) return;
    if (hle) { OSDynLoad_Release(hle_module); hle_module = nullptr; hle = false; }
    else nn::swkbd::Destroy();
    initialized = showing = false;
    FSDelClient(client, FS_ERROR_FLAG_NONE);
    std::free(client); std::free(work); client = nullptr; work = nullptr;
}
#endif
