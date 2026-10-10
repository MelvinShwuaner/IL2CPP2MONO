#import <Foundation/Foundation.h>
#include "IOS.h"
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

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

__attribute__((constructor))
static void IOS_OnLoad() {
    @autoreleasepool {
        const char* path = NSHomeDirectory().UTF8String;
        InternalPath = path;
        NSArray<NSURL*>* urls =
            [[NSFileManager defaultManager]
                URLsForDirectory:NSDocumentDirectory
                       inDomains:NSUserDomainMask];
        path = urls.firstObject.path.UTF8String;
        ExternalPath = path;
    }
}
