#pragma once
#include <unordered_map>
#include "il2cpp-api-types.h"
#include "mono/metadata/assembly.h"
#include "mono/metadata/object-forward.h"
#include "mono/metadata/object.h"
#include <sys/mman.h>
#include "mono/metadata/appdomain.h"
#include <mono/metadata/threads.h>
#include <mutex>
#include "mono/metadata/tabledefs.h"
static std::unordered_map<MonoMethod*, MethodInfo*> MethodCache;
static std::mutex Mutex;
std::pair<std::string, std::string> SplitFullNameIntoComponents(const std::string& str)
{
    size_t pos = str.rfind('.');

    if (pos == std::string::npos)
        return { "", str };

    return {
        str.substr(0, pos),
        str.substr(pos + 1)
    };
}
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
static void* liveness_reallocate_trampoline_legacy(void* ptr, int size, void* /*userdata*/)
{
    constexpr size_t kHeader = 16;                 // keeps the returned block 16-byte aligned

    if (size == 0)
    {
        if (ptr)
        {
            char* base = static_cast<char*>(ptr) - kHeader;
            munmap(base, *reinterpret_cast<size_t*>(base));
        }
        return nullptr;
    }

    const size_t total = static_cast<size_t>(size) + kHeader;
    void* base = mmap(nullptr, total, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (base == MAP_FAILED)
        return nullptr;

    *static_cast<size_t*>(base) = total;           // remember the mapping length for the free
    return static_cast<char*>(base) + kHeader;
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
const char* GetAssemblyName(MonoClass* klass) {
    MonoImage* image = mono_class_get_image(klass);
    MonoAssembly* assembly = mono_image_get_assembly(image);
    return mono_assembly_name_get_name(mono_assembly_get_name(assembly));
}