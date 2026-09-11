cmake_minimum_required(VERSION 4.2)
project(il2cpp)

set(CMAKE_CXX_STANDARD 20)

add_library(il2cpp SHARED
        include/miniz/miniz.c
        il2cpp-api.cpp
)
target_include_directories(il2cpp PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)
target_link_directories(il2cpp PRIVATE
        ${CMAKE_SOURCE_DIR}/libs/${ANDROID_ABI}
)
target_link_libraries(il2cpp PRIVATE
        monosgen-2.0
        log
        android
)
set(CMAKE_BUILD_TYPE Release)
set_target_properties(il2cpp PROPERTIES
        LINK_FLAGS "-s"  # strip symbols at link time
)