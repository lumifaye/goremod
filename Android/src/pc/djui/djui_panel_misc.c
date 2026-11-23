#include "djui.h"
#include "djui_panel.h"
#include "djui_panel_menu.h"
#include "djui_panel_confirm.h"
#include "game/save_file.h"
#include "pc/network/network.h"
#include "djui_panel_menu_options.h"
#include "djui_panel_options.h"
#include "djui_panel_language.h"
#include "djui_panel_info.h"
#include "pc/utils/misc.h"
#include "pc/configfile.h"
#include "game/hardcoded.h"
#if defined(_WIN32)
#include <windows.h>
#endif

static s32 sCompletionSlot;
static void djui_panel_misc_complete_yes(struct DjuiBase* caller) {
    if (gDjuiInMainMenu && gNetworkType == NT_NONE && save_file_complete_vanilla(sCompletionSlot))
        djui_popup_create("Vanilla 120-star save updated!", 1);
    else
        djui_popup_create("Only available in the main menu, offline.", 1);
    djui_panel_menu_back(caller);
}
static void djui_panel_misc_complete(struct DjuiBase* caller) {
    if (!gDjuiInMainMenu || gNetworkType != NT_NONE || configHostSaveSlot < 1 || configHostSaveSlot > NUM_SAVE_FILES) return;
    sCompletionSlot = configHostSaveSlot - 1;
    char message[256];
    snprintf(message, sizeof(message), "Add 120 vanilla stars and unlocks to host save %c? Existing progress is kept. Mod trophies are not included.", 'A' + sCompletionSlot);
    djui_panel_confirm_create(caller, "Complete Save", message, djui_panel_misc_complete_yes);
}

static void djui_panel_options_open_user_folder(UNUSED struct DjuiBase* caller) {
    open_folder(fs_get_write_path(""));
}

#ifdef DEVELOPMENT
void djui_panel_options_debug_create(struct DjuiBase* caller) {
    struct DjuiThreePanel* panel = djui_panel_menu_create(DLANG(MISC, DEBUG_TITLE), false);
    struct DjuiBase* body = djui_three_panel_get_body(panel);
    {
        djui_checkbox_create(body, DLANG(MISC, FIXED_COLLISIONS), (bool*)&gLevelValues.fixCollisionBugs, NULL);
        djui_checkbox_create(body, DLANG(MISC, LUA_PROFILER), &configLuaProfiler, NULL);
        djui_checkbox_create(body, DLANG(MISC, CTX_PROFILER), &configCtxProfiler, NULL);
        djui_checkbox_create(body, DLANG(MISC, DEBUG_PRINT), &configDebugPrint, NULL);
        djui_checkbox_create(body, DLANG(MISC, DEBUG_INFO), &configDebugInfo, NULL);
        djui_checkbox_create(body, DLANG(MISC, DEBUG_ERRORS), &configDebugError, NULL);

#ifndef HANDHELD
#if defined(_WIN32)
        djui_button_create(body, DLANG(OPTIONS, APPDATA), DJUI_BUTTON_STYLE_NORMAL, djui_panel_options_open_user_folder);
#elif __linux__ || __APPLE__ || __MACH__
        djui_button_create(body, DLANG(OPTIONS, USER_FOLDER), DJUI_BUTTON_STYLE_NORMAL, djui_panel_options_open_user_folder);
#endif
#endif
        djui_button_create(body, DLANG(MENU, BACK), DJUI_BUTTON_STYLE_BACK, djui_panel_menu_back);
    }

    djui_panel_add(caller, panel, NULL);
}
#endif

void djui_panel_misc_create(struct DjuiBase* caller) {
    struct DjuiThreePanel* panel = djui_panel_menu_create(DLANG(MISC, MISC_TITLE), false);
    struct DjuiBase* body = djui_three_panel_get_body(panel);
    {
        djui_checkbox_create(body, DLANG(DISPLAY, SHOW_PING), &configShowPing, NULL);
        djui_checkbox_create(body, DLANG(MISC, DISABLE_POPUPS), &configDisablePopups, NULL);
#ifndef DEVELOPMENT
        djui_checkbox_create(body, DLANG(MISC, LUA_PROFILER), &configLuaProfiler, NULL);
#endif

        struct DjuiButton* complete = djui_button_create(body, "Complete Host Save (120 Stars)", DJUI_BUTTON_STYLE_NORMAL, djui_panel_misc_complete);
        djui_base_set_enabled(&complete->base, gDjuiInMainMenu && gNetworkType == NT_NONE);
        djui_button_create(body, DLANG(MISC, LANGUAGE), DJUI_BUTTON_STYLE_NORMAL, djui_panel_language_create);
        djui_button_create(body, DLANG(MISC, MENU_OPTIONS), DJUI_BUTTON_STYLE_NORMAL, djui_panel_main_menu_create);
        djui_button_create(body, DLANG(MISC, INFORMATION), DJUI_BUTTON_STYLE_NORMAL, djui_panel_info_create);
#ifdef DEVELOPMENT
        djui_button_create(body, DLANG(MISC, DEBUG), DJUI_BUTTON_STYLE_NORMAL, djui_panel_options_debug_create);
#endif

#ifndef DEVELOPMENT
#ifndef HANDHELD
#if defined(_WIN32)
        djui_button_create(body, DLANG(OPTIONS, APPDATA), DJUI_BUTTON_STYLE_NORMAL, djui_panel_options_open_user_folder);
#elif __linux__ || __APPLE__ || __MACH__
        djui_button_create(body, DLANG(OPTIONS, USER_FOLDER), DJUI_BUTTON_STYLE_NORMAL, djui_panel_options_open_user_folder);
#endif
#endif
#endif
        djui_button_create(body, DLANG(MENU, BACK), DJUI_BUTTON_STYLE_BACK, djui_panel_menu_back);
    }

    djui_panel_add(caller, panel, NULL);
}
