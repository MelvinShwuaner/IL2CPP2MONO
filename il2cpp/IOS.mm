#import <Foundation/Foundation.h>
#include "Platform.h"
#include <cstdint>
#include <cstring>
#include <string>
#include "dlfcn.h"
#include <vector>
#include <mono/utils/mono-publib.h>
#include <os/log.h>
MONO_BEGIN_DECLS

MONO_API int mono_ios_jit_prepare (size_t capacity);

MONO_END_DECLS

bool ReadAssetToBuffer(
    const char* assetPath,
    std::vector<uint8_t>& outBuf)
{
    @autoreleasepool {
        NSString* relativePath =
            [NSString stringWithUTF8String:assetPath];

        // Unity iOS StreamingAssets:
        // <AppName.app>/Data/Raw/
        NSString* path =
            [[[NSBundle mainBundle].bundlePath
                stringByAppendingPathComponent:@"Data"]
                stringByAppendingPathComponent:@"Raw"];

        path = [path stringByAppendingPathComponent:relativePath];

        NSError* error = nil;
        NSData* data = [NSData dataWithContentsOfFile:path
                                              options:NSDataReadingMappedIfSafe
                                                error:&error];
        if (!data) {
            NSLog(@"Failed to open asset %s: %@",
                  assetPath, error);
            return false;
        }

        outBuf.resize(data.length);

        if (data.length > 0) {
            std::memcpy(outBuf.data(), data.bytes, data.length);
        }

        return true;
    }
}
const char* GetLibPath(const std::string& MonoPath) {
    NSString* frameworksPath = [[NSBundle mainBundle] privateFrameworksPath];
    return [[frameworksPath stringByAppendingPathComponent:@"MonoRuntime.framework"]
     stringByAppendingPathComponent:@"lib"].UTF8String;
}
bool InitPlatform() {
    @autoreleasepool {
        NSArray<NSURL*>* urls =
            [[NSFileManager defaultManager]
                URLsForDirectory:NSDocumentDirectory
                       inDomains:NSUserDomainMask];
        auto path = urls.firstObject.path;
        InternalPath = path.UTF8String;
        ExternalPath = [path stringByAppendingPathComponent:@"files"].UTF8String;
    }
    int error = mono_ios_jit_prepare(0);
    if (error)
        os_log_with_type(OS_LOG_DEFAULT, OS_LOG_TYPE_FAULT, "Mono iOS preparation failed: errno=%d (%{public}s). did you attach stikdebug? make sure to use the universal script if your device needs it", error, std::strerror(error));
    return !error;
}