#include "metadata.h"
#include "mono/utils/mono-publib.h"

typedef struct _LivenessState LivenessState;
typedef void* gpointer;
typedef unsigned int guint;
typedef void *(*ReallocateArray) (void *ptr, int size, void *callback_userdata);
typedef void(*register_object_callback) (gpointer *arr, int size, void *callback_userdata);

MONO_BEGIN_DECLS

MONO_API MONO_RT_EXTERNAL_ONLY LivenessState * mono_unity_liveness_allocate_struct(MonoClass *filter, guint max_count, register_object_callback callback, void *callback_userdata, ReallocateArray reallocateArray);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_stop_gc_world();
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_finalize(LivenessState *state);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_start_gc_world();
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_free_struct(LivenessState *state);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_calculation_from_root(MonoObject *root, LivenessState *state);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_calculation_from_statics(LivenessState *state);

MONO_END_DECLS