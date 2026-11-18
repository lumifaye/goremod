#pragma once
#include <stdint.h>
#include <vpad/input.h>
#include <coreinit/filesystem.h>
namespace nn { namespace swkbd {
enum class RegionType { USA }; enum class State { Hidden, Visible }; enum class PasswordMode { Clear, Hide };
struct CreateArg { void *workMemory = nullptr; FSClient *fsClient = nullptr; RegionType regionType = RegionType::USA; };
struct ConfigArg { bool disableNewLine = false; }; struct KeyboardArg { ConfigArg configArg; }; struct InputFormArg { const char16_t *initialText = nullptr; int32_t maxTextLength = -1; PasswordMode passwordMode = PasswordMode::Clear; }; struct AppearArg { KeyboardArg keyboardArg; InputFormArg inputFormArg; };
struct ControllerInfo { VPADStatus *vpad = nullptr; };
unsigned GetWorkMemorySize(unsigned); bool Create(const CreateArg &); void Destroy(); State GetStateInputForm(); bool AppearInputForm(const AppearArg &); bool DisappearInputForm(); void SetEnableOkButton(bool); void Calc(const ControllerInfo &); bool IsNeedCalcSubThreadFont(); void CalcSubThreadFont(); bool IsNeedCalcSubThreadPredict(); void CalcSubThreadPredict(); bool IsDecideOkButton(bool *); bool IsDecideCancelButton(bool *); const char16_t *GetInputFormString(); void DrawDRC();
} }
