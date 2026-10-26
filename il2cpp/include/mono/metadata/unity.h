#include "metadata.h"
#include "mono/utils/mono-publib.h"

typedef struct _LivenessState LivenessState;
typedef void* gpointer;
typedef unsigned int guint;
typedef void *(*ReallocateArray) (void *ptr, int size, void *callback_userdata);
typedef void(*register_object_callback) (gpointer *arr, int size, void *callback_userdata);

MONO_BEGIN_DECLS

MONO_API MONO_RT_EXTERNAL_ONLY LivenessState * mono_unity_liveness_allocate_struct(MonoClass *filter, guint max_count, register_object_callback callback, void *callback_userdata, ReallocateArray reallocateArray);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_finalize(LivenessState *state);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_free_struct(LivenessState *state);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_calculation_from_root(MonoObject *root, LivenessState *state);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_liveness_calculation_from_statics(LivenessState *state);
MONO_API MONO_RT_EXTERNAL_ONLY int mono_class_get_userdata_offset();
MONO_API MONO_RT_EXTERNAL_ONLY void mono_class_set_userdata(MonoClass* klass, void* userdata);
MONO_API MONO_RT_EXTERNAL_ONLY bool mono_class_is_generic(MonoClass *klass);
MONO_API MONO_RT_EXTERNAL_ONLY bool mono_class_is_inflated(MonoClass *klass);
MONO_API MONO_RT_EXTERNAL_ONLY bool mono_class_is_blittable(MonoClass *klass);
typedef uint8_t (*android_network_up_state)(const char* ifName, uint8_t* is_up);
MONO_API MONO_RT_EXTERNAL_ONLY void mono_unity_set_android_network_up_state_func(android_network_up_state func);
MONO_END_DECLS