#pragma once
#include <vector>
#include <android/log.h>
#include <android/asset_manager_jni.h>
#include "android/asset_manager.h"

static jclass ActivityThreadClass = NULL;
static jclass ContextClass = NULL;
static jclass FileClass = NULL;
static JavaVM* JVM = NULL;
static const char* InternalPath;
static const char* ExternalPath;
static AAssetManager* AssetManager = nullptr;
static AAssetManager* GetAssetManager(JNIEnv* env, jobject Context) {
    jmethodID getAssetsMid = env->GetMethodID(ContextClass, "getAssets", "()Landroid/content/res/AssetManager;");
    jobject assetManagerObj = env->CallObjectMethod(Context, getAssetsMid);
    jobject globalAssetManagerObj = env->NewGlobalRef(assetManagerObj); // keep alive past this call
    return AAssetManager_fromJava(env, globalAssetManagerObj);
}

#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, "IL2CPP JNI", __VA_ARGS__)
jobject GetContext(JNIEnv *env) {
    jclass activityThreadCls = env->FindClass("android/app/ActivityThread");

    jmethodID currentActivityThreadMid = env->GetStaticMethodID(
        activityThreadCls, "currentActivityThread", "()Landroid/app/ActivityThread;");
    jobject activityThreadObj = env->CallStaticObjectMethod(activityThreadCls, currentActivityThreadMid);

    jmethodID getApplicationMid = env->GetMethodID(
        activityThreadCls, "getApplication", "()Landroid/app/Application;");
    jobject contextObj = env->CallObjectMethod(activityThreadObj, getApplicationMid);

    return contextObj;
}
static const char* GetPathUsingFunction(jmethodID getFilesDir, JNIEnv* env, jobject Context, bool hasArg) {
    jobject fileObj = hasArg
        ? env->CallObjectMethod(Context, getFilesDir, (jstring)nullptr)
        : env->CallObjectMethod(Context, getFilesDir);

    jclass fileClass = env->FindClass("java/io/File");
    jmethodID getAbsolutePath = env->GetMethodID(fileClass, "getAbsolutePath", "()Ljava/lang/String;");

    auto pathStr = (jstring) env->CallObjectMethod(fileObj, getAbsolutePath);
    return env->GetStringUTFChars(pathStr, nullptr);
}

static int Init(JNIEnv* env) {
    jclass local;

    local = env->FindClass("android/app/ActivityThread");
    ActivityThreadClass = (jclass)env->NewGlobalRef(local);
    env->DeleteLocalRef(local);

    local = env->FindClass("android/content/Context");
    ContextClass = (jclass)env->NewGlobalRef(local);
    env->DeleteLocalRef(local);

    local = env->FindClass("java/io/File");
    FileClass = (jclass)env->NewGlobalRef(local);
    env->DeleteLocalRef(local);

    jobject Context = GetContext(env);
    AssetManager = GetAssetManager(env, Context);
    InternalPath = GetPathUsingFunction(env->GetMethodID(ContextClass, "getFilesDir", "()Ljava/io/File;"), env, Context, false);
    ExternalPath = GetPathUsingFunction(env->GetMethodID(ContextClass, "getExternalFilesDir", "(Ljava/lang/String;)Ljava/io/File;"), env, Context, true);

    return 1;
}
static bool ReadAssetToBuffer(const char* assetPath, std::vector<uint8_t>& outBuf) {
    AAsset* asset = AAssetManager_open(AssetManager, assetPath, AASSET_MODE_BUFFER);
    if (!asset) {
        LOGE("Failed to open asset: %s", assetPath);
        return false;
    }
    off_t size = AAsset_getLength(asset);
    outBuf.resize(size);
    AAsset_read(asset, outBuf.data(), size);
    AAsset_close(asset);
    return true;
}