#pragma once
#include <mono/jit/jit.h>
#include <mono/metadata/assembly.h>
#include <mono/metadata/object.h>
#include <mono/metadata/mono-config.h>
#include "InternalCalls.cpp"
#include <format>
#include "Utils.cpp"
#include "MonoUtils.cpp"
#include "JNI.cpp"
#include "Debug.cpp"
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, "IL2CPP", __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, "IL2CPP", __VA_ARGS__)
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, "IL2CPP", __VA_ARGS__)
static std::string DllPath;
static std::string MonoPath;
void ExtractMonoIfNecessary() {
    if (!DirExists(DllPath)) {
        MakeDirsRecursive(DllPath);
        std::vector<uint8_t> Zip;
        if (!ReadAssetToBuffer("Mono/Managed.zip", Zip)) {
            LOGE("Failed to find Managed dlls in apk assets! did you forget to add them?");
            return;
        }
        ExtractZipBuffer(Zip, DllPath);
    }
    if (!DirExists(MonoPath)) {
        std::vector<uint8_t> Zip;
        if (!ReadAssetToBuffer("Mono/mono.zip", Zip)) {
            LOGE("Failed to find mono.zip in apk assets! did you forget to add it?");
            return;
        }
        ExtractZipBuffer(Zip, InternalPath);
    }
}
static bool IsMonoReady = false;

int InitMono(const char* domain_name) {
    DllPath = std::format("{}/mono/4.5", ExternalPath);
    MonoPath = std::format("{}/mono", InternalPath);
    ExtractMonoIfNecessary();
    mono_set_dirs(std::format("{}/lib", MonoPath).c_str(), MonoPath.c_str());
    mono_set_assemblies_path(DllPath.c_str());
    mono_config_parse (NULL);

    Domain = mono_jit_init_version(domain_name, "v4.0.30319");
    if (!Domain) {
        LOGE("mono_jit_init_version failed — corlib likely not found, check mono/4.5 path");
        return -1;
    }
    LOGI("Mono initialized, domain = %p", Domain);
    IsMonoReady = true;
    LoadInterceptors();
    FlushICallQueue();
    BeginDebugging();
    return 0;
}