#pragma once
typedef void *OSDynLoad_Module;
typedef int OSDynLoad_Error;
enum { OS_DYNLOAD_OK = 0, OS_DYNLOAD_EXPORT_FUNC = 0 };
OSDynLoad_Error OSDynLoad_Acquire(const char *, OSDynLoad_Module *);
OSDynLoad_Error OSDynLoad_FindExport(OSDynLoad_Module, int, const char *, void **);
void OSDynLoad_Release(OSDynLoad_Module);
