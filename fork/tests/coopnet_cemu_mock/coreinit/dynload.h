#pragma once
typedef void* OSDynLoad_Module;
enum OSDynLoad_Error { OS_DYNLOAD_OK = 0, OS_DYNLOAD_ERROR = 1 };
enum OSDynLoad_ExportType { OS_DYNLOAD_EXPORT_FUNC = 0 };
extern "C" OSDynLoad_Error OSDynLoad_Acquire(const char*, OSDynLoad_Module*);
extern "C" OSDynLoad_Error OSDynLoad_FindExport(OSDynLoad_Module, OSDynLoad_ExportType, const char*, void**);
extern "C" void OSDynLoad_Release(OSDynLoad_Module);
