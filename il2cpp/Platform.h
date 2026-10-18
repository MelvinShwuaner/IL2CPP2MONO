#pragma once

#include <cstdint>
#include <string>
#include <vector>

bool ReadAssetToBuffer(
    const char* assetPath,
    std::vector<uint8_t>& outBuf
);
bool InitPlatform();
inline std::string InternalPath;
const char* GetLibPath(const std::string& MonoPath);
inline std::string ExternalPath;