#pragma once
#include <string>
#include <unistd.h>
#include <vector>
#include <android/log.h>
#include <miniz/miniz.h>
#include <sys/stat.h>
#include <elf.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <dlfcn.h>
#include <fstream>

typedef Elf64_Ehdr Elf_Ehdr;
typedef Elf64_Shdr Elf_Shdr;
typedef Elf64_Sym Elf_Sym;

#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, "IL2CPP Utils", __VA_ARGS__)
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, "IL2CPP Utils", __VA_ARGS__)
static void MakeDirsRecursive(const std::string& path) {
    std::string current;
    size_t pos = 0;
    while ((pos = path.find('/', pos + 1)) != std::string::npos) {
        current = path.substr(0, pos);
        mkdir(current.c_str(), 0755);
    }
    mkdir(path.c_str(), 0755);
}
static bool DirExists(const std::string& path) {
    struct stat st;
    if (stat(path.c_str(), &st) != 0) {
        return false; // path doesn't exist at all
    }
    return S_ISDIR(st.st_mode);
}
static bool ExtractZipBuffer(const std::vector<uint8_t>& zipData, const std::string& outDir) {
    mz_zip_archive zip = {};
    if (!mz_zip_reader_init_mem(&zip, zipData.data(), zipData.size(), 0)) {
        LOGE("Failed to open zip archive from memory");
        return false;
    }

    int fileCount = (int)mz_zip_reader_get_num_files(&zip);
    for (int i = 0; i < fileCount; i++) {
        mz_zip_archive_file_stat stat;
        if (!mz_zip_reader_file_stat(&zip, i, &stat)) continue;

        std::string outPath = outDir + "/" + stat.m_filename;
        if (mz_zip_reader_is_file_a_directory(&zip, i)) {
            MakeDirsRecursive(outPath);
            continue;
        }

        size_t lastSlash = outPath.find_last_of('/');
        if (lastSlash != std::string::npos) {
            MakeDirsRecursive(outPath.substr(0, lastSlash));
        }

        if (!mz_zip_reader_extract_to_file(&zip, i, outPath.c_str(), 0)) {
            LOGE("Failed to extract: %s", stat.m_filename);
        }
    }

    mz_zip_reader_end(&zip);
    return true;
}
static void DumpAddress(uintptr_t* address, int Down, int Up = 1) {
    LOGI("data dump: %p", address);
    for (int i = Down; i <= Up; i++) {
        LOGI("%p", (void*)address[i]);
    }
}