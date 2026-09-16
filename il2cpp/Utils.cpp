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
//shamelessly skidded from fusioncore AND vibeslopped

std::string GetLibraryPath(const char* library)
{
    FILE* fp = fopen("/proc/self/maps", "r");

    char line[4096];
    while (fgets(line, sizeof(line), fp))
    {
        if (!strstr(line, library))
            continue;

        char* path = strchr(line, '/');
        if (path)
        {
            char* newline = strchr(path, '\n');
            if (newline)
                *newline = '\0';

            fclose(fp);
            return path;
        }
    }
    fclose(fp);
    return NULL;
}
uintptr_t GetVAFromLib(const char* filepath, const char* target_symbol, uintptr_t load_base)
{
    int fd = open(filepath, O_RDONLY);
    if (fd < 0)
        return 0;

    off_t size = lseek(fd, 0, SEEK_END);
    if (size <= 0) {
        close(fd);
        return 0;
    }

    uint8_t* map = (uint8_t*)mmap(
        NULL,
        size,
        PROT_READ,
        MAP_PRIVATE,
        fd,
        0
    );
    close(fd);
    if (map == MAP_FAILED)
        return 0;
    uintptr_t value = 0;
    Elf_Ehdr* ehdr = (Elf_Ehdr*)map;
    if (memcmp(ehdr->e_ident, ELFMAG, SELFMAG) == 0) {
        Elf_Shdr* shdr = (Elf_Shdr*)(map + ehdr->e_shoff);

        for (int i = 0; i < ehdr->e_shnum; i++) {
            if (shdr[i].sh_type != SHT_SYMTAB &&
                shdr[i].sh_type != SHT_DYNSYM)
                continue;
            Elf_Sym* syms = (Elf_Sym*)(map + shdr[i].sh_offset);
            size_t count = shdr[i].sh_size / sizeof(Elf_Sym);

            const char* strtab =
                (const char*)(map + shdr[shdr[i].sh_link].sh_offset);
            for (size_t j = 0; j < count; j++) {
                if (strcmp(
                        &strtab[syms[j].st_name],
                        target_symbol) == 0)
                {
                    value = load_base + (uintptr_t)syms[j].st_value;
                    break;
                }
            }
            if (value != 0)
                break;
        }
    }

    munmap(map, size);
    return value;
}
uintptr_t GetModuleBase(const char* lib_name, const char* known_export_symbol) {
    void* handle = dlopen(lib_name, RTLD_NOLOAD | RTLD_LAZY);
    if (!handle) {
        handle = dlopen(lib_name, RTLD_NOW);
    }
    if (!handle) return 0;

    void* symbol_addr = dlsym(handle, known_export_symbol);
    dlclose(handle);

    if (!symbol_addr) return 0;

    Dl_info info;
    if (dladdr(symbol_addr, &info) && info.dli_fbase) {
        return reinterpret_cast<uintptr_t>(info.dli_fbase);
    }

    return 0;
}