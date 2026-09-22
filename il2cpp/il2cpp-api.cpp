#pragma once
/*#include "il2cpp-api.h"
#include "il2cpp-object-internals.h"
#include "il2cpp-runtime-stats.h"

#include "gc/WriteBarrier.h"
#include "os/StackTrace.h"
#include "os/Image.h"
#include "vm/AndroidRuntime.h"
#include "vm/Array.h"
#include "vm/Assembly.h"
#include "vm/Class.h"
#include "vm/Domain.h"
#include "vm/Exception.h"
#include "vm/Field.h"
#include "vm/Image.h"
#include "vm/InternalCalls.h"
#include "vm/Liveness.h"
#include "vm/MemoryInformation.h"
#include "vm/Method.h"
#include "vm/Monitor.h"
#include "vm/Object.h"
#include "vm/Path.h"
#include "vm/PlatformInvoke.h"
#include "vm/Profiler.h"
#include "vm/Property.h"
#include "vm/Reflection.h"
#include "vm/Runtime.h"
#include "vm/StackTrace.h"
#include "vm/String.h"
#include "vm/Thread.h"
#include "vm/Type.h"
#include "utils/Exception.h"
#include "utils/Logging.h"
#include "utils/Memory.h"
#include "utils/MemoryPool.h"
#include "utils/StringUtils.h"
#include "utils/Environment.h"
#include "vm-utils/Debugger.h"
#include "vm-utils/NativeSymbol.h"

#include "gc/GarbageCollector.h"
#include "gc/GCHandle.h"
#include "gc/WriteBarrierValidation.h"
*/
#include <locale.h>
#include <fstream>
#include <jni.h>
#include <string>
#include <android/log.h>

#include "il2cpp-api-types.h"
#include "main.cpp"
#include "mono/metadata/mono-gc.h"
#include "mono/metadata/unity-liveness.h"
typedef size_t il2cpp_array_size_t;
#include <mono/jit/jit.h>
#include <mono/metadata/exception.h>
#include <unordered_map>
#include <string>
#include <cstring>
#include <unistd.h>
//used for debugging when necessary
#define LOGCALL() //__android_log_print(ANDROID_LOG_DEBUG, "IL2CPPAPI", "%s", __FUNCTION__);
#define LOGCALL2() __android_log_print(ANDROID_LOG_DEBUG, "IL2CPPAPI", "%s", __FUNCTION__);
#define LOGMSG(...) __android_log_print(ANDROID_LOG_DEBUG, "IL2CPPAPI", "%s %s", __FUNCTION__, __VA_ARGS__);
#define LOGMSG2(...) __android_log_print(ANDROID_LOG_DEBUG, "IL2CPPAPI", __VA_ARGS__);

JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void* reserved) {
    __android_log_print(ANDROID_LOG_INFO, "libil2cpp", "JNI_Load");
    JVM = vm;
    JNIEnv* env;
    if (vm->GetEnv((void**)&env, JNI_VERSION_1_6) != JNI_OK) {
        return JNI_ERR;
    }
    if (Init(env) == 0) {
      //  __android_log_print(ANDROID_LOG_INFO, "libil2cpp", "JNI_Load failed to initialize!");
    }
    return JNI_VERSION_1_6;
}
extern "C" {
int il2cpp_init(const char* domain_name)
{
    // Use environment's default locale
    setlocale(LC_ALL, "");
    LOGCALL();
    return InitMono(domain_name);
}

int il2cpp_init_utf16(const Il2CppChar* domain_name)
{
    return 0;
    //return il2cpp_init(il2cpp::utils::StringUtils::Utf16ToUtf8(domain_name).c_str());
}
bool il2cpp_method_is_instance(const MethodInfo* method)
{
    //LOGCALL();
    MonoMethod* m = method->originalMethod;
    uint32_t flags = mono_method_get_flags(m, nullptr);
    return (flags & METHOD_ATTRIBUTE_STATIC) == 0; // instance methods lack the static flag
}

bool il2cpp_class_has_attribute(Il2CppClass* klass, Il2CppClass* attr_class)
{
    //LOGCALL();
    

    MonoClass* attrKlass = attr_class->original;
    MonoCustomAttrInfo* attrInfo = mono_custom_attrs_from_class(klass->original);
    if (!attrInfo) return false;
    bool has = mono_custom_attrs_has_attr(attrInfo, attrKlass);
    mono_custom_attrs_free(attrInfo);
    return has;
}

void il2cpp_class_set_userdata(Il2CppClass* klass, void* userdata)
{
    LOGCALL();
   klass->unity_user_data = userdata;
}
void il2cpp_add_internal_call(const char* name, Il2CppMethodPointer method)
{
    LOGCALL();
    if (!IsMonoReady) {
        ICallQueue[name] = method;
    }
    else {
        AddInternalCall(name, method);
    }
}

Il2CppMethodPointer il2cpp_resolve_icall(const char* name)
{
    LOGCALL();
    return ResolveICall(name);
}

// ---------------- domain / assembly ----------------

Il2CppDomain* il2cpp_domain_get()
{
    //LOGCALL();
    return (Il2CppDomain*)mono_domain_get();
}

const Il2CppAssembly* il2cpp_domain_assembly_open(Il2CppDomain* domain, const char* name)
{
    LOGCALL();
    //MonoImageOpenStatus status;
    std::string path = std::format("{}/{}", DllPath, name);
    MonoAssembly* asm_ = mono_domain_assembly_open((MonoDomain*)domain, path.c_str());
    if (!asm_) {
        LOGW("missing assembly %s", path.c_str());
    }
    return reinterpret_cast<Il2CppAssembly *>(asm_);
}

const Il2CppAssembly** il2cpp_domain_get_assemblies(const Il2CppDomain* domain, size_t* size)
{
    LOGCALL();
    // mono_domain_get_assemblies (internal API) or mono_assembly_foreach — use foreach + static cache
    static std::vector<const Il2CppAssembly*> s_assemblies;
    s_assemblies.clear();

    mono_assembly_foreach([](void* asm_, void* userdata) {
        auto* list = static_cast<std::vector<const Il2CppAssembly*>*>(userdata);
        list->push_back((const Il2CppAssembly*)asm_);
    }, &s_assemblies);

    *size = s_assemblies.size();
    return s_assemblies.empty() ? nullptr : s_assemblies.data();
}

const Il2CppImage* il2cpp_assembly_get_image(const Il2CppAssembly* assembly)
{
    LOGCALL();
    return (const Il2CppImage*)mono_assembly_get_image((MonoAssembly*)assembly);
}

const Il2CppImage* il2cpp_get_corlib()
{
    LOGCALL();
    return (const Il2CppImage*)mono_get_corlib();
}

// ---------------- class ----------------

Il2CppClass* il2cpp_class_from_name(const Il2CppImage* image, const char* namespaze, const char* name)
{
    //LOGCALL();
    MonoClass* k = mono_class_from_name((MonoImage*)image, namespaze, name);
    if (!k) {
        //__android_log_print(ANDROID_LOG_WARN, "il2cpp_shim", "class not found: %s.%s", namespaze, name);
    }
    return WrapClass(k);
}

Il2CppClass* il2cpp_class_from_il2cpp_type(const Il2CppType* type)
{
    LOGCALL();
    return WrapClass(mono_class_from_mono_type((MonoType*)type));
}

Il2CppClass* il2cpp_class_from_type(const Il2CppType* type)
{
   // LOGCALL();
    return WrapClass(mono_class_from_mono_type((MonoType*)type));
}

const MethodInfo* il2cpp_class_get_method_from_name(Il2CppClass* klass, const char* name, int argsCount)
{
    LOGCALL();
    
    return WrapMethod(mono_class_get_method_from_name(klass->original, name, argsCount));
}

FieldInfo* il2cpp_class_get_field_from_name(Il2CppClass* klass, const char* name)
{
   // LOGCALL();
    return (FieldInfo*)mono_class_get_field_from_name(klass->original, name);
}

const MethodInfo* il2cpp_class_get_methods(Il2CppClass* klass, void** iter)
{
    return WrapMethod(mono_class_get_methods(klass->original, iter));
}

FieldInfo* il2cpp_class_get_fields(Il2CppClass* klass, void** iter)
{
   // LOGCALL();
    return (FieldInfo*)mono_class_get_fields(klass->original, iter);
}

Il2CppClass* il2cpp_class_get_parent(Il2CppClass* klass)
{
    //LOGCALL();
    return WrapClass(mono_class_get_parent(klass->original));
}

bool il2cpp_class_is_subclass_of(Il2CppClass* klass, Il2CppClass* klassc, bool check_interfaces)
{
    //LOGCALL();
    return mono_class_is_subclass_of(klass->original, klassc->original, check_interfaces);
}

bool il2cpp_class_is_assignable_from(Il2CppClass* klass, Il2CppClass* oklass)
{
    LOGCALL();
    return mono_class_is_assignable_from(klass->original, oklass->original);
}

const char* il2cpp_class_get_name(Il2CppClass* klass)
{
    //LOGCALL();
    return klass->name;
}

const char* il2cpp_class_get_namespace(Il2CppClass* klass)
{
    //LOGCALL();
    return mono_class_get_namespace(klass->original);
}

const Il2CppType* il2cpp_class_get_type(Il2CppClass* klass)
{
    LOGCALL();
    return (const Il2CppType*)mono_class_get_type(klass->original);
}

int32_t il2cpp_class_instance_size(Il2CppClass* klass)
{
    LOGCALL();
    return mono_class_instance_size(klass->original);
}

bool il2cpp_class_is_valuetype(const Il2CppClass* klass)
{
    LOGCALL();
    return mono_class_is_valuetype(klass->original);
}

const Il2CppImage* il2cpp_class_get_image(Il2CppClass* klass)
{
    LOGCALL();
    return (const Il2CppImage*)mono_class_get_image(klass->original);
}

Il2CppClass* il2cpp_array_class_get(Il2CppClass* element_class, uint32_t rank)
{
    LOGCALL();
    return WrapClass(mono_array_class_get(element_class->original, rank));
}

int il2cpp_class_array_element_size(const Il2CppClass* klass)
{
    LOGCALL();
    return mono_class_array_element_size(klass->original);
}

// ---------------- object / field ----------------

Il2CppObject* il2cpp_object_new(const Il2CppClass* klass)
{
    LOGCALL();
    return (Il2CppObject*)mono_object_new(mono_domain_get(), klass->original);
}

Il2CppClass* il2cpp_object_get_class(Il2CppObject* obj)
{
    LOGCALL();
    return WrapClass(mono_object_get_class((MonoObject*)obj));
}

const MethodInfo* il2cpp_object_get_virtual_method(Il2CppObject* obj, const MethodInfo* method)
{
    LOGCALL();
    return WrapMethod(mono_object_get_virtual_method((MonoObject*)obj, method->originalMethod));
}

void* il2cpp_object_unbox(Il2CppObject* obj)
{
    LOGCALL();
    return mono_object_unbox((MonoObject*)obj);
}

Il2CppObject* il2cpp_value_box(Il2CppClass* klass, void* data)
{
    LOGCALL();
    return (Il2CppObject*)mono_value_box(Domain, klass->original, data);
}

void il2cpp_field_get_value(Il2CppObject* obj, FieldInfo* field, void* value)
{
    LOGCALL();
    mono_field_get_value((MonoObject*)obj, (MonoClassField*)field, value);
}

void il2cpp_field_set_value(Il2CppObject* obj, FieldInfo* field, void* value)
{
    LOGCALL();
    mono_field_set_value((MonoObject*)obj, (MonoClassField*)field, value);
}

void il2cpp_field_static_get_value(FieldInfo* field, void* value)
{
    LOGCALL();
    MonoClass* klass = mono_field_get_parent((MonoClassField*)field);
    MonoVTable* vtable = mono_class_vtable(mono_domain_get(), klass);
    mono_field_static_get_value(vtable, (MonoClassField*)field, value);
}

void il2cpp_field_static_set_value(FieldInfo* field, void* value)
{
    LOGCALL();
    MonoClass* klass = mono_field_get_parent((MonoClassField*)field);
    MonoVTable* vtable = mono_class_vtable(mono_domain_get(), klass);
    mono_field_static_set_value(vtable, (MonoClassField*)field, value);
}

// ---------------- runtime invoke ----------------

Il2CppObject* il2cpp_runtime_invoke(const MethodInfo* method, void* obj, void** params, Il2CppException** exc)
{
    //LOGMSG2("%s.%s", method->klass->name, method->name);
    MonoObject* monoExc = nullptr;
    MonoObject* result = mono_runtime_invoke(method->originalMethod, obj, params, &monoExc);
    if (exc) *exc = (Il2CppException*)monoExc;
    return (Il2CppObject*)result;
}

// Converts boxed Il2CppObject* args into a native void** layout Mono expects,
// unboxing value types where the parameter signature calls for it.
Il2CppObject* il2cpp_runtime_invoke_convert_args(const MethodInfo* method, void* obj,
                                                   Il2CppObject** params, int paramCount,
                                                   Il2CppException** exc)
{
    LOGCALL();
    MonoMethodSignature* sig = mono_method_signature(method->originalMethod);
    void* iter = nullptr;
    std::vector<void*> nativeArgs(paramCount);

    for (int i = 0; i < paramCount; i++) {
        MonoType* paramType = mono_signature_get_params(sig, &iter);
        auto* argObj = (MonoObject*)params[i];

        if (argObj && mono_type_is_struct(paramType)) {
            // Value type — unbox to get a pointer to the raw data
            nativeArgs[i] = mono_object_unbox(argObj);
        } else {
            // Reference type — pass the object pointer itself
            nativeArgs[i] = argObj;
        }
    }

    MonoObject* monoExc = nullptr;
    MonoObject* result = mono_runtime_invoke(method->originalMethod, obj, nativeArgs.data(), &monoExc);
    if (exc) *exc = (Il2CppException*)monoExc;
    return (Il2CppObject*)result;
}

void il2cpp_runtime_class_init(Il2CppClass* klass)
{
    LOGCALL();
    mono_runtime_class_init(mono_class_vtable(mono_domain_get(), klass->original));
}

void il2cpp_runtime_object_init(Il2CppObject* obj)
{
    LOGCALL();
    mono_runtime_object_init((MonoObject*)obj);
}

// ---------------- string / array ----------------

Il2CppString* il2cpp_string_new(const char* str)
{
    LOGCALL();
    return (Il2CppString*)mono_string_new(mono_domain_get(), str);
}

Il2CppString* il2cpp_string_new_wrapper(const char* str)
{
    LOGCALL();
    return (Il2CppString*)mono_string_new_wrapper(str);
}

Il2CppString* il2cpp_string_new_utf16(const Il2CppChar* text, int32_t len)
{
    LOGCALL();
    return (Il2CppString*)mono_string_new_utf16(mono_domain_get(), (const uint16_t*)text, len);
}

Il2CppString* il2cpp_string_new_len(const char* str, uint32_t length)
{
    LOGCALL();
    return (Il2CppString*)mono_string_new_len(mono_domain_get(), str, length);
}

int32_t il2cpp_string_length(Il2CppString* str)
{
   // LOGCALL();
    return mono_string_length((MonoString*)str);
}

Il2CppChar* il2cpp_string_chars(Il2CppString* str)
{
    //LOGCALL();
    return (Il2CppChar*)mono_string_chars((MonoString*)str);
}

Il2CppArray* il2cpp_array_new(Il2CppClass* elementTypeInfo, il2cpp_array_size_t length)
{
    LOGCALL();
    return (Il2CppArray*)mono_array_new(mono_domain_get(), elementTypeInfo->original, length);
}

uint32_t il2cpp_array_length(Il2CppArray* array)
{
    LOGCALL();
    return (uint32_t)mono_array_length((MonoArray*)array);
}

uint32_t il2cpp_array_get_byte_length(Il2CppArray* array)
{
    LOGCALL();
    MonoClass* elemClass = mono_object_get_class((MonoObject*)array);
    return (uint32_t)(mono_array_length((MonoArray*)array) * mono_class_array_element_size(elemClass));
}

int il2cpp_array_element_size(const Il2CppClass* klass)
{
    LOGCALL();
    return mono_array_element_size(klass->original);
}

// ---------------- thread ----------------

Il2CppThread* il2cpp_thread_current()
{
    LOGCALL();
    if (mono_domain_get() == nullptr) {
        return NULL;
    }
    auto* value = (Il2CppThread*)mono_thread_current();
    return value;
}

Il2CppThread* il2cpp_thread_attach(Il2CppDomain* domain)
{
    LOGCALL();
    return (Il2CppThread*)mono_thread_attach((MonoDomain*)domain);
}

void il2cpp_thread_detach(Il2CppThread* thread)
{
    LOGCALL();
    mono_thread_detach((MonoThread*)thread);
}

// ---------------- gchandle ----------------

uint32_t il2cpp_gchandle_new(Il2CppObject* obj, bool pinned)
{
    LOGCALL();
    return mono_gchandle_new((MonoObject*)obj, pinned);
}

uint32_t il2cpp_gchandle_new_weakref(Il2CppObject* obj, bool track_resurrection)
{
    LOGCALL();
    return mono_gchandle_new_weakref((MonoObject*)obj, track_resurrection);
}

Il2CppObject* il2cpp_gchandle_get_target(uint32_t gchandle)
{
    LOGCALL();
    return (Il2CppObject*)mono_gchandle_get_target(gchandle);
}

void il2cpp_gchandle_free(uint32_t gchandle)
{
    LOGCALL();
    mono_gchandle_free(gchandle);
}

// ---------------- exception ----------------

void il2cpp_raise_exception(Il2CppException* exc)
{
    LOGCALL();
    mono_raise_exception((MonoException*)exc);
}

Il2CppException* il2cpp_exception_from_name_msg(const Il2CppImage* image, const char* name_space, const char* name, const char* msg)
{
    LOGCALL();
    return (Il2CppException*)mono_exception_from_name_msg((MonoImage*)image, name_space, name, msg);
}

Il2CppException* il2cpp_get_exception_argument_null(const char* arg)
{
    LOGCALL();
    return (Il2CppException*)mono_get_exception_argument_null(arg);
}

void il2cpp_format_exception(const Il2CppException* ex, char* message, int message_size)
{
    LOGCALL();
    MonoObject* exc = nullptr;
    MonoString* str = mono_object_to_string((MonoObject*)ex, &exc);
    if (!str) {
        strncpy(message, "<unformattable exception>", message_size);
        return;
    }
    char* utf8 = mono_string_to_utf8(str);
    strncpy(message, utf8, message_size);
    message[message_size - 1] = '\0';
    mono_free(utf8);
}

// ---------------- monitor ----------------

void il2cpp_monitor_enter(Il2CppObject* obj)
{
    LOGCALL();
    mono_monitor_enter((MonoObject*)obj);
}

bool il2cpp_monitor_try_enter(Il2CppObject* obj, uint32_t timeout)
{
    LOGCALL();
    return mono_monitor_try_enter((MonoObject*)obj, timeout);
}

void il2cpp_monitor_exit(Il2CppObject* obj)
{
    LOGCALL();
    mono_monitor_exit((MonoObject*)obj);
}

void il2cpp_monitor_pulse(Il2CppObject* obj)
{
    LOGCALL();
    MonoClass* monitorClass = GetMonitorClass();
    MonoMethod* pulseMethod = mono_class_get_method_from_name(monitorClass, "Pulse", 1);
    void* args[1] = { obj };
    MonoObject* exc = nullptr;
    mono_runtime_invoke(pulseMethod, nullptr, args, &exc);
}

void il2cpp_monitor_wait(Il2CppObject* obj)
{
    LOGCALL();
    MonoClass* monitorClass = GetMonitorClass();
    MonoMethod* waitMethod = mono_class_get_method_from_name(monitorClass, "Wait", 1);
    void* args[1] = { obj };
    MonoObject* exc = nullptr;
    mono_runtime_invoke(waitMethod, nullptr, args, &exc);
}

void il2cpp_shutdown()
{
    LOGCALL();
    mono_runtime_set_shutting_down();
}

void il2cpp_set_config_dir(const char *config_path)
{
    LOGCALL2();
    //il2cpp::vm::Runtime::SetConfigDir(config_path);
}

void il2cpp_set_data_dir(const char *data_path)
{
    LOGCALL2();
   // il2cpp::utils::Runtime::SetDataDir(data_path);
}

void il2cpp_set_temp_dir(const char *temp_dir)
{
    LOGCALL2();
  //  il2cpp::vm::Path::SetTempPath(temp_dir);
}

void il2cpp_set_commandline_arguments(int argc, const char* const argv[], const char* basedir)
{
    LOGCALL();
    mono_jit_parse_options(argc, const_cast<char**>(argv));
}

void il2cpp_set_commandline_arguments_utf16(int argc, const Il2CppChar* const argv[], const char* basedir)
{
    LOGCALL2();
    //il2cpp::utils::Environment::SetMainArgs(argv, argc);
}

void il2cpp_set_config_utf16(const Il2CppChar* executablePath)
{
    LOGCALL2();
    //il2cpp::vm::Runtime::SetConfigUtf16(executablePath);
}

void il2cpp_set_config(const char* executablePath)
{
    LOGCALL2();
   // il2cpp::vm::Runtime::SetConfig(executablePath);
}

void il2cpp_set_memory_callbacks(Il2CppMemoryCallbacks* callbacks)
{
    LOGCALL2();
    //Memory::SetMemoryCallbacks(callbacks);
}
static size_t RegionSize; //lol
void il2cpp_memory_pool_set_region_size(size_t size)
{
    LOGCALL();
    RegionSize = size;
}

size_t il2cpp_memory_pool_get_region_size()
{
    LOGCALL();
    return RegionSize;
}

void* il2cpp_alloc(size_t size)
{
    LOGCALL2();
    return nullptr;
    //return IL2CPP_MALLOC(size);
}

void il2cpp_free(void* ptr)
{
    LOGCALL();
    mono_free(ptr);
}


Il2CppArray* il2cpp_array_new_specific(Il2CppClass *arrayTypeInfo, il2cpp_array_size_t length)
{
    LOGCALL2();
    return (Il2CppArray*)mono_array_new_specific(mono_class_vtable(Domain, arrayTypeInfo->original), length);
}

Il2CppArray* il2cpp_array_new_full(Il2CppClass *array_class, il2cpp_array_size_t *lengths, il2cpp_array_size *lower_bounds)
{
    LOGCALL2();
    return (Il2CppArray*)mono_array_new_full(Domain, array_class->original, lengths, lower_bounds);
}

Il2CppClass* il2cpp_bounded_array_class_get(Il2CppClass *element_class, uint32_t rank, bool bounded)
{
    LOGCALL();
    return (Il2CppClass*)mono_bounded_array_class_get(element_class->original, rank, bounded);
}

// class

const Il2CppType* il2cpp_class_enum_basetype(Il2CppClass *klass)
{
    LOGCALL();
    MonoType* baseType = mono_class_enum_basetype(klass->original);
    return (const Il2CppType*)baseType;
}

Il2CppClass* il2cpp_class_from_system_type(Il2CppReflectionType *type)
{
    LOGCALL();
    auto* t = (MonoReflectionType*)type;
    return WrapClass(mono_class_from_mono_type(t->type));
}

bool il2cpp_class_is_inited(const Il2CppClass *klass)
{
    LOGCALL2();
    return true;//klass->initialized;
}

bool il2cpp_class_is_generic(const Il2CppClass *klass)
{
    MonoType* type = mono_class_get_type(klass->original);
    if (type && mono_type_get_type(type) == 0x15) return false;

    const char* name = klass->name;
    return name && strchr(name, '`') != nullptr;
}

bool il2cpp_class_is_inflated(const Il2CppClass *klass)
{
    LOGCALL();
    MonoType* type = mono_class_get_type(klass->original);
    return mono_type_get_type(type) == MONO_TYPE_GENERICINST;
}

bool il2cpp_class_has_parent(Il2CppClass *klass, Il2CppClass *klassc)
{
    LOGCALL();
    MonoClass* k = klass->original;
    MonoClass* target = klassc->original;
    while (k != nullptr) {
        if (k == target) {
            return true;
        }
        k = mono_class_get_parent(k);
    }
    return false;
}

Il2CppClass* il2cpp_class_get_element_class(Il2CppClass *klass)
{ LOGCALL();
    return WrapClass(mono_class_get_element_class(klass->original));
}

const EventInfo* il2cpp_class_get_events(Il2CppClass *klass, void* *iter)
{ LOGCALL();
    return (EventInfo*)mono_class_get_events(klass->original, iter);
}

Il2CppClass* il2cpp_class_get_nested_types(Il2CppClass *klass, void* *iter)
{ LOGCALL();
    return WrapClass(mono_class_get_nested_types(klass->original, iter));
}

Il2CppClass* il2cpp_class_get_interfaces(Il2CppClass *klass, void* *iter)
{ LOGCALL();
    return WrapClass(mono_class_get_interfaces(klass->original, iter));
}

const PropertyInfo* il2cpp_class_get_properties(Il2CppClass *klass, void* *iter)
{ LOGCALL();
    return (PropertyInfo*)mono_class_get_properties(klass->original, iter);
}

const PropertyInfo* il2cpp_class_get_property_from_name(Il2CppClass *klass, const char *name)
{ LOGCALL();
    return (PropertyInfo*)mono_class_get_property_from_name(klass->original, name);
}

Il2CppClass* il2cpp_class_get_declaring_type(Il2CppClass* klass)
{ //LOGCALL();
    return WrapClass(mono_class_get_nesting_type(klass->original));
}

size_t il2cpp_class_num_fields(const Il2CppClass* klass)
{ LOGCALL();
    return mono_class_num_fields(klass->original);
}

bool il2cpp_class_is_blittable(const Il2CppClass* klass)
{ LOGCALL();
    return IsMonoClassBlittable(klass->original);
}

int32_t il2cpp_class_value_size(Il2CppClass *klass, uint32_t *align)
{ LOGCALL();
    return mono_class_value_size(klass->original, align);
}

int il2cpp_class_get_flags(const Il2CppClass *klass)
{ LOGCALL();
    return mono_class_get_flags(klass->original);
}

bool il2cpp_class_is_abstract(const Il2CppClass *klass)
{ //LOGCALL();
    
    auto flags = mono_class_get_flags(klass->original);
    bool is_abstract = (flags & TYPE_ATTRIBUTE_ABSTRACT) != 0;
    return is_abstract;
}

bool il2cpp_class_is_interface(const Il2CppClass *klass)
{ //LOGCALL();
    
    return MONO_CLASS_IS_INTERFACE(klass->original);
}

uint32_t il2cpp_class_get_type_token(Il2CppClass *klass)
{ LOGCALL();
    return mono_class_get_type_token(klass->original);
}

bool il2cpp_class_has_references(Il2CppClass *klass)
{ LOGCALL2();
    return false;
}

bool il2cpp_class_is_enum(const Il2CppClass *klass)
{ //LOGCALL();
    
    
    return mono_class_is_enum(klass->original);
}

const char *il2cpp_class_get_assemblyname(const Il2CppClass *klass)
{ //LOGCALL();
    
    return GetAssemblyName(klass->original);
}

int il2cpp_class_get_rank(const Il2CppClass *klass)
{ LOGCALL();
    return mono_class_get_rank(klass->original);
}

uint32_t il2cpp_class_get_data_size(const Il2CppClass *klass)
{ LOGCALL2();
    return NULL;//klass->static_fields_size;
}

void* il2cpp_class_get_static_field_data(const Il2CppClass *klass)
{ LOGCALL2();
    return NULL;//klass->static_fields;
}

// testing only
size_t il2cpp_class_get_bitmap_size(const Il2CppClass *klass)
{ LOGCALL2();
    return NULL;//Class::GetBitmapSize(klass);
}

void il2cpp_class_get_bitmap(Il2CppClass *klass, size_t* bitmap)
{ LOGCALL2();
    size_t dummy = 0;
    //Class::GetBitmap(klass, bitmap, dummy);
}

// stats

extern Il2CppRuntimeStats il2cpp_runtime_stats{};


uint64_t il2cpp_stats_get_value(Il2CppStat stat)
{ LOGCALL();

    switch (stat)
    {
        case IL2CPP_STAT_NEW_OBJECT_COUNT:
            return il2cpp_runtime_stats.new_object_count;

        case IL2CPP_STAT_INITIALIZED_CLASS_COUNT:
            return il2cpp_runtime_stats.initialized_class_count;

            /*case IL2CPP_STAT_GENERIC_VTABLE_COUNT:
                return il2cpp_runtime_stats.generic_vtable_count;

            case IL2CPP_STAT_USED_CLASS_COUNT:
                return il2cpp_runtime_stats.used_class_count;*/

        case IL2CPP_STAT_METHOD_COUNT:
            return il2cpp_runtime_stats.method_count;

            /*case IL2CPP_STAT_CLASS_VTABLE_SIZE:
                return il2cpp_runtime_stats.class_vtable_size;*/

        case IL2CPP_STAT_CLASS_STATIC_DATA_SIZE:
            return il2cpp_runtime_stats.class_static_data_size;

        case IL2CPP_STAT_GENERIC_INSTANCE_COUNT:
            return il2cpp_runtime_stats.generic_instance_count;

        case IL2CPP_STAT_GENERIC_CLASS_COUNT:
            return il2cpp_runtime_stats.generic_class_count;

        case IL2CPP_STAT_INFLATED_METHOD_COUNT:
            return il2cpp_runtime_stats.inflated_method_count;

        case IL2CPP_STAT_INFLATED_TYPE_COUNT:
            return il2cpp_runtime_stats.inflated_type_count;

            /*case IL2CPP_STAT_DELEGATE_CREATIONS:
                return il2cpp_runtime_stats.delegate_creations;

            case IL2CPP_STAT_MINOR_GC_COUNT:
                return il2cpp_runtime_stats.minor_gc_count;

            case IL2CPP_STAT_MAJOR_GC_COUNT:
                return il2cpp_runtime_stats.major_gc_count;

            case IL2CPP_STAT_MINOR_GC_TIME_USECS:
                return il2cpp_runtime_stats.minor_gc_time_usecs;

            case IL2CPP_STAT_MAJOR_GC_TIME_USECS:
                return il2cpp_runtime_stats.major_gc_time_usecs;*/
    }
    return 0;
}
bool il2cpp_stats_dump_to_file(const char *path)
{ LOGCALL();
    std::fstream fs;

    fs.open(path, std::fstream::out | std::fstream::trunc);

    fs << "New object count: " << il2cpp_stats_get_value(IL2CPP_STAT_NEW_OBJECT_COUNT) << "\n";
    fs << "Method count: " << il2cpp_stats_get_value(IL2CPP_STAT_METHOD_COUNT) << "\n";
    fs << "Class static data size: " << il2cpp_stats_get_value(IL2CPP_STAT_CLASS_STATIC_DATA_SIZE) << "\n";
    fs << "Inflated method count: " << il2cpp_stats_get_value(IL2CPP_STAT_INFLATED_METHOD_COUNT) << "\n";
    fs << "Inflated type count: " << il2cpp_stats_get_value(IL2CPP_STAT_INFLATED_TYPE_COUNT) << "\n";
    fs << "Initialized class count: " << il2cpp_stats_get_value(IL2CPP_STAT_INITIALIZED_CLASS_COUNT) << "\n";
    fs << "Generic instance count: " << il2cpp_stats_get_value(IL2CPP_STAT_GENERIC_INSTANCE_COUNT) << "\n";
    fs << "Generic class count: " << il2cpp_stats_get_value(IL2CPP_STAT_GENERIC_CLASS_COUNT) << "\n";

    fs.close();


    return true;
}
void il2cpp_format_stack_trace(const Il2CppException* ex, char* output, int output_size)
{ LOGCALL2();
    //strncpy(output, il2cpp::utils::Exception::FormatStackTrace(ex).c_str(), output_size);
}

void il2cpp_unhandled_exception(Il2CppException* exc)
{ LOGCALL();
   mono_unhandled_exception(&((MonoException*)exc)->object);
}

void il2cpp_native_stack_trace(const Il2CppException* ex, uintptr_t** addresses, int* numFrames, char** imageUUID, char** imageName)
{
    LOGCALL(); //holy vibe slop

    *addresses = nullptr;
    *numFrames = 0;
    *imageUUID = nullptr;
    *imageName = nullptr;

    if (!ex)
        return;

    MonoException* monoEx =
        reinterpret_cast<MonoException*>(const_cast<Il2CppException*>(ex));

    if (!monoEx->native_trace_ips)
        return;

    int count = (int)mono_array_length(monoEx->native_trace_ips);

    if (count <= 0)
        return;

    *addresses = static_cast<uintptr_t*>(
        il2cpp_alloc(sizeof(uintptr_t) * count)
    );

    if (!*addresses)
        return;

    for (int i = 0; i < count; ++i)
    {
        (*addresses)[i] =
            mono_array_get(monoEx->native_trace_ips, uintptr_t, i);
    }

    *numFrames = count;
}

// field

const char* il2cpp_field_get_name(FieldInfo *field)
{ //LOGCALL();
    return mono_field_get_name((MonoClassField*)field);
}

int il2cpp_field_get_flags(FieldInfo *field)
{// LOGCALL();
    return mono_field_get_flags((MonoClassField*)field);
}

Il2CppClass* il2cpp_field_get_parent(FieldInfo *field)
{
    //LOGCALL();
    return WrapClass(mono_field_get_parent((MonoClassField*)field));
}

size_t il2cpp_field_get_offset(FieldInfo *field)
{// LOGCALL();
    return mono_field_get_offset((MonoClassField*)field);
}

const Il2CppType* il2cpp_field_get_type(FieldInfo *field)
{ //LOGCALL();
    return (Il2CppType*)mono_field_get_type((MonoClassField*)field);
}

Il2CppObject* il2cpp_field_get_value_object(FieldInfo *field, Il2CppObject *obj)
{ LOGCALL();
    return (Il2CppObject*)mono_field_get_value_object(Domain, (MonoClassField*)field, (MonoObject*)obj);
}

bool il2cpp_field_has_attribute(FieldInfo *field, Il2CppClass *attr_class)
{ //LOGCALL();
    MonoCustomAttrInfo* attr = mono_custom_attrs_from_field(mono_field_get_parent((MonoClassField*)field), (MonoClassField*)field);
    if (!attr) return false;
    bool result = mono_custom_attrs_has_attr(attr, attr_class->original);
    mono_custom_attrs_free(attr);
    return result;
}

void il2cpp_field_set_value_object(Il2CppObject* objectInstance, FieldInfo* field, Il2CppObject* value)
{ LOGCALL();
    MonoObject* v = (MonoObject*)value;
    mono_field_set_value((MonoObject*)objectInstance, (MonoClassField*)field, &v);
}

bool il2cpp_field_is_literal(FieldInfo *field)
{ LOGCALL2();
    return NULL;//(field->type->attrs & FIELD_ATTRIBUTE_LITERAL) != 0;
}

// gc
void il2cpp_gc_collect(int maxGenerations)
{ LOGCALL();
    mono_gc_collect(maxGenerations);
}

int32_t il2cpp_gc_collect_a_little()
{ LOGCALL2();
    return NULL;//mono_gc_collect_a_little();
}

void il2cpp_gc_start_incremental_collection()
{
    LOGCALL();
    mono_gc_start_incremental_collection();
}

void il2cpp_gc_enable()
{ LOGCALL2();
    //GarbageCollector::Enable();
}

void il2cpp_gc_disable()
{ LOGCALL2();
   // GarbageCollector::Disable();
}

bool il2cpp_gc_is_disabled()
{ LOGCALL2();
    return false;//GarbageCollector::IsDisabled();
}

void il2cpp_gc_set_mode(Il2CppGCMode mode)
{ LOGCALL2();
    //GarbageCollector::SetMode(mode);
}

bool il2cpp_gc_is_incremental()
{ //LOGCALL();
    return mono_gc_is_incremental();
}

int64_t il2cpp_gc_get_max_time_slice_ns()
{ LOGCALL2();
    return 0; //GarbageCollector::GetMaxTimeSliceNs();
}

void il2cpp_gc_set_max_time_slice_ns(int64_t maxTimeSlice)
{ LOGCALL2();
    //GarbageCollector::SetMaxTimeSliceNs(maxTimeSlice);
}

int64_t il2cpp_gc_get_used_size()
{ LOGCALL2();
    return 0; //GarbageCollector::GetUsedHeapSize();
}

int64_t il2cpp_gc_get_heap_size()
{ LOGCALL2();
    return 0;//GarbageCollector::GetAllocatedHeapSize();
}

void il2cpp_gc_foreach_heap(void(*func)(void* data, void* context), void* userData)
{ LOGCALL2();
    /*MemoryInformation::IterationContext ctx;
    ctx.callback = func;
    ctx.userData = userData;
    il2cpp::gc::GarbageCollector::ForEachHeapSection(&ctx, MemoryInformation::ReportGcHeapSection);
    */
}

void il2cpp_stop_gc_world()
{
    LOGCALL2();
    //LOGW("warning: il2cpp_stop_gc_world is not supported in boehm GC");
}

void il2cpp_start_gc_world()
{ LOGCALL2();
    //LOGW("warning: il2cpp_start_gc_world is not supported in boehm GC");
}

void* il2cpp_gc_alloc_fixed(size_t size)
{ LOGCALL2();
    return NULL;//il2cpp::gc::GarbageCollector::AllocateFixed(size, NULL);
}

void il2cpp_gc_free_fixed(void* address)
{ LOGCALL2();
   // il2cpp::gc::GarbageCollector::FreeFixed(address);
}

void il2cpp_gchandle_foreach_get_target(void(*func)(void*, void*), void* userData)
{ LOGCALL2();
    /*MemoryInformation::IterationContext ctx;
    ctx.callback = func;
    ctx.userData = userData;
    il2cpp::gc::GCHandle::WalkStrongGCHandleTargets(MemoryInformation::ReportGcHandleTarget, &ctx);
    */
}

void il2cpp_gc_wbarrier_set_field(Il2CppObject *obj, void **targetAddress, void *object)
{ //LOGCALL();
    mono_gc_wbarrier_set_field((MonoObject*)obj, targetAddress, (MonoObject*)object);
}

bool il2cpp_gc_has_strict_wbarriers()
{ LOGCALL();
#if IL2CPP_ENABLE_STRICT_WRITE_BARRIERS
    return true;
#else
    return false;
#endif
}

void il2cpp_gc_set_external_allocation_tracker(void(*func)(void*, size_t, int))
{ LOGCALL();
#if IL2CPP_ENABLE_WRITE_BARRIER_VALIDATION
    il2cpp::gc::WriteBarrierValidation::SetExternalAllocationTracker(func);
#endif
}

void il2cpp_gc_set_external_wbarrier_tracker(void(*func)(void**))
{ LOGCALL();
#if IL2CPP_ENABLE_WRITE_BARRIER_VALIDATION
    il2cpp::gc::WriteBarrierValidation::SetExternalWriteBarrierTracker(func);
#endif
}

// vm runtime info
uint32_t il2cpp_object_header_size()
{ LOGCALL2();
    return static_cast<uint32_t>(sizeof(MonoObject));
}

uint32_t il2cpp_array_object_header_size()
{ LOGCALL2();
    return NULL;//static_cast<uint32_t>(kIl2CppSizeOfArray);
}

uint32_t il2cpp_offset_of_array_length_in_array_object_header()
{ LOGCALL2();
    return NULL;//kIl2CppOffsetOfArrayLength;
}

uint32_t il2cpp_offset_of_array_bounds_in_array_object_header()
{ LOGCALL2();
    return NULL;//kIl2CppOffsetOfArrayBounds;
}

uint32_t il2cpp_allocation_granularity()
{ LOGCALL2();
    return static_cast<uint32_t>(2 * sizeof(void*));
}

// liveness

void* il2cpp_unity_liveness_allocate_struct(Il2CppClass* filter, int max_object_count, il2cpp_register_object_callback callback, void* userdata, il2cpp_liveness_reallocate_callback reallocate)
{ LOGCALL();
    auto* state =
            static_cast<Il2CppLivenessState*>(std::malloc(sizeof(Il2CppLivenessState)));

    state->register_callback = callback;
    state->reallocate_callback = reallocate;
    state->il2cpp_userdata = userdata;

    MonoClass* mono_filter = filter->original;

    state->mono_state =
        mono_unity_liveness_allocate_struct(
            mono_filter,
            static_cast<guint>(max_object_count),
            liveness_register_trampoline,
            state,
            liveness_reallocate_trampoline);

    if (!state->mono_state)
    {
        std::free(state);
        return nullptr;
    }

    return state;
}

void il2cpp_unity_liveness_calculation_from_root(Il2CppObject* root, Il2CppLivenessState* state)
{ LOGCALL();
   mono_unity_liveness_calculation_from_root((MonoObject*)root, state->mono_state);
}

void il2cpp_unity_liveness_calculation_from_statics(Il2CppLivenessState* state)
{ LOGCALL();
    mono_unity_liveness_calculation_from_statics(state->mono_state);
}

void il2cpp_unity_liveness_finalize(Il2CppLivenessState* state)
{ LOGCALL();
   mono_unity_liveness_finalize(state->mono_state);
}

void il2cpp_unity_liveness_free_struct(Il2CppLivenessState* state)
{ LOGCALL();
   mono_unity_liveness_free_struct(state->mono_state);
    std::free(state);
}

// method

const Il2CppType* il2cpp_method_get_return_type(const MethodInfo* method)
{ LOGCALL();
    return method->return_type;
}

const MethodInfo* il2cpp_method_get_from_reflection(const Il2CppReflectionMethod *method)
{ LOGCALL();
    const MonoReflectionMethod* monoMethod = (MonoReflectionMethod*)method;
    return WrapMethod(monoMethod->method);
}

Il2CppReflectionMethod* il2cpp_method_get_object(const MethodInfo *method, Il2CppClass *refclass)
{ LOGCALL();
    return (Il2CppReflectionMethod* )mono_method_get_object(Domain, method->originalMethod, refclass->original);
}

const char* il2cpp_method_get_name(const MethodInfo *method)
{ //LOGCALL();
    return mono_method_get_name(method->originalMethod);
}

bool il2cpp_method_is_generic(const MethodInfo *method)
{ LOGCALL();
    return method->is_generic;
}

bool il2cpp_method_is_inflated(const MethodInfo *method)
{ LOGCALL();
    return method->is_inflated;
}

uint32_t il2cpp_method_get_param_count(const MethodInfo *method)
{ //LOGCALL();
    return method->parameters_count;
}

const Il2CppType* il2cpp_method_get_param(const MethodInfo *method, uint32_t index)
{ LOGCALL();
    if (index < method->parameters_count) {
        return method->parameters[index];
    }
    return NULL;
}

Il2CppClass* il2cpp_method_get_class(const MethodInfo *method)
{ LOGCALL();
    return method->klass;
}

bool il2cpp_method_has_attribute(const MethodInfo *method, Il2CppClass *attr_class)
{ LOGCALL();
    MonoCustomAttrInfo* attr = mono_custom_attrs_from_method(method->originalMethod);
    if (!attr) return false;
    bool result = mono_custom_attrs_has_attr(attr, attr_class->original);
    mono_custom_attrs_free(attr);
    return result;
}

Il2CppClass* il2cpp_method_get_declaring_type(const MethodInfo* method)
{ LOGCALL();
    return method->klass;
}

uint32_t il2cpp_method_get_flags(const MethodInfo *method, uint32_t *iflags)
{ LOGCALL();
    return method->flags;
}

uint32_t il2cpp_method_get_token(const MethodInfo *method)
{ LOGCALL();
    return method->token;
}

const char *il2cpp_method_get_param_name(const MethodInfo *method, uint32_t index)
{ LOGCALL2();
    return NULL;//Method::GetParamName(method, index);
}

// property

const char* il2cpp_property_get_name(PropertyInfo *prop)
{ LOGCALL();
    return mono_property_get_name((MonoProperty*)prop);
}

const MethodInfo* il2cpp_property_get_get_method(PropertyInfo *prop)
{ LOGCALL();
    return WrapMethod(mono_property_get_get_method((MonoProperty*)prop));
}

const MethodInfo* il2cpp_property_get_set_method(PropertyInfo *prop)
{ LOGCALL();
    return WrapMethod(mono_property_get_set_method((MonoProperty*)prop));
}

Il2CppClass* il2cpp_property_get_parent(PropertyInfo *prop)
{ LOGCALL();
    return WrapClass(mono_property_get_parent((MonoProperty*)prop));
}

uint32_t il2cpp_property_get_flags(PropertyInfo *prop)
{ LOGCALL();
    return mono_property_get_flags((MonoProperty*)prop);
}

// object

uint32_t il2cpp_object_get_size(Il2CppObject* obj)
{ LOGCALL();
    return mono_object_get_size((MonoObject*)obj);
}

void il2cpp_monitor_pulse_all(Il2CppObject* obj)
{ LOGCALL2();
    //Monitor::PulseAll(obj);
}


bool il2cpp_monitor_try_wait(Il2CppObject* obj, uint32_t timeout)
{ LOGCALL2();
    return NULL;//Monitor::TryWait(obj, timeout);
}

void il2cpp_runtime_object_init_exception(Il2CppObject *obj, Il2CppException **exc)
{ LOGCALL();
    MonoObject* mono_obj = (MonoObject*)obj;
    MonoClass* klass = mono_object_get_class(mono_obj);
    MonoMethod* ctor =
        mono_class_get_method_from_name(klass, ".ctor", 0);
    if (ctor == nullptr) {
        return;
    }
    mono_runtime_invoke(
        ctor,
        mono_obj,
        nullptr,
        (MonoObject**)exc
    );
}

void il2cpp_runtime_unhandled_exception_policy_set(Il2CppRuntimeUnhandledExceptionPolicy value)
{ LOGCALL();
    //Runtime::SetUnhandledExceptionPolicy(value);
}

Il2CppString* il2cpp_string_intern(Il2CppString* str)
{ LOGCALL2();
    return NULL;//String::Intern(str);
}

Il2CppString* il2cpp_string_is_interned(Il2CppString* str)
{ LOGCALL2();
    return NULL;//String::IsInterned(str);
}

Il2CppThread **il2cpp_thread_get_all_attached_threads(size_t *size)
{ LOGCALL2();
    return NULL;//Thread::GetAllAttachedThreads(*size);
}

bool il2cpp_is_vm_thread(Il2CppThread *thread)
{ LOGCALL2();
    return NULL;//Thread::IsVmThread(thread);
}

// stacktrace

void il2cpp_current_thread_walk_frame_stack(Il2CppFrameWalkFunc func, void* user_data)
{ LOGCALL();
    //StackTrace::WalkFrameStack(func, user_data);
}

void il2cpp_thread_walk_frame_stack(Il2CppThread *thread, Il2CppFrameWalkFunc func, void *user_data)
{ LOGCALL();
    //return StackTrace::WalkThreadFrameStack(thread, func, user_data);
}

bool il2cpp_current_thread_get_top_frame(Il2CppStackFrameInfo* frame)
{ LOGCALL2();
    //IL2CPP_ASSERT(frame);
    return false;//StackTrace::GetTopStackFrame(*frame);
}

bool il2cpp_thread_get_top_frame(Il2CppThread* thread, Il2CppStackFrameInfo* frame)
{ LOGCALL2();
    //IL2CPP_ASSERT(frame);
    return false;//StackTrace::GetThreadTopStackFrame(thread, *frame);
}

bool il2cpp_current_thread_get_frame_at(int32_t offset, Il2CppStackFrameInfo* frame)
{ LOGCALL2();
  // IL2CPP_ASSERT(frame);
    return false;//StackTrace::GetStackFrameAt(offset, *frame);
}

bool il2cpp_thread_get_frame_at(Il2CppThread* thread, int32_t offset, Il2CppStackFrameInfo* frame)
{ LOGCALL2();
    //IL2CPP_ASSERT(frame);
    return false;//StackTrace::GetThreadStackFrameAt(thread, offset, *frame);
}

int32_t il2cpp_current_thread_get_stack_depth()
{ LOGCALL2();
    return 0;//static_cast<int32_t>(StackTrace::GetStackDepth());
}

int32_t il2cpp_thread_get_stack_depth(Il2CppThread *thread)
{ LOGCALL2();
    return 0;//StackTrace::GetThreadStackDepth(thread);
}

void il2cpp_set_default_thread_affinity(int64_t affinity_mask)
{ LOGCALL2();
    //Thread::SetDefaultAffinityMask(affinity_mask);
}

void il2cpp_override_stack_backtrace(Il2CppBacktraceFunc stackBacktraceFunc)
{ LOGCALL2();
   // il2cpp::os::StackTrace::OverrideStackBacktrace(stackBacktraceFunc);
}

// type

Il2CppObject* il2cpp_type_get_object(const Il2CppType *type)
{ LOGCALL();
    return (Il2CppObject*)mono_type_get_object(Domain, (MonoType*)type);
}

int il2cpp_type_get_type(const Il2CppType *type)
{ //LOGCALL();
    return mono_type_get_type((MonoType*)type);
}

Il2CppClass* il2cpp_type_get_class_or_element_class(const Il2CppType *type)
{ LOGCALL();
    MonoType* t = (MonoType*)type;
    int typeEnum = mono_type_get_type(t);

    if (typeEnum == MONO_TYPE_SZARRAY || typeEnum == MONO_TYPE_ARRAY) {
        // Array type — get the element class, not the array class itself
        MonoClass* arrayClass = mono_type_get_class(t);
        return WrapClass(mono_class_get_element_class(arrayClass));
    }
    if (typeEnum == MONO_TYPE_PTR) {
        // Pointer type — get what it points to
        MonoType* pointedType = mono_type_get_ptr_type(t);
        return WrapClass(mono_class_from_mono_type(pointedType));
    }

    // Ordinary case — just the class for this type
    return WrapClass(mono_class_from_mono_type(t));
}

char* il2cpp_type_get_name(const Il2CppType *type)
{ LOGCALL();
    return mono_type_get_name((MonoType*)type);
}

char* il2cpp_type_get_assembly_qualified_name(const Il2CppType * type)
{ LOGCALL();
    return mono_type_get_name_full(
         (MonoType*)type,
         MONO_TYPE_NAME_FORMAT_ASSEMBLY_QUALIFIED);
}

char* il2cpp_type_get_reflection_name(const Il2CppType *type)
{ LOGCALL();
    return mono_type_get_name_full((MonoType*)type, MONO_TYPE_NAME_FORMAT_REFLECTION);
}

bool il2cpp_type_is_byref(const Il2CppType *type)
{ LOGCALL();
    return mono_type_is_byref((MonoType*)type);
}

uint32_t il2cpp_type_get_attrs(const Il2CppType *type)
{ LOGCALL();
    return mono_type_get_attrs((MonoType*)type);
}

bool il2cpp_type_equals(const Il2CppType* type, const Il2CppType *otherType)
{ LOGCALL();
    return mono_metadata_type_equal((MonoType*)type, (MonoType*)otherType);
}

bool il2cpp_type_is_static(const Il2CppType *type)
{ LOGCALL2();
    return NULL;
}

bool il2cpp_type_is_pointer_type(const Il2CppType *type)
{ LOGCALL();
    return mono_type_is_pointer((MonoType*)type);
}

// image

const Il2CppAssembly* il2cpp_image_get_assembly(const Il2CppImage *image)
{ LOGCALL();
    return (Il2CppAssembly*)mono_image_get_assembly((MonoImage*)image);
}

const char* il2cpp_image_get_name(const Il2CppImage *image)
{ LOGCALL();
    return mono_image_get_name((MonoImage*)image);
}

const char* il2cpp_image_get_filename(const Il2CppImage *image)
{ LOGCALL();
    return mono_image_get_filename((MonoImage*)image);
}

const MethodInfo* il2cpp_image_get_entry_point(const Il2CppImage *image)
{ LOGCALL2();
   //uint32_t entry_token = mono_image_get_entry_point((MonoImage*)image);
    return NULL;
}

size_t il2cpp_image_get_class_count(const Il2CppImage * image)
{ LOGCALL();
    const MonoTableInfo* table =
        mono_image_get_table_info((MonoImage*)image, MONO_TABLE_TYPEDEF);

    return table ? mono_table_info_get_rows(table) : 0;
}

const Il2CppClass* il2cpp_image_get_class(const Il2CppImage * image, size_t index)
{ LOGCALL2();
    return NULL;//Image::GetType(image, static_cast<AssemblyTypeIndex>(index));
}

Il2CppManagedMemorySnapshot* il2cpp_capture_memory_snapshot()
{ LOGCALL2();
    return NULL;//MemoryInformation::CaptureManagedMemorySnapshot();
}

void il2cpp_free_captured_memory_snapshot(Il2CppManagedMemorySnapshot* snapshot)
{ LOGCALL2();
    //MemoryInformation::FreeCapturedManagedMemorySnapshot(snapshot);
}

void il2cpp_set_find_plugin_callback(Il2CppSetFindPlugInCallback method)
{ LOGCALL2();
    //il2cpp::vm::PlatformInvoke::SetFindPluginCallback(method);
}

// Logging

void il2cpp_register_log_callback(Il2CppLogCallback method)
{ LOGCALL2();
    //il2cpp::utils::Logging::SetLogCallback(method);
}

// Debugger
void il2cpp_debugger_set_agent_options(const char* options)
{ LOGCALL2();
#if IL2CPP_MONO_DEBUGGER
    il2cpp::utils::Debugger::SetAgentOptions(options);
#endif
}

bool il2cpp_is_debugger_attached()
{ LOGCALL2();
    return false;//il2cpp::utils::Debugger::GetIsDebuggerAttached();
}

void il2cpp_register_debugger_agent_transport(Il2CppDebuggerTransport * debuggerTransport)
{ LOGCALL2();
#if IL2CPP_MONO_DEBUGGER
    il2cpp::utils::Debugger::RegisterTransport(debuggerTransport);
#endif
}

bool il2cpp_debug_get_method_info(const MethodInfo* method, Il2CppMethodDebugInfo* methodDebugInfo)
{ LOGCALL2();
#if IL2CPP_ENABLE_NATIVE_STACKTRACES
    return il2cpp::utils::NativeSymbol::GetMethodDebugInfo(method, methodDebugInfo);
#else
    return false;
#endif
}

void il2cpp_unity_install_unitytls_interface(const void* unitytlsInterfaceStruct)
{ LOGCALL2();
    //il2cpp::vm::Runtime::SetUnityTlsInterface(unitytlsInterfaceStruct);
}

// Custom Attributes
Il2CppCustomAttrInfo* il2cpp_custom_attrs_from_class(Il2CppClass *klass)
{ LOGCALL();
    return (Il2CppCustomAttrInfo*)mono_custom_attrs_from_class(klass->original);
}

Il2CppCustomAttrInfo* il2cpp_custom_attrs_from_method(const MethodInfo * method)
{ LOGCALL2();
    return NULL;//(Il2CppCustomAttrInfo*)(MetadataCache::GetCustomAttributeTypeToken(method->klass->image, method->token));
}

Il2CppCustomAttrInfo* il2cpp_custom_attrs_from_field(const FieldInfo * field)
{ LOGCALL2();
   // return (MonoCustomAttrInfo*)mono_custom_attrs_from_field(mono_field(MonoClassField*)field);
    return NULL;//Il2CppCustomAttrInfo*)(MetadataCache::GetCustomAttributeTypeToken(field->parent->image, field->token));
}

bool il2cpp_custom_attrs_has_attr(Il2CppCustomAttrInfo *ainfo, Il2CppClass *attr_klass)
{ LOGCALL();
    return mono_custom_attrs_has_attr((MonoCustomAttrInfo*)ainfo, attr_klass->original);
}

Il2CppObject* il2cpp_custom_attrs_get_attr(Il2CppCustomAttrInfo *ainfo, Il2CppClass *attr_klass)
{ LOGCALL();
    return (Il2CppObject*)mono_custom_attrs_get_attr((MonoCustomAttrInfo*)ainfo, attr_klass->original);
}

Il2CppArray*  il2cpp_custom_attrs_construct(Il2CppCustomAttrInfo *ainfo)
{ LOGCALL();
    MonoCustomAttrInfo* attrInfo = (MonoCustomAttrInfo*)ainfo;
    if (!attrInfo) return nullptr;

    MonoArray* result = mono_custom_attrs_construct(attrInfo);
    return (Il2CppArray*)result;
}

void il2cpp_custom_attrs_free(Il2CppCustomAttrInfo *ainfo)
{ LOGCALL();
    mono_custom_attrs_free((MonoCustomAttrInfo*)ainfo);
}

void il2cpp_type_get_name_chunked(const Il2CppType * type, void(*chunkReportFunc)(void* data, void* userData), void* userData)
{ LOGCALL2();
    //Type::GetNameChunkedRecurse(type, IL2CPP_TYPE_NAME_FORMAT_IL, chunkReportFunc, userData);
}

int il2cpp_class_get_userdata_offset()
{ LOGCALL2();
    return offsetof(struct Il2CppClass, unity_user_data);
}

void il2cpp_class_for_each(void(*klassReportFunc)(Il2CppClass* klass, void* userData), void* userData)
{ LOGCALL2();
  //  MemoryInformation::ReportIL2CppClasses(klassReportFunc, userData);
}
// profiler

//#if IL2CPP_ENABLE_PROFILER

void il2cpp_profiler_install(Il2CppProfiler *prof, Il2CppProfileFunc shutdown_callback)
{LOGCALL2();
   // Profiler::Install(prof, shutdown_callback);
}

void il2cpp_profiler_set_events(Il2CppProfileFlags events)
{LOGCALL2();
   // Profiler::SetEvents(events);
}

void il2cpp_profiler_install_enter_leave(Il2CppProfileMethodFunc enter, Il2CppProfileMethodFunc fleave)
{LOGCALL2();
   // Profiler::InstallEnterLeave(enter, fleave);
}

void il2cpp_profiler_install_allocation(Il2CppProfileAllocFunc callback)
{LOGCALL2();
    //Profiler::InstallAllocation(callback);
}

void il2cpp_profiler_install_gc(Il2CppProfileGCFunc callback, Il2CppProfileGCResizeFunc heap_resize_callback)
{LOGCALL2();
    //Profiler::InstallGC(callback, heap_resize_callback);
}

void il2cpp_profiler_install_fileio(Il2CppProfileFileIOFunc callback)
{LOGCALL2();
   // Profiler::InstallFileIO(callback);
}

void il2cpp_profiler_install_thread(Il2CppProfileThreadFunc start, Il2CppProfileThreadFunc end)
{LOGCALL2();
   // Profiler::InstallThread(start, end);
}

//#endif
// Android
void il2cpp_unity_set_android_network_up_state_func(Il2CppAndroidUpStateFunc func)
{ LOGCALL2();
    //AndroidRuntime::SetNetworkUpStateFunc(func);
}
}