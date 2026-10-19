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
            Android.cpp
    )
    target_link_directories(il2cpp PRIVATE
            ${CMAKE_SOURCE_DIR}/libs/${ANDROID_ABI}
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
    set(IOS_MONO_LIBS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/libs/ios")

    file(GLOB IOS_MONO_LIBS CONFIGURE_DEPENDS
            "${IOS_MONO_LIBS_DIR}/*.a"
    )
    add_custom_command(TARGET il2cpp POST_BUILD
            COMMAND "${CMAKE_COMMAND}" -E rm -f
            "$<TARGET_FILE:il2cpp>.merged"

            COMMAND /usr/bin/libtool -static
            -o "$<TARGET_FILE:il2cpp>.merged"
            "$<TARGET_FILE:il2cpp>"
            ${IOS_MONO_LIBS}

            COMMAND "${CMAKE_COMMAND}" -E copy
            "$<TARGET_FILE:il2cpp>.merged"
            "$<TARGET_FILE:il2cpp>"

            COMMAND "${CMAKE_COMMAND}" -E rm -f
            "$<TARGET_FILE:il2cpp>.merged"
    )
endif ()
target_link_libraries(il2cpp PRIVATE fmt::fmt-header-only)
target_include_directories(il2cpp PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)