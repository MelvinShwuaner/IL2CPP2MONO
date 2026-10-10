cmake_minimum_required(VERSION 4.2)
project(il2cpp LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_BUILD_TYPE Release)
set(FMT_TEST OFF CACHE BOOL "" FORCE)
set(FMT_DOC OFF CACHE BOOL "" FORCE)
set(FMT_INSTALL OFF CACHE BOOL "" FORCE)
add_subdirectory(include/fmt EXCLUDE_FROM_ALL)

if(ANDROID)
    add_library(il2cpp SHARED
            include/miniz/miniz.c
            il2cpp-api.cpp
    )
    target_link_directories(il2cpp PRIVATE
            ${CMAKE_SOURCE_DIR}/libs/android/${ANDROID_ABI}
    )

    target_link_libraries(il2cpp PRIVATE
            monosgen-2.0
            log
            android
    )

    target_link_options(il2cpp PRIVATE -s)

else()
    add_library(il2cpp STATIC
            include/miniz/miniz.c
            il2cpp-api.cpp
            IOS.mm
    )
    enable_language(OBJCXX)
    target_link_libraries(il2cpp PRIVATE
            "-framework Foundation"
            z
            iconv
    )
    target_link_directories(il2cpp PRIVATE
            ${CMAKE_SOURCE_DIR}/libs/ios/${CMAKE_OSX_ARCHITECTURES}
    )

    target_link_libraries(il2cpp PRIVATE
            monosgen-2.0
    )
endif ()
target_link_libraries(il2cpp PRIVATE fmt::fmt)
target_include_directories(il2cpp PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)