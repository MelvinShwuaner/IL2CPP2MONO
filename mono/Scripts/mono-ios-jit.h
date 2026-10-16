#ifndef __MONO_IOS_JIT_H__
#define __MONO_IOS_JIT_H__

#include <mono/utils/mono-publib.h>

MONO_BEGIN_DECLS

MONO_API int mono_ios_jit_prepare (size_t capacity);
MONO_API mono_bool mono_ios_jit_contains_code (const void *address, size_t size);

void *mono_ios_jit_alloc (size_t size);
void mono_ios_jit_free (void *address, size_t size);
void *mono_ios_jit_write_address (void *address);
void mono_ios_jit_write_memory (void *address, const void *source, size_t size);
void mono_ios_jit_set_memory (void *address, int value, size_t size);
void mono_ios_jit_cleanup (void);

MONO_END_DECLS

#endif
