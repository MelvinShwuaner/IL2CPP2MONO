#pragma once
#include <unordered_map>
#include <android/log.h>

#include "il2cpp-api-types.h"
#include "mono/metadata/assembly.h"
#include "mono/metadata/object-forward.h"
#include "mono/metadata/object.h"
#include "mono/utils/mono-publib.h"
#include "mono/metadata/appdomain.h"
#include <mono/metadata/threads.h>
#include <mutex>

#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, "Mono", __VA_ARGS__)
static std::unordered_map<MonoMethod*, MethodInfo*> MethodCache;
static std::unordered_map<MonoClass*, Il2CppClass*> ClassCache;
static std::mutex Mutex;
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
static MonoClass* GetMonitorClass()
{
    static MonoClass* s_monitorClass = nullptr;
    if (!s_monitorClass) {
        s_monitorClass = mono_class_from_name(mono_get_corlib(), "System.Threading", "Monitor");
    }
    return s_monitorClass;
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
        info->methodPointer = (Il2CppMethodPointer)mono_compile_method(m);
    } else {
        info->methodPointer = nullptr;
    }
    info->virtualMethodPointer = info->methodPointer; // same JIT trampoline; refine later if virtual dispatch misbehaves
    info->invoker_method = nullptr; // see note below — likely needs a real invoker eventually
    info->name = mono_method_get_name(m);
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
const char* GetAssemblyName(MonoClass* klass) {
    MonoImage* image = mono_class_get_image(klass);
    MonoAssembly* assembly = mono_image_get_assembly(image);
    return mono_assembly_name_get_name(mono_assembly_get_name(assembly));
}
static void LogObject(MonoObject* exc, const char* context = "")
{
    MonoObject* toStringExc = nullptr;
    MonoString* str = mono_object_to_string(exc, &toStringExc);
    if (toStringExc) {
        LOGE("[%s] Exception occurred formatting MonoObject!", context);
        return;
    }

    if (!str) {
        LOGE("[%s] MonoObject string is null!", context);
        return;
    }
    char* utf8 = mono_string_to_utf8(str);
    LOGE("[%s] MonoObject: %s", context, utf8);
    mono_free(utf8);
}