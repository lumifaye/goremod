#pragma once
struct FSClient { int unused; };
#define FS_ERROR_FLAG_NONE 0
int FSAddClient(FSClient *, int);
int FSDelClient(FSClient *, int);
