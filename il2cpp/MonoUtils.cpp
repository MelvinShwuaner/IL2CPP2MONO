#pragma once
#include <unordered_map>
#include "il2cpp-api-types.h"
#include "mono/metadata/assembly.h"
#include "mono/metadata/object-forward.h"
#include "mono/metadata/object.h"
#include "mono/utils/mono-publib.h"
#include "mono/metadata/appdomain.h"
#include <mono/metadata/threads.h>
#include <mutex>
#include "mono/metadata/tabledefs.h"
static std::unordered_map<MonoMethod*, MethodInfo*> MethodCache;
static std::unordered_map<MonoClass*, Il2CppClass*> ClassCache;
static std::mutex Mutex;

static void liveness_register_trampoline(
    gpointer* arr,
    int size,
    void* userdata)
{
    auto* bridge = static_cast<Il2CppLivenessState*>(userdata);

    bridge->register_callback(
        reinterpret_cast<Il2CppObject**>(arr),
        size,
        bridge->il2cpp_userdata);
}

static void* liveness_reallocate_trampoline(
    void* ptr,
    int size,
    void* userdata)
{
    auto* bridge = static_cast<Il2CppLivenessState*>(userdata);

    return bridge->reallocate_callback(
        ptr,
        static_cast<size_t>(size),
        bridge->il2cpp_userdata);
}


static Il2CppClass* WrapClass(MonoClass* m, bool Lock = true) {
    if (!m) return nullptr;
    std::unique_lock guard(Mutex, std::defer_lock);
    if (Lock)
        guard.lock();

    auto it = ClassCache.find(m);
    if (it != ClassCache.end()) return it->second;
    auto* klass = new Il2CppClass();
    klass->original = m;
    klass->name = mono_class_get_name(m);
    ClassCache[m] = klass;
    return klass;
}
static MonoDomain* Domain;
static MonoThread* AttachThreadIfNeeded() {
    if (mono_domain_get() == nullptr) {
        // Not attached! Attach it to the root domain now
        return mono_thread_attach(Domain);
    }
    return nullptr;
}
static MonoClass* MonitorClass = nullptr;
static MonoClass* GetMonitorClass()
{
    if (!MonitorClass) {
        MonitorClass = mono_class_from_name(mono_get_corlib(), "System.Threading", "Monitor");
    }
    return MonitorClass;
}
static MethodInfo* WrapMethod(MonoMethod* m)
{
    if (!m) return nullptr;
    std::lock_guard lock(Mutex);

    auto it = MethodCache.find(m);
    if (it != MethodCache.end()) return it->second;

    auto* info = new MethodInfo();
    memset(info, 0, sizeof(MethodInfo));

    MonoMethodSignature* sig = mono_method_signature(m);

    uint32_t flags, iflags;
    flags = mono_method_get_flags(m, &iflags);
    if (!sig->has_type_parameters && !(sig->generic_param_count && !m->is_inflated)) {
        info->methodPointer = nullptr;//(Il2CppMethodPointer)mono_compile_method(m); we cant init the classes so early. and it also looks like unity doesn't use the methodpointer, atleast for now.
    } else {
        info->methodPointer = nullptr;
    }
    info->virtualMethodPointer = info->methodPointer; // same JIT trampoline; refine later if virtual dispatch misbehaves
    info->invoker_method = nullptr;
    info->name = m->name;
    info->klass = WrapClass(mono_method_get_class(m), false);
    info->return_type = (const Il2CppType*)mono_signature_get_return_type(sig);

    uint32_t paramCount = mono_signature_get_param_count(sig);
    info->parameters_count = (uint8_t)paramCount;

    if (paramCount > 0) {
        const auto** paramTypes = new const Il2CppType*[paramCount];
        void* iter = nullptr;
        for (uint32_t i = 0; i < paramCount; i++) {
            paramTypes[i] = (const Il2CppType*)mono_signature_get_params(sig, &iter);
        }
        info->parameters = paramTypes;
    } else {
        info->parameters = nullptr;
    }

    info->token = mono_method_get_token(m);
    info->flags = (uint16_t)flags;
    info->iflags = (uint16_t)iflags;
    info->slot = m->slot; // Mono doesn't expose vtable slot the same way — 0 as a safe-ish default; revisit if virtual dispatch breaks
    info->is_generic = m->is_generic;
    info->is_inflated = sig->is_inflated;
    info->wrapper_type = m->wrapper_type; // MONO_WRAPPER_NONE, matches the struct's documented always-zero expectation
    info->has_full_generic_sharing_signature = 0;
    info->originalMethod = m;
    MethodCache[m] = info;
    return info;
}
static bool IsMonoTypeBlittable(MonoType* type);
static bool IsMonoClassBlittable(MonoClass* k) {
    if (!mono_class_is_valuetype(k)) return false;
    if (mono_class_is_enum(k)) return true;

    void* iter = nullptr;
    MonoClassField* field;
    while ((field = mono_class_get_fields(k, &iter)) != nullptr) {
        if (mono_field_get_flags(field) & FIELD_ATTRIBUTE_STATIC) continue; // only instance fields matter for layout
        if (!IsMonoTypeBlittable(mono_field_get_type(field))) return false;
    }
    return true;
}
static bool IsMonoTypeBlittable(MonoType* type)
{
    switch (mono_type_get_type(type)) {
        case MONO_TYPE_I1:
        case MONO_TYPE_U1:
        case MONO_TYPE_I2:
        case MONO_TYPE_U2:
        case MONO_TYPE_I4:
        case MONO_TYPE_U4:
        case MONO_TYPE_I8:
        case MONO_TYPE_U8:
        case MONO_TYPE_R4:
        case MONO_TYPE_R8:
        case MONO_TYPE_I:
        case MONO_TYPE_U:
        case MONO_TYPE_PTR:
            return true;

        case MONO_TYPE_BOOLEAN: // 1 byte managed, marshals as 4-byte BOOL by default — not blittable
        case MONO_TYPE_CHAR:    // UTF-16 managed, marshaling target varies — not blittable
            return false;

        case MONO_TYPE_VALUETYPE: {
            MonoClass* fieldClass = mono_class_from_mono_type(type);
            if (mono_class_is_enum(fieldClass)) return true; // underlying type is always a blittable primitive
            return IsMonoClassBlittable(fieldClass);
        }

        default:
            return false; // reference types, strings, arrays of non-blittable elements, generic params, etc.
    }
}
const char* GetAssemblyName(MonoClass* klass) {
    MonoImage* image = mono_class_get_image(klass);
    MonoAssembly* assembly = mono_image_get_assembly(image);
    return mono_assembly_name_get_name(mono_assembly_get_name(assembly));
}