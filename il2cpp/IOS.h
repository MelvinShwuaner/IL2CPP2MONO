#pragma once

#include <cstdint>
#include <string>
#include <vector>

bool ReadAssetToBuffer(
    const char* assetPath,
    std::vector<uint8_t>& outBuf
);

inline std::string InternalPath;
inline std::string ExternalPath;
std::string GetApplicationSupportPath();