#include <string>
#include <unordered_map>
#include <mutex>
#include "il2cpp-api-types.h"
#include "mono/metadata/loader.h"
#include "mono/metadata/object.h"
#include <android/log.h>

#include "mono/metadata/tabledefs.h"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, "IL2CPP", __VA_ARGS__)
namespace Interceptors {
    struct Interceptor {
        Interceptor(Il2CppMethodPointer m, Il2CppMethodPointer* o) : method(m), original(o) {}
        Il2CppMethodPointer method;
        Il2CppMethodPointer* original;
    };
    static std::unordered_map<std::string, Interceptor*> InterceptorMap;
    static Interceptor* GetInterceptor(const char* name) {
        auto it = InterceptorMap.find(name);
        return it != InterceptorMap.end() ? it->second : nullptr;
    }
}

static std::unordered_map<std::string, Il2CppMethodPointer> ICallTable;
static std::mutex mutex;
static void AddInternalCall(const char* name, Il2CppMethodPointer method) {
    std::lock_guard lock(mutex);
    Interceptors::Interceptor* interceptor = Interceptors::GetInterceptor(name);
    if (interceptor != nullptr) {
        *interceptor->original = method;
        method = interceptor->method;
    }
    ICallTable[name] = method;
    mono_add_internal_call(name, (void*)method);
}
static Il2CppMethodPointer ResolveICall(const char* name) {
    std::lock_guard lock(mutex);
    auto it = ICallTable.find(name);
    return it != ICallTable.end() ? it->second : nullptr;
}
static std::unordered_map<std::string, Il2CppMethodPointer> ICallQueue;
static void FlushICallQueue()
{
    for (auto& icall : ICallQueue) {
        AddInternalCall(icall.first.c_str(), icall.second);
    }
    ICallQueue.clear();
}
//place all your interceptors here
namespace Interceptors {
    /* example of an interceptor
    typedef void (*GetComponentsForListInternal_original)(MonoObject* obj, Il2CppReflectionType* type, MonoObject* list);
    GetComponentsForListInternal_original originalmethod;
    static void GetComponentsForListInternal(MonoObject* obj, Il2CppReflectionType* type, MonoObject* list) {
        originalmethod(obj, type, list);
    }*/
}
static void LoadInterceptors() {
    //Interceptors::InterceptorMap["UnityEngine.Component::GetComponentsForListInternal"] =
       // new Interceptors::Interceptor((Il2CppMethodPointer)&Interceptors::GetComponentsForListInternal, (Il2CppMethodPointer*)&Interceptors::originalmethod);
}