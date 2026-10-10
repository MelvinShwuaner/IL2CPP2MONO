#pragma once
#include "fmt/include/fmt/format.h"
#if ANDROID
#include <android/log.h>
enum LogTag {
    LOG_DEBUG = ANDROID_LOG_DEBUG,
    LOG_INFO = ANDROID_LOG_INFO,
    LOG_WARN = ANDROID_LOG_WARN,
    LOG_ERROR = ANDROID_LOG_ERROR,
    LOG_FATAL = ANDROID_LOG_FATAL,
  };
template<typename... Args>
void log_format(
    int prio,
    const char* tag,
    fmt::format_string<Args...> fmt,
    Args&&... args)
{
    auto message = fmt::format(fmt, std::forward<Args>(args)...);
    __android_log_write(prio, tag, message.c_str());
}
inline void log(
    int prio,
    const char* tag,
    const char* msg)
{
    __android_log_write(prio, tag, msg);
}
#else
#include <os/log.h>
enum LogTag {
    LOG_DEBUG = OS_LOG_TYPE_DEBUG,
    LOG_INFO  = OS_LOG_TYPE_INFO,
    LOG_WARN  = OS_LOG_TYPE_DEFAULT,
    LOG_ERROR = OS_LOG_TYPE_ERROR,
    LOG_FATAL = OS_LOG_TYPE_FAULT,
};

template<typename... Args>
void log_format(
    int prio,
    const char* tag,
    fmt::format_string<Args...> format,
    Args&&... args)
{
    auto message = fmt::format(
        format,
        std::forward<Args>(args)...
    );

    os_log_with_type(
        OS_LOG_DEFAULT,
        static_cast<os_log_type_t>(prio),
        "%{public}s: %{public}s",
        tag,
        message.c_str()
    );
}

inline void log(int prio, const char* tag, const char* msg)
{
    os_log_with_type(
        OS_LOG_DEFAULT,
        static_cast<os_log_type_t>(prio),
        "%{public}s: %{public}s",
        tag,
        msg
    );
}
#endif

