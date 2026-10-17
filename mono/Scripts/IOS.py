import argparse
from difflib import unified_diff
import hashlib
from pathlib import Path
import subprocess
import sys


BASE_REVISION = "b8eb56fab45dd52845fabba7b7ddc9a80b2b0498"
BASE_BRANCH = "unity-2022.3-mbe"
ASSET_NAMES = ("mono-ios-jit.cpp", "mono-ios-jit.h")
PATCHED_PATHS = (
    'configure.ac',
    'mono/arch/arm64/arm64-codegen.h',
    'mono/metadata/Makefile.am',
    'mono/metadata/icall-signatures.h',
    'mono/metadata/mono-gc.h',
    'mono/metadata/sgen-mono.c',
    'mono/metadata/unity-liveness.c',
    'mono/mini/aot-compiler.c',
    'mono/mini/debugger-agent.c',
    'mono/mini/driver.c',
    'mono/mini/jit.h',
    'mono/mini/mini-arm64.c',
    'mono/mini/mini-runtime.c',
    'mono/mini/mini.c',
    'mono/mini/tramp-arm64.c',
    'mono/utils/Makefile.am',
    'mono/utils/mono-codeman.c',
    'mono/utils/mono-codeman.h',
    'mono/utils/mono-sigcontext.h',
    'mono/utils/mono-threads-mach-helper.c',
    'sdks/builds/ios.mk',
    'mono/utils/mono-log-darwin.c',
    'mono/metadata/w32process-unix-osx.c',
    'mono/metadata/icall-decl.h',
    'mono/Scripts/mono-ios-jit.cpp',
    'mono/Scripts/mono-ios-jit.h',
)
PATCH = (
    'diff --git a/configure.ac b/configure.ac\n'
    '--- a/configure.ac\n'
    '+++ b/configure.ac\n'
    '@@ -5083,6 +5083,48 @@\n'
    ' \n'
    ' AM_CONDITIONAL(TARGET_OSX, test x$target_osx = xyes)\n'
    ' \n'
    '+AC_ARG_ENABLE(ios-jit, [  --enable-ios-jit          Enable the ARM64 iOS JIT code pool], [], [enable_ios_jit=no])\n'
    '+case "$enable_ios_jit" in\n'
    '+yes)\n'
    '+\tif test "x$target_ios" != "xyes" -o "x$TARGET" != "xARM64" -o "x$host" != "x$target"; then\n'
    '+\t\tAC_MSG_ERROR([--enable-ios-jit requires an ARM64 iOS device runtime])\n'
    '+\tfi\n'
    '+\tif test "x$mono_feature_disable_jit" = "xyes"; then\n'
    '+\t\tAC_MSG_ERROR([--enable-ios-jit cannot be combined with --enable-minimal=jit])\n'
    '+\tfi\n'
    '+\tif test "x$support_boehm" != "xno"; then\n'
    '+\t\tAC_MSG_ERROR([--enable-ios-jit requires --disable-boehm and the SGen collector])\n'
    '+\tfi\n'
    '+\tif test "x$enable_llvm" = "xyes" -o "x$enable_llvm_runtime" = "xyes" -o "x$with_bitcode" = "xyes"; then\n'
    '+\t\tAC_MSG_ERROR([--enable-ios-jit requires the Mono JIT without LLVM or bitcode])\n'
    '+\tfi\n'
    '+\tAC_COMPILE_IFELSE([AC_LANG_SOURCE([\n'
    '+#include <TargetConditionals.h>\n'
    '+#include <Availability.h>\n'
    '+#if !TARGET_OS_IOS || TARGET_OS_SIMULATOR || !defined(__aarch64__) || defined(__arm64e__)\n'
    '+#error ARM64 iOS device target required; arm64e is unsupported\n'
    '+#endif\n'
    '+#if __IPHONE_OS_VERSION_MIN_REQUIRED < 170400\n'
    '+#error iOS 17.4 or newer deployment target required\n'
    '+#endif\n'
    '+#if __IPHONE_OS_VERSION_MIN_REQUIRED > __IPHONE_OS_VERSION_MAX_ALLOWED\n'
    '+#error Deployment target exceeds the selected iPhoneOS SDK\n'
    '+#endif\n'
    '+#ifdef DISABLE_JIT\n'
    '+#error JIT must be enabled\n'
    '+#endif\n'
    '+int main (void) { return 0; }\n'
    '+\t])], [], [AC_MSG_ERROR([--enable-ios-jit requires the iPhoneOS SDK, iOS 17.4 or newer, and JIT enabled])])\n'
    '+\tAC_DEFINE(ENABLE_IOS_JIT, 1, [Enable the ARM64 iOS JIT code pool])\n'
    '+\t;;\n'
    '+no)\n'
    '+\t;;\n'
    '+*)\n'
    '+\tAC_MSG_ERROR([--enable-ios-jit accepts only yes or no])\n'
    '+\t;;\n'
    '+esac\n'
    '+AM_CONDITIONAL(ENABLE_IOS_JIT, test x$enable_ios_jit = xyes)\n'
    '+\n'
    ' AC_SUBST(SIZEOF_VOID_P,[$ac_cv_sizeof_void_p])\n'
    ' \n'
    ' if test "x$target_byte_order" = "xG_BIG_ENDIAN"; then\n'
    '@@ -5119,6 +5161,9 @@\n'
    ' dnl\n'
    ' SGEN_DEFINES=\n'
    ' AC_ARG_WITH(sgen,                    [  --with-sgen=yes,no             Extra Generational GC, default=yes],[buildsgen=$with_sgen],[buildsgen=yes])\n'
    '+if test "x$enable_ios_jit" = "xyes" -a "x$buildsgen" != "xyes"; then\n'
    '+   AC_MSG_ERROR([--enable-ios-jit requires --with-sgen=yes])\n'
    '+fi\n'
    ' AC_ARG_WITH(sgen-default-concurrent, [  --with-sgen-default-concurrent=yes,no             Use Concurrent GC, default=no],[],[with_sgen_default_concurrent=no])\n'
    ' if test x$buildsgen = xyes; then\n'
    '    AC_DEFINE(HAVE_MOVING_COLLECTOR, 1, [Moving collector])\n'
    '@@ -5511,6 +5556,9 @@\n'
    ' fi\n'
    ' \n'
    ' AC_ARG_ENABLE(icall-tables,[  --disable-icall-tables Disable the runtime lookup of icalls], icall_tables=$enableval, icall_tables=yes)\n'
    '+if test "x$enable_ios_jit" = "xyes" -a "x$icall_tables" != "xyes"; then\n'
    '+   AC_MSG_ERROR([--enable-ios-jit requires runtime icall tables])\n'
    '+fi\n'
    ' if test "x$icall_tables" = "xno"; then\n'
    '    AC_DEFINE(DISABLE_ICALL_TABLES, 1, [Icall tables disabled])\n'
    ' fi\n'
    'diff --git a/mono/arch/arm64/arm64-codegen.h b/mono/arch/arm64/arm64-codegen.h\n'
    '--- a/mono/arch/arm64/arm64-codegen.h\n'
    '+++ b/mono/arch/arm64/arm64-codegen.h\n'
    '@@ -12,6 +12,10 @@\n'
    ' #define __ARM64_CODEGEN_H__\n'
    ' \n'
    ' #include <glib.h>\n'
    '+\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#include <mono/utils/mono-codeman.h>\n'
    '+#endif\n'
    ' \n'
    ' enum {\n'
    ' \tARMREG_R0 = 0,\n'
    '@@ -123,13 +127,22 @@\n'
    ' \tARMSIZE_X = 0x3\n'
    ' } ARMSize;\n'
    ' \n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#define arm_emit(p, ins) do { guint32 _arm_instruction = (ins); mono_codeman_write_memory ((p), &_arm_instruction, sizeof (_arm_instruction)); (p) += 4; } while (0)\n'
    '+#else\n'
    ' #define arm_emit(p, ins) do { *(guint32*)(p) = (ins); (p) += 4; } while (0)\n'
    '+#endif\n'
    ' \n'
    ' /* Overwrite bits [offset,offset+nbits] with value */\n'
    ' static G_GNUC_UNUSED inline void\n'
    ' arm_set_ins_bits (void *p, int offset, int nbits, guint32 value)\n'
    ' {\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tguint32 instruction = (*(guint32*)p & ~(((1 << nbits) - 1) << offset)) | (value << offset);\n'
    '+\tmono_codeman_write_memory (p, &instruction, sizeof (instruction));\n'
    '+#else\n'
    ' \t*(guint32*)p = (*(guint32*)p & ~(((1 << nbits) - 1) << offset)) | (value << offset);\n'
    '+#endif\n'
    ' }\n'
    ' \n'
    ' /*\n'
    'diff --git a/mono/metadata/Makefile.am b/mono/metadata/Makefile.am\n'
    '--- a/mono/metadata/Makefile.am\n'
    '+++ b/mono/metadata/Makefile.am\n'
    '@@ -476,6 +476,9 @@\n'
    ' libmonoruntime_la_LIBADD = libmonoruntime-config.la $(culture_libraries) $(support_libraries) $(shim_libraries)\n'
    ' \n'
    ' libmonoruntimesgen_la_SOURCES = $(common_sources) $(icall_tables_sources) $(ilgen_sources) $(gc_dependent_sources) $(sgen_sources)\n'
    '+if ENABLE_IOS_JIT\n'
    '+libmonoruntimesgen_la_SOURCES += $(unity_gc_dependent_sources)\n'
    '+endif\n'
    ' # Add CXX_ADD_CFLAGS per-library until/unless https://github.com/dotnet/corefx/pull/31342.\n'
    ' libmonoruntimesgen_la_CFLAGS = $(SGEN_DEFINES) $(GLOBALIZATION_SHIM_DEFINES) @CXX_ADD_CFLAGS@\n'
    ' libmonoruntimesgen_la_LIBADD = libmonoruntime-config.la $(culture_libraries) $(support_libraries) $(shim_libraries)\n'
    'diff --git a/mono/metadata/icall-signatures.h b/mono/metadata/icall-signatures.h\n'
    '--- a/mono/metadata/icall-signatures.h\n'
    '+++ b/mono/metadata/icall-signatures.h\n'
    '@@ -57,7 +57,6 @@\n'
    ' // mono_icall_sig_void_int32\n'
    ' // mono_icall_sig_void_object\n'
    ' // mono_icall_sig_void_ptr\n'
    '-// mono_icall_sig_bool_ptr_ptrref\n'
    ' // mono_icall_sig_double_double_double\n'
    ' // mono_icall_sig_float_float_float\n'
    ' // mono_icall_sig_int_obj_ptr\n'
    '@@ -94,7 +93,6 @@\n'
    ' // mono_icall_sig_void_ptr_ptr\n'
    ' // mono_icall_sig_void_ptr_ptrref\n'
    ' // mono_icall_sig_void_uint32_ptrref\n'
    '-// mono_icall_sig_bool_ptr_int32_ptrref\n'
    ' // mono_icall_sig_int32_int32_ptr_ptrref\n'
    ' // mono_icall_sig_int32_ptr_int32_ptr\n'
    ' // mono_icall_sig_int32_ptr_int32_ptrref\n'
    '@@ -182,7 +180,7 @@\n'
    ' ICALL_SIG (2, (void, int32))\t\t\t\\\n'
    ' ICALL_SIG (2, (void, object))\t\t\t\\\n'
    ' ICALL_SIG (2, (void, ptr))\t\t\t\\\n'
    '-ICALL_SIG (3, (bool, ptr, ptrref))\t\t\\\n'
    '+ICALL_SIG (3, (boolean, ptr, ptrref))\t\t\\\n'
    ' ICALL_SIG (3, (double, double, double))\t\t\\\n'
    ' ICALL_SIG (3, (float, float, float))\t\t\\\n'
    ' ICALL_SIG (3, (int, obj, ptr))\t\t\t\\\n'
    '@@ -220,7 +218,7 @@\n'
    ' ICALL_SIG (3, (void, ptr, ptr))\t\t\t\\\n'
    ' ICALL_SIG (3, (void, ptr, ptrref))\t\t\\\n'
    ' ICALL_SIG (3, (void, uint32, ptrref))\t\t\\\n'
    '-ICALL_SIG (4, (bool, ptr, int32, ptrref))\t\\\n'
    '+ICALL_SIG (4, (boolean, ptr, int32, ptrref))\t\\\n'
    ' ICALL_SIG (4, (int32, int32, ptr, ptrref))\t\\\n'
    ' ICALL_SIG (4, (int32, ptr, int32, ptr))\t\t\\\n'
    ' ICALL_SIG (4, (int32, ptr, int32, ptrref))\t\\\n'
    'diff --git a/mono/metadata/mono-gc.h b/mono/metadata/mono-gc.h\n'
    '--- a/mono/metadata/mono-gc.h\n'
    '+++ b/mono/metadata/mono-gc.h\n'
    '@@ -135,8 +135,8 @@\n'
    ' /*\n'
    '  * Only supported under SGen. These two with Sgen will take and release the LOCK_GC\n'
    '  */\n'
    '-void mono_gc_stop_world (void);\n'
    '-void mono_gc_restart_world (void);\n'
    '+MONO_API void mono_gc_stop_world (void);\n'
    '+MONO_API void mono_gc_restart_world (void);\n'
    ' \n'
    ' MONO_END_DECLS\n'
    ' \n'
    'diff --git a/mono/metadata/sgen-mono.c b/mono/metadata/sgen-mono.c\n'
    '--- a/mono/metadata/sgen-mono.c\n'
    '+++ b/mono/metadata/sgen-mono.c\n'
    '@@ -845,6 +845,9 @@\n'
    ' {\n'
    ' \tLOCK_GC;\n'
    ' \tsgen_stop_world (0, FALSE);\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tsgen_finish_concurrent_work ("liveness", FALSE);\n'
    '+#endif\n'
    ' }\n'
    ' \n'
    ' void\n'
    'diff --git a/mono/metadata/unity-liveness.c b/mono/metadata/unity-liveness.c\n'
    '--- a/mono/metadata/unity-liveness.c\n'
    '+++ b/mono/metadata/unity-liveness.c\n'
    '@@ -347,7 +347,9 @@\n'
    ' \tMonoClass *p;\n'
    ' \tgboolean added_objects = FALSE;\n'
    ' \n'
    '+#ifndef DISABLE_REMOTING\n'
    ' \tif (!isStruct && mono_class_has_parent_fast(klass, mono_defaults.real_proxy_class)) return FALSE;\n'
    '+#endif\n'
    ' \n'
    ' \tg_assert(object);\n'
    ' \n'
    '@@ -400,7 +402,9 @@\n'
    ' \tMonoClass* p;\n'
    ' \tgboolean added_objects = FALSE;\n'
    ' \n'
    '+#ifndef DISABLE_REMOTING\n'
    ' \tif (!isStruct && mono_class_has_parent_fast(klass, mono_defaults.real_proxy_class)) return FALSE;\n'
    '+#endif\n'
    ' \n'
    ' \tg_assert(object);\n'
    ' \n'
    'diff --git a/mono/mini/aot-compiler.c b/mono/mini/aot-compiler.c\n'
    '--- a/mono/mini/aot-compiler.c\n'
    '+++ b/mono/mini/aot-compiler.c\n'
    '@@ -13740,8 +13740,8 @@\n'
    ' \n'
    ' #ifndef MONO_ARCH_HAVE_INTERP_ENTRY_TRAMPOLINE\n'
    ' static MonoMethodSignature * const * const interp_in_static_sigs [] = {\n'
    '-    &mono_icall_sig_bool_ptr_int32_ptrref,\n'
    '-    &mono_icall_sig_bool_ptr_ptrref,\n'
    '+    &mono_icall_sig_boolean_ptr_int32_ptrref,\n'
    '+    &mono_icall_sig_boolean_ptr_ptrref,\n'
    '     &mono_icall_sig_int32_int32_ptrref,\n'
    '     &mono_icall_sig_int32_int32_ptr_ptrref,\n'
    '     &mono_icall_sig_int32_ptr_int32_ptr,\n'
    'diff --git a/mono/mini/debugger-agent.c b/mono/mini/debugger-agent.c\n'
    '--- a/mono/mini/debugger-agent.c\n'
    '+++ b/mono/mini/debugger-agent.c\n'
    '@@ -1855,8 +1855,9 @@\n'
    ' }\n'
    ' \n'
    ' static void\n'
    '-buffer_add_byte (Buffer *buf, guint8 val)\n'
    '-{\n'
    '+buffer_add_byte (void *buffer, guint8 val)\n'
    '+{\n'
    '+\tBuffer *buf = (Buffer *)buffer;\n'
    ' \tbuffer_make_room (buf, 1);\n'
    ' \tbuf->p [0] = val;\n'
    ' \tbuf->p++;\n'
    '@@ -1872,8 +1873,9 @@\n'
    ' }\n'
    ' \n'
    ' static void\n'
    '-buffer_add_int (Buffer *buf, guint32 val)\n'
    '-{\n'
    '+buffer_add_int (void *buffer, guint32 val)\n'
    '+{\n'
    '+\tBuffer *buf = (Buffer *)buffer;\n'
    ' \tbuffer_make_room (buf, 4);\n'
    ' \tbuf->p [0] = (val >> 24) & 0xff;\n'
    ' \tbuf->p [1] = (val >> 16) & 0xff;\n'
    '@@ -1890,8 +1892,9 @@\n'
    ' }\n'
    ' \n'
    ' static void\n'
    '-buffer_add_id (Buffer *buf, int id)\n'
    '-{\n'
    '+buffer_add_id (void *buffer, int id)\n'
    '+{\n'
    '+\tBuffer *buf = (Buffer *)buffer;\n'
    ' \tbuffer_add_int (buf, (guint64)id);\n'
    ' }\n'
    ' \n'
    '@@ -1919,8 +1922,9 @@\n'
    ' }\n'
    ' \n'
    ' static void\n'
    '-buffer_add_string (Buffer *buf, const char *str)\n'
    '-{\n'
    '+buffer_add_string (void *buffer, const char *str)\n'
    '+{\n'
    '+\tBuffer *buf = (Buffer *)buffer;\n'
    ' \tint len;\n'
    ' \n'
    ' \tif (str == NULL) {\n'
    'diff --git a/mono/mini/driver.c b/mono/mini/driver.c\n'
    '--- a/mono/mini/driver.c\n'
    '+++ b/mono/mini/driver.c\n'
    '@@ -2936,6 +2936,13 @@\n'
    ' MonoDomain * \n'
    ' mono_jit_init_version (const char *domain_name, const char *runtime_version)\n'
    ' {\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tint error = mono_ios_jit_prepare (0);\n'
    '+\tif (error) {\n'
    '+\t\tfprintf (stderr, "iOS JIT preparation failed: %s (%d). Attach StikDebug\'s universal script and check MONO_IOS_JIT_POOL_MB before starting Mono.\\n", g_strerror (error), error);\n'
    '+\t\treturn NULL;\n'
    '+\t}\n'
    '+#endif\n'
    ' \tMonoDomain *ret = mini_init (domain_name, runtime_version);\n'
    " \tMONO_ENTER_GC_SAFE_UNBALANCED; //once it is not executing any managed code yet, it's safe to run the gc\n"
    ' \treturn ret;\n'
    'diff --git a/mono/mini/jit.h b/mono/mini/jit.h\n'
    '--- a/mono/mini/jit.h\n'
    '+++ b/mono/mini/jit.h\n'
    '@@ -12,6 +12,12 @@\n'
    ' #include <mono/metadata/appdomain.h>\n'
    ' \n'
    ' MONO_BEGIN_DECLS\n'
    '+\n'
    '+MONO_API int\n'
    '+mono_ios_jit_prepare       (size_t capacity);\n'
    '+\n'
    '+MONO_API mono_bool\n'
    '+mono_ios_jit_contains_code (const void *address, size_t size);\n'
    ' \n'
    ' MONO_API MONO_RT_EXTERNAL_ONLY MonoDomain * \n'
    ' mono_jit_init              (const char *file);\n'
    'diff --git a/mono/mini/mini-arm64.c b/mono/mini/mini-arm64.c\n'
    '--- a/mono/mini/mini-arm64.c\n'
    '+++ b/mono/mini/mini-arm64.c\n'
    '@@ -846,7 +846,11 @@\n'
    ' \n'
    ' \tarm_ldrx_lit (code, ARMREG_IP0, code + 8);\n'
    ' \tarm_brx (code, ARMREG_IP0);\n'
    '-\t*(guint64*)code = (guint64)target;\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tg_assert ((gsize)code % sizeof (guint64) == 0);\n'
    '+#endif\n'
    '+\tguint64 thunk_target = (guint64)target;\n'
    '+\tmono_codeman_write_memory (code, &thunk_target, sizeof (thunk_target));\n'
    ' \tcode += sizeof (guint64);\n'
    ' \n'
    ' \tmono_arch_flush_icache (p, code - p);\n'
    '@@ -2046,6 +2050,9 @@\n'
    ' #if __APPLE__\n'
    ' G_BEGIN_DECLS\n'
    ' void sys_icache_invalidate (void *start, size_t len);\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+void sys_dcache_flush (void *start, size_t len);\n'
    '+#endif\n'
    ' G_END_DECLS\n'
    ' #endif\n'
    ' \n'
    '@@ -2054,6 +2061,9 @@\n'
    ' {\n'
    ' #ifndef MONO_CROSS_COMPILE\n'
    ' #if __APPLE__\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tsys_dcache_flush (mono_codeman_write_address (code), size);\n'
    '+#endif\n'
    ' \tsys_icache_invalidate (code, size);\n'
    ' #else\n'
    " \t/* Don't rely on GCC's __clear_cache implementation, as it caches\n"
    'diff --git a/mono/mini/mini-runtime.c b/mono/mini/mini-runtime.c\n'
    '--- a/mono/mini/mini-runtime.c\n'
    '+++ b/mono/mini/mini-runtime.c\n'
    '@@ -1485,7 +1485,8 @@\n'
    ' \n'
    ' \t\tmono_codeman_enable_write ();\n'
    ' \t\tfor (i = 0; i < patch_info->data.table->table_size; i++) {\n'
    '-\t\t\tjump_table [i] = code + GPOINTER_TO_INT (patch_info->data.table->table [i]);\n'
    '+\t\t\tgpointer jump_target = code + GPOINTER_TO_INT (patch_info->data.table->table [i]);\n'
    '+\t\t\tmono_codeman_write_memory (&jump_table [i], &jump_target, sizeof (jump_target));\n'
    ' \t\t}\n'
    ' \t\tmono_codeman_disable_write ();\n'
    ' \n'
    'diff --git a/mono/mini/mini.c b/mono/mini/mini.c\n'
    '--- a/mono/mini/mini.c\n'
    '+++ b/mono/mini/mini.c\n'
    '@@ -2116,13 +2116,15 @@\n'
    ' \t\t\t}\n'
    ' \n'
    ' \t\t\tfor (i = 0; i < patch_info->data.table->table_size; i++) {\n'
    '+\t\t\t\tgpointer target;\n'
    ' \t\t\t\t/* Might be NULL if the switch is eliminated */\n'
    ' \t\t\t\tif (patch_info->data.table->table [i]) {\n'
    ' \t\t\t\t\tg_assert (patch_info->data.table->table [i]->native_offset);\n'
    '-\t\t\t\t\ttable [i] = GINT_TO_POINTER (patch_info->data.table->table [i]->native_offset);\n'
    '+\t\t\t\t\ttarget = GINT_TO_POINTER (patch_info->data.table->table [i]->native_offset);\n'
    ' \t\t\t\t} else {\n'
    '-\t\t\t\t\ttable [i] = NULL;\n'
    '+\t\t\t\t\ttarget = NULL;\n'
    ' \t\t\t\t}\n'
    '+\t\t\t\tmono_codeman_write_memory (&table [i], &target, sizeof (target));\n'
    ' \t\t\t}\n'
    ' \t\t\tpatch_info->data.table->table = (MonoBasicBlock**)table;\n'
    ' \t\t\tbreak;\n'
    '@@ -2237,6 +2239,11 @@\n'
    ' \t\tunwindlen = mono_arch_unwindinfo_init_method_unwind_info (cfg);\n'
    ' #endif\n'
    ' \n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tif (cfg->thunk_area)\n'
    '+\t\tcfg->code_size += (sizeof (guint64) - (cfg->code_size + unwindlen) % sizeof (guint64)) % sizeof (guint64);\n'
    '+#endif\n'
    '+\n'
    ' \tif (cfg->method->dynamic) {\n'
    ' \t\t/* Allocate the code into a separate memory pool so it can be freed */\n'
    ' \t\tcfg->dynamic_info = g_new0 (MonoJitDynamicMethodInfo, 1);\n'
    '@@ -2259,11 +2266,11 @@\n'
    ' \tif (cfg->thunk_area) {\n'
    ' \t\tcfg->thunks_offset = cfg->code_size + unwindlen;\n'
    ' \t\tcfg->thunks = code + cfg->thunks_offset;\n'
    '-\t\tmemset (cfg->thunks, 0, cfg->thunk_area);\n'
    '+\t\tmono_codeman_set_memory (cfg->thunks, 0, cfg->thunk_area);\n'
    ' \t}\n'
    ' \n'
    ' \tg_assert (code);\n'
    '-\tmemcpy (code, cfg->native_code, cfg->code_len);\n'
    '+\tmono_codeman_write_memory (code, cfg->native_code, cfg->code_len);\n'
    ' \tg_free (cfg->native_code);\n'
    ' \tcfg->native_code = code;\n'
    ' \tcode = cfg->native_code + cfg->code_len;\n'
    'diff --git a/mono/mini/tramp-arm64.c b/mono/mini/tramp-arm64.c\n'
    '--- a/mono/mini/tramp-arm64.c\n'
    '+++ b/mono/mini/tramp-arm64.c\n'
    '@@ -27,7 +27,11 @@\n'
    ' #endif\n'
    ' #include "mono/utils/mono-tls-inline.h"\n'
    ' \n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#define JUMP_TRAMP_PATCH_OFFSET (8 * 4)\n'
    '+#else\n'
    ' #define JUMP_TRAMP_PATCH_OFFSET (7 * 4)\n'
    '+#endif\n'
    ' \n'
    ' void\n'
    ' mono_arch_patch_callsite (guint8 *method_start, guint8 *code_ptr, guint8 *addr)\n'
    '@@ -42,7 +46,10 @@\n'
    ' {\n'
    ' \tMINI_BEGIN_CODEGEN();\n'
    ' \tguint8* patch_addr = jump_tramp + JUMP_TRAMP_PATCH_OFFSET;\n'
    '-\t*(gpointer*)patch_addr = addr;\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tg_assert ((gsize)patch_addr % sizeof (guint64) == 0);\n'
    '+#endif\n'
    '+\tmono_codeman_write_memory (patch_addr, &addr, sizeof (addr));\n'
    ' \tMINI_END_CODEGEN(patch_addr, 8, -1, NULL);\n'
    ' }\n'
    ' \n'
    '@@ -354,11 +361,19 @@\n'
    ' \t\tarm_movkx(code, ARMREG_IP1, (imm >> 32) & 0xffff, 32);\n'
    ' \t\tarm_movkx(code, ARMREG_IP1, (imm >> 48) & 0xffff, 48);\n'
    ' \n'
    '-\t\tarm_adrx(code, ARMREG_IP0, code + (3 * 4));\n'
    '+\t\tarm_adrx(code, ARMREG_IP0, buf + JUMP_TRAMP_PATCH_OFFSET);\n'
    ' \t\tarm_ldrx(code, ARMREG_IP0, ARMREG_IP0, 0);\n'
    ' \t\tcode = mono_arm_emit_brx(code, ARMREG_IP0);\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\t\tarm_nop (code);\n'
    '+\t\tg_assert ((gsize)code % sizeof (guint64) == 0);\n'
    '+#endif\n'
    ' \t\tg_assert(code - buf == JUMP_TRAMP_PATCH_OFFSET);\n'
    '-\t\t*(guint64*)code = (guint64)(gsize)tramp;\n'
    '+\t\tguint64 trampoline_target = (guint64)(gsize)tramp;\n'
    '+\t\tmono_codeman_write_memory (code, &trampoline_target, sizeof (trampoline_target));\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\t\tcode += sizeof (guint64);\n'
    '+#endif\n'
    ' \t}\n'
    ' \telse {\n'
    ' \t\tcode = mono_arm_emit_imm64(code, ARMREG_IP1, (guint64)arg1);\n'
    'diff --git a/mono/utils/Makefile.am b/mono/utils/Makefile.am\n'
    '--- a/mono/utils/Makefile.am\n'
    '+++ b/mono/utils/Makefile.am\n'
    '@@ -325,6 +325,11 @@\n'
    ' libmonoutils_la_CFLAGS = $(JEMALLOC_CFLAGS) @CXX_ADD_CFLAGS@\n'
    ' libmonoutils_la_LDFLAGS = $(JEMALLOC_LDFLAGS)\n'
    ' \n'
    '+if ENABLE_IOS_JIT\n'
    '+libmonoutils_la_SOURCES += ../Scripts/mono-ios-jit.cpp ../Scripts/mono-ios-jit.h\n'
    '+libmonoutils_la_CXXFLAGS = $(JEMALLOC_CFLAGS) $(CXXFLAGS_COMMON)\n'
    '+endif\n'
    '+\n'
    ' endif # !ENABLE_MSVC_ONLY\n'
    ' \n'
    ' libmonoutilsincludedir = $(includedir)/mono-$(API_VER)/mono/utils\n'
    'diff --git a/mono/utils/mono-codeman.c b/mono/utils/mono-codeman.c\n'
    '--- a/mono/utils/mono-codeman.c\n'
    '+++ b/mono/utils/mono-codeman.c\n'
    '@@ -19,6 +19,12 @@\n'
    ' \n'
    ' #include "mono-codeman.h"\n'
    ' #include "mono-mmap.h"\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#include <errno.h>\n'
    '+#include <libkern/OSCacheControl.h>\n'
    '+#include <mono/Scripts/mono-ios-jit.h>\n'
    '+#include "mono-mmap-internals.h"\n'
    '+#endif\n'
    ' #include "mono-counters.h"\n'
    ' #if _WIN32\n'
    ' static void* mono_code_manager_heap;\n'
    '@@ -112,6 +118,23 @@\n'
    ' static void*\n'
    ' codechunk_valloc (void *preferred, guint32 size)\n'
    ' {\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tif (!mono_valloc_can_alloc (size)) {\n'
    '+\t\tg_error ("iOS JIT code allocation of %u bytes exceeds the runtime memory limit", size);\n'
    '+\t\treturn NULL;\n'
    '+\t}\n'
    '+\tvoid *ptr = mono_ios_jit_alloc (size);\n'
    '+\tif (!ptr) {\n'
    '+\t\tint allocation_error = errno;\n'
    '+\t\tif (allocation_error == EPERM)\n'
    '+\t\t\tg_error ("iOS JIT requires mono_ios_jit_prepare with the StikDebug universal script attached before Mono initialization");\n'
    '+\t\telse\n'
    '+\t\t\tg_error ("iOS JIT code allocation of %u bytes failed: %s. Check the prepared code-pool capacity and available memory", size, g_strerror (allocation_error));\n'
    '+\t\treturn NULL;\n'
    '+\t}\n'
    '+\tmono_account_mem (MONO_MEM_ACCOUNT_CODE, size);\n'
    '+\treturn ptr;\n'
    '+#else\n'
    ' \tvoid *ptr;\n'
    ' \tGSList *freelist;\n'
    ' \n'
    '@@ -139,11 +162,16 @@\n'
    ' \t}\n'
    ' \tmono_os_mutex_unlock (&valloc_mutex);\n'
    ' \treturn ptr;\n'
    '+#endif\n'
    ' }\n'
    ' \n'
    ' static void\n'
    ' codechunk_vfree (void *ptr, guint32 size)\n'
    ' {\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tmono_ios_jit_free (ptr, size);\n'
    '+\tmono_account_mem (MONO_MEM_ACCOUNT_CODE, -(ssize_t)size);\n'
    '+#else\n'
    ' \tGSList *freelist;\n'
    ' \n'
    ' \tmono_os_mutex_lock (&valloc_mutex);\n'
    '@@ -155,6 +183,7 @@\n'
    ' \t\tmono_vfree (ptr, size, MONO_MEM_ACCOUNT_CODE);\n'
    ' \t}\n'
    ' \tmono_os_mutex_unlock (&valloc_mutex);\n'
    '+#endif\n'
    ' }\t\t\n'
    ' \n'
    ' static void\n'
    '@@ -192,6 +221,9 @@\n'
    ' mono_code_manager_cleanup (void)\n'
    ' {\n'
    ' \tcodechunk_cleanup ();\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tmono_ios_jit_cleanup ();\n'
    '+#endif\n'
    ' }\n'
    ' \n'
    ' void\n'
    '@@ -204,7 +236,9 @@\n'
    ' int\n'
    ' mono_codeman_allocation_type (MonoCodeManager const *cman)\n'
    ' {\n'
    '-#ifdef FORCE_MALLOC\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\treturn CODE_FLAG_MMAP;\n'
    '+#elif defined(FORCE_MALLOC)\n'
    ' \treturn CODE_FLAG_MALLOC;\n'
    ' #else\n'
    ' \treturn cman->dynamic ? CODE_FLAG_MALLOC : CODE_FLAG_MMAP;\n'
    '@@ -355,6 +389,16 @@\n'
    ' \tg_free (cman);\n'
    ' }\n'
    ' \n'
    '+static void\n'
    '+invalidate_code_chunk (CodeChunk *chunk, int fill_value)\n'
    '+{\n'
    '+\tmono_codeman_set_memory (chunk->data, fill_value, chunk->size);\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\tsys_dcache_flush (mono_codeman_write_address (chunk->data), chunk->size);\n'
    '+\tsys_icache_invalidate (chunk->data, chunk->size);\n'
    '+#endif\n'
    '+}\n'
    '+\n'
    ' /**\n'
    '  * mono_code_manager_invalidate:\n'
    '  * \\param cman a code manager\n'
    '@@ -374,9 +418,9 @@\n'
    ' #endif\n'
    ' \n'
    ' \tfor (chunk = cman->current; chunk; chunk = chunk->next)\n'
    '-\t\tmemset (chunk->data, fill_value, chunk->size);\n'
    '+\t\tinvalidate_code_chunk (chunk, fill_value);\n'
    ' \tfor (chunk = cman->full; chunk; chunk = chunk->next)\n'
    '-\t\tmemset (chunk->data, fill_value, chunk->size);\n'
    '+\t\tinvalidate_code_chunk (chunk, fill_value);\n'
    ' }\n'
    ' \n'
    ' /**\n'
    '@@ -502,7 +546,11 @@\n'
    ' \t\tif (flags == CODE_FLAG_MALLOC)\n'
    ' \t\t\tmono_codeman_free (ptr);\n'
    ' \t\telse\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+\t\t\tcodechunk_vfree (ptr, chunk_size);\n'
    '+#else\n'
    ' \t\t\tmono_vfree (ptr, chunk_size, MONO_MEM_ACCOUNT_CODE);\n'
    '+#endif\n'
    ' \t\treturn NULL;\n'
    ' \t}\n'
    ' \tchunk->next = NULL;\n'
    '@@ -696,3 +744,23 @@\n'
    ' \t}\n'
    ' #endif\n'
    ' }\n'
    '+\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+void*\n'
    '+mono_codeman_write_address (void *address)\n'
    '+{\n'
    '+\treturn mono_ios_jit_write_address (address);\n'
    '+}\n'
    '+\n'
    '+void\n'
    '+mono_codeman_write_memory (void *address, const void *source, size_t size)\n'
    '+{\n'
    '+\tmono_ios_jit_write_memory (address, source, size);\n'
    '+}\n'
    '+\n'
    '+void\n'
    '+mono_codeman_set_memory (void *address, int value, size_t size)\n'
    '+{\n'
    '+\tmono_ios_jit_set_memory (address, value, size);\n'
    '+}\n'
    '+#endif\n'
    'diff --git a/mono/utils/mono-codeman.h b/mono/utils/mono-codeman.h\n'
    '--- a/mono/utils/mono-codeman.h\n'
    '+++ b/mono/utils/mono-codeman.h\n'
    '@@ -44,5 +44,15 @@\n'
    ' void mono_codeman_enable_write (void);\n'
    ' void mono_codeman_disable_write (void);\n'
    ' \n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+void *mono_codeman_write_address (void *address);\n'
    '+void mono_codeman_write_memory (void *address, const void *source, size_t size);\n'
    '+void mono_codeman_set_memory (void *address, int value, size_t size);\n'
    '+#else\n'
    '+#define mono_codeman_write_address(address) (address)\n'
    '+#define mono_codeman_write_memory(address, source, size) memcpy ((address), (source), (size))\n'
    '+#define mono_codeman_set_memory(address, value, size) memset ((address), (value), (size))\n'
    '+#endif\n'
    '+\n'
    ' #endif /* __MONO_CODEMAN_H__ */\n'
    ' \n'
    'diff --git a/mono/utils/mono-sigcontext.h b/mono/utils/mono-sigcontext.h\n'
    '--- a/mono/utils/mono-sigcontext.h\n'
    '+++ b/mono/utils/mono-sigcontext.h\n'
    '@@ -495,7 +495,7 @@\n'
    ' \n'
    ' #ifndef UCONTEXT_REG_SET_PC\n'
    ' #define UCONTEXT_REG_SET_PC(ctx, val) do { \\\n'
    '-\tUCONTEXT_REG_PC (ctx) = (val); \\\n'
    '+\tUCONTEXT_REG_PC (ctx) = (host_mgreg_t)(val); \\\n'
    ' \t } while (0)\n'
    ' #define UCONTEXT_REG_SET_SP(ctx, val) do { \\\n'
    ' \tUCONTEXT_REG_SP (ctx) = (val); \\\n'
    'diff --git a/mono/utils/mono-threads-mach-helper.c b/mono/utils/mono-threads-mach-helper.c\n'
    '--- a/mono/utils/mono-threads-mach-helper.c\n'
    '+++ b/mono/utils/mono-threads-mach-helper.c\n'
    '@@ -57,13 +57,7 @@\n'
    ' static void\n'
    ' mono_dead_letter_dealloc (id self, SEL _cmd)\n'
    ' {\n'
    '-\tstruct objc_super super;\n'
    '-\tsuper.receiver = self;\n'
    '-#if !defined(__cplusplus) && !__OBJC2__\n'
    '-\tsuper.class = nsobject;\n'
    '-#else\n'
    '-\tsuper.super_class = nsobject;\n'
    '-#endif\n'
    '+\tstruct objc_super super = { self, nsobject };\n'
    ' \tvoid (*objc_msgSendSuper_op)(struct objc_super *, SEL) = (void (*)(struct objc_super *, SEL)) objc_msgSendSuper;\n'
    ' \tobjc_msgSendSuper_op (&super, dealloc);\n'
    ' \n'
    'diff --git a/sdks/builds/ios.mk b/sdks/builds/ios.mk\n'
    '--- a/sdks/builds/ios.mk\n'
    '+++ b/sdks/builds/ios.mk\n'
    '@@ -123,6 +123,13 @@\n'
    ' \t--disable-cooperative-suspend \\\n'
    ' \t--disable-hybrid-suspend \\\n'
    ' \t--disable-crash-reporting\n'
    '+\n'
    '+ifeq ($(1),target64)\n'
    '+_ios-$(1)_CONFIGURE_FLAGS := $$(filter-out --disable-icall-tables --enable-minimal=% --with-lazy-gc-thread-creation=yes,$$(_ios-$(1)_CONFIGURE_FLAGS)) \\\n'
    '+\t--enable-minimal=ssa,com,interpreter,portability,assembly_remapping,attach,verifier,full_messages,appdomains,security,sgen_remset,sgen_marksweep_par,sgen_marksweep_fixed,sgen_marksweep_fixed_par,sgen_copying,logging,remoting,shared_perfcounters,gac \\\n'
    '+\t--enable-ios-jit --enable-unity-define --enable-icall-tables --with-sgen=yes \\\n'
    '+\t--disable-llvm --disable-llvm-runtime --with-bitcode=no\n'
    '+endif\n'
    ' \n'
    ' .stamp-ios-$(1)-toolchain:\n'
    ' \ttouch $$@\n'
    'diff --git a/mono/utils/mono-log-darwin.c b/mono/utils/mono-log-darwin.c\n'
    '--- a/mono/utils/mono-log-darwin.c\n'
    '+++ b/mono/utils/mono-log-darwin.c\n'
    '@@ -94,10 +94,17 @@\n'
    ' void\n'
    ' mono_log_write_asl (const char *log_domain, GLogLevelFlags level, mono_bool hdr, const char *message)\n'
    ' {\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#pragma clang diagnostic push\n'
    '+#pragma clang diagnostic ignored "-Wdeprecated-declarations"\n'
    '+#endif\n'
    ' \tasl_log (NULL, NULL, to_asl_priority (level), "%s%s%s\\n",\n'
    ' \t\tlog_domain != NULL ? log_domain : "",\n'
    ' \t\tlog_domain != NULL ? ": " : "",\n'
    ' \t\tmessage);\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#pragma clang diagnostic pop\n'
    '+#endif\n'
    ' \n'
    ' \tif (level & G_LOG_LEVEL_ERROR)\n'
    ' \t\tg_assert_abort ();\n'
    'diff --git a/mono/metadata/w32process-unix-osx.c b/mono/metadata/w32process-unix-osx.c\n'
    '--- a/mono/metadata/w32process-unix-osx.c\n'
    '+++ b/mono/metadata/w32process-unix-osx.c\n'
    '@@ -185,7 +185,14 @@\n'
    ' {\n'
    ' \t#if SIZEOF_VOID_P == 8\n'
    ' \tconst struct mach_header_64 *hdr64 = (const struct mach_header_64 *)hdr32;\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#pragma clang diagnostic push\n'
    '+#pragma clang diagnostic ignored "-Wdeprecated-declarations"\n'
    '+#endif\n'
    ' \tconst struct section_64 *sec = getsectbynamefromheader_64 (hdr64, SEG_DATA, SECT_DATA);\n'
    '+#ifdef ENABLE_IOS_JIT\n'
    '+#pragma clang diagnostic pop\n'
    '+#endif\n'
    ' \t#else\n'
    ' \tconst struct section *sec = getsectbynamefromheader (hdr32, SEG_DATA, SECT_DATA);\n'
    ' \t#endif\n'
    'diff --git a/mono/metadata/icall-decl.h b/mono/metadata/icall-decl.h\n'
    '--- a/mono/metadata/icall-decl.h\n'
    '+++ b/mono/metadata/icall-decl.h\n'
    '@@ -71,6 +71,10 @@\n'
    ' #undef HANDLES_REUSE_WRAPPER\n'
    ' #undef NOHANDLES\n'
    ' #undef MONO_HANDLE_REGISTER_ICALL\n'
    '+\n'
    '+#ifdef DISABLE_REMOTING\n'
    '+ICALL_EXPORT MonoBoolean ves_icall_IsTransparentProxy (MonoObject *proxy);\n'
    '+#endif\n'
    ' \n'
    ' // This is sorted.\n'
    ' // grep ICALL_EXPORT | sort | uniq\n'
)


VALIDATION_SOURCES = {
    "MonoIosValidation.cs": r'''using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace MonoIosValidation
{
    public sealed class Node
    {
        public int Value;
        public Node Next;
    }

    public static class Checks
    {
        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        public delegate int NativeCallback(int value);

        [MethodImpl(MethodImplOptions.InternalCall)]
        private static extern int InvokeNativeCallback(IntPtr callback, int value);

        [MethodImpl(MethodImplOptions.InternalCall)]
        private static extern int ThunkNative(int value);

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static T Identity<T>(T value)
        {
            return value;
        }

        public static int Basic(int value)
        {
            return value * 3 + 12;
        }

        public static int Generics()
        {
            var values = new List<int> { 7, 11, 19 };
            string text = new string(new[] { 'j', 'i', 't' });
            var pair = new KeyValuePair<int, string>(37, text);
            if (Identity(29) != 29 || !Object.ReferenceEquals(Identity(text), text))
                throw new InvalidOperationException("Generic identity failed");
            var copied = Identity(pair);
            if (copied.Key != 37 || !Object.ReferenceEquals(copied.Value, text))
                throw new InvalidOperationException("Generic struct failed");
            return values[0] + values[1] + values[2];
        }

        public static int DynamicMethods()
        {
            var method = new DynamicMethod("AddRuntimeValues", typeof(int), new[] { typeof(int), typeof(int) }, typeof(Checks).Module);
            ILGenerator il = method.GetILGenerator();
            il.Emit(OpCodes.Ldarg_0);
            il.Emit(OpCodes.Ldarg_1);
            il.Emit(OpCodes.Add);
            il.Emit(OpCodes.Ret);
            var add = (Func<int, int, int>)method.CreateDelegate(typeof(Func<int, int, int>));
            int result = add(17, 25);
            GC.KeepAlive(add);
            return result;
        }

        public static int Delegates()
        {
            int total = 0;
            Action<int> first = value => total += value;
            Action<int> second = value => total += value * 2;
            Action<int> combined = first + second;
            combined(9);
            combined -= first;
            combined(5);
            return total;
        }

        private static int CallbackTarget(int value)
        {
            return value * 3 + 5;
        }

        public static int ReverseCallback()
        {
            NativeCallback callback = CallbackTarget;
            IntPtr address = Marshal.GetFunctionPointerForDelegate(callback);
            int result = InvokeNativeCallback(address, 11);
            GC.KeepAlive(callback);
            return result;
        }

        public static int Exceptions()
        {
            int result = 0;
            try
            {
                ThrowExpected();
            }
            catch (InvalidOperationException error)
            {
                if (error.Message != "expected iOS validation exception")
                    throw;
                result = 17;
            }
            finally
            {
                result += 25;
            }
            return result;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThrowExpected()
        {
            throw new InvalidOperationException("expected iOS validation exception");
        }

        public static int ThreadWork(int seed)
        {
            Node head = null;
            for (int i = 0; i < 32; ++i)
            {
                head = new Node { Value = seed + i, Next = head };
                if ((i & 7) == 7)
                    GC.Collect();
            }
            int sum = 0;
            int count = 0;
            for (Node current = head; current != null; current = current.Next)
            {
                sum += current.Value;
                ++count;
            }
            GC.KeepAlive(head);
            if (count != 32)
                throw new InvalidOperationException("Attached-thread root was lost");
            return sum;
        }

        public static object[] CreateGraph()
        {
            var first = new Node { Value = 11 };
            var second = new Node { Value = 22 };
            var third = new Node { Value = 33 };
            var unrelated = new Node { Value = 44 };
            first.Next = second;
            second.Next = third;
            third.Next = first;
            return new object[] { first, second, third, unrelated };
        }

        public static int CheckGraph(object[] values)
        {
            var first = (Node)values[0];
            var second = (Node)values[1];
            var third = (Node)values[2];
            var unrelated = (Node)values[3];
            if (!Object.ReferenceEquals(first.Next, second) || !Object.ReferenceEquals(second.Next, third) ||
                !Object.ReferenceEquals(third.Next, first) || unrelated.Next != null)
                throw new InvalidOperationException("Liveness graph references changed");
            return first.Value + second.Value + third.Value + unrelated.Value;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkTarget(int value) { return value * 3 + 1; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller0(int value) { return ThunkTarget(value); }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller1(int value) { return ThunkTarget(value) + value; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller2(int value) { return ThunkTarget(value) + value * 2; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller3(int value) { return ThunkTarget(value) + value * 3; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller4(int value) { return ThunkTarget(value) + value * 4; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller5(int value) { return ThunkTarget(value) + value * 5; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller6(int value) { return ThunkTarget(value) + value * 6; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int ThunkCaller7(int value) { return ThunkTarget(value) + value * 7; }

        public static int Thunks()
        {
            return ThunkCaller0(5) + ThunkCaller1(5) + ThunkCaller2(5) + ThunkCaller3(5) +
                ThunkCaller4(5) + ThunkCaller5(5) + ThunkCaller6(5) + ThunkCaller7(5);
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller0(int value) { return ThunkNative(value); }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller1(int value) { return ThunkNative(value) + value; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller2(int value) { return ThunkNative(value) + value * 2; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller3(int value) { return ThunkNative(value) + value * 3; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller4(int value) { return ThunkNative(value) + value * 4; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller5(int value) { return ThunkNative(value) + value * 5; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller6(int value) { return ThunkNative(value) + value * 6; }
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static int NativeThunkCaller7(int value) { return ThunkNative(value) + value * 7; }

        public static int NativeThunks()
        {
            return NativeThunkCaller0(5) + NativeThunkCaller1(5) + NativeThunkCaller2(5) + NativeThunkCaller3(5) +
                NativeThunkCaller4(5) + NativeThunkCaller5(5) + NativeThunkCaller6(5) + NativeThunkCaller7(5);
        }
    }
}
''',
    "mono-ios-validation.h": r'''#ifndef MONO_IOS_VALIDATION_H
#define MONO_IOS_VALIDATION_H

#ifdef __cplusplus
extern "C" {
#endif

int mono_ios_validation_run (const char *managed_directory, const char *config_directory, const char *validation_assembly_path);

#ifdef __cplusplus
}
#endif

#endif
''',
    "mono-ios-validation.cpp": r'''#include <TargetConditionals.h>
#if !TARGET_OS_IOS || TARGET_OS_SIMULATOR || !defined(__aarch64__) || defined(__arm64e__)
#error Validation requires an ARM64 iOS device target
#endif
#include "mono-ios-validation.h"

#include <mono/Scripts/mono-ios-jit.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern "C" void mono_arch_flush_icache (uint8_t *code, int size);

static const size_t mono_ios_validation_pool_size = 32u * 1024u * 1024u;
static const uint32_t mono_ios_validation_movz_w0 = 0x52800000u;
static const uint32_t mono_ios_validation_ret = 0xd65f03c0u;
static const uint32_t mono_ios_validation_ldr_x16_literal = 0x58000050u;
static const uint32_t mono_ios_validation_br_x16 = 0xd61f0200u;

static int
mono_ios_validation_call (void *address)
{
	return ((int (*)(void))address) ();
}

extern "C" int
mono_ios_validation_native (void)
{
	void *blocks [4] = { NULL, NULL, NULL, NULL };
	size_t sizes [4] = { 0, 0, 0, 0 };
	const char *failure = NULL;
	int prepare_error = 0;
	bool owns_pool = false;
	uint8_t *code = NULL;
	uint8_t *literal = NULL;
	uint8_t unaligned [sizeof (uint64_t) + 1] __attribute__((aligned(16)));
	uint32_t instructions [2] = { mono_ios_validation_movz_w0 | (0x1357u << 5), mono_ios_validation_ret };
	uint32_t changed_instruction = mono_ios_validation_movz_w0 | (0x2468u << 5);
	uint32_t thunk_instructions [2] = { mono_ios_validation_ldr_x16_literal, mono_ios_validation_br_x16 };
	uint64_t target = 0;

#define MONO_IOS_VALIDATE(condition, message) do { if (!(condition)) { failure = (message); goto finish; } } while (0)

	errno = 0;
	sizes [0] = 16;
	blocks [0] = mono_ios_jit_alloc (sizes [0]);
	MONO_IOS_VALIDATE (!blocks [0] && errno == EPERM, "native validation requires fresh process before Mono initialization");
	prepare_error = mono_ios_jit_prepare (mono_ios_validation_pool_size);
	MONO_IOS_VALIDATE (prepare_error == 0, "32 MiB preparation failed");
	owns_pool = true;
	errno = 0;
	MONO_IOS_VALIDATE (mono_ios_jit_alloc (0) == NULL && errno == EINVAL, "zero-sized allocation was not rejected");
	errno = 0;
	MONO_IOS_VALIDATE (mono_ios_jit_alloc (SIZE_MAX) == NULL && errno == EINVAL, "overflowing allocation was not rejected");

	sizes [0] = mono_ios_validation_pool_size;
	blocks [0] = mono_ios_jit_alloc (sizes [0]);
	MONO_IOS_VALIDATE (blocks [0] != NULL, "exact-fit pool allocation failed");
	MONO_IOS_VALIDATE ((uintptr_t)blocks [0] % 16 == 0, "code allocation is not 16-byte aligned");
	MONO_IOS_VALIDATE (mono_ios_jit_contains_code (blocks [0], sizes [0]), "exact-fit allocation is outside prepared code arena");
	MONO_IOS_VALIDATE (mono_ios_jit_write_address (blocks [0]) != blocks [0], "code allocation has no separate writable alias");
	errno = 0;
	sizes [1] = 16;
	blocks [1] = mono_ios_jit_alloc (sizes [1]);
	MONO_IOS_VALIDATE (!blocks [1] && errno == ENOMEM, "exhausted pool did not return ENOMEM");
	mono_ios_jit_set_memory (blocks [0], 0xa5, sizes [0]);
	MONO_IOS_VALIDATE (((const uint8_t *)blocks [0]) [0] == 0xa5 && ((const uint8_t *)blocks [0]) [sizes [0] - 1] == 0xa5, "pool fill is not visible through executable alias");
	mono_ios_jit_free (blocks [0], sizes [0]);
	blocks [0] = mono_ios_jit_alloc (sizes [0]);
	MONO_IOS_VALIDATE (blocks [0] != NULL, "freed pool could not be reused");
	for (size_t index = 0; index < sizes [0]; ++index)
		MONO_IOS_VALIDATE (((const uint8_t *)blocks [0]) [index] == 0, "reused allocation was not fully zeroed");
	mono_ios_jit_free (blocks [0], sizes [0]);
	blocks [0] = NULL;

	sizes [0] = 16;
	sizes [1] = 32;
	sizes [2] = 48;
	sizes [3] = mono_ios_validation_pool_size - sizes [0] - sizes [1] - sizes [2];
	for (int index = 0; index < 4; ++index) {
		blocks [index] = mono_ios_jit_alloc (sizes [index]);
		MONO_IOS_VALIDATE (blocks [index] != NULL, "partitioned pool allocation failed");
		MONO_IOS_VALIDATE (mono_ios_jit_contains_code (blocks [index], sizes [index]), "partition is outside prepared code arena");
		for (int previous = 0; previous < index; ++previous)
			MONO_IOS_VALIDATE ((uintptr_t)blocks [index] + sizes [index] <= (uintptr_t)blocks [previous] || (uintptr_t)blocks [previous] + sizes [previous] <= (uintptr_t)blocks [index], "live code allocations overlap");
	}
	mono_ios_jit_free (blocks [0], sizes [0]);
	blocks [0] = NULL;
	mono_ios_jit_free (blocks [2], sizes [2]);
	blocks [2] = NULL;
	errno = 0;
	sizes [0] = 64;
	blocks [0] = mono_ios_jit_alloc (sizes [0]);
	MONO_IOS_VALIDATE (!blocks [0] && errno == ENOMEM, "fragmented free ranges incorrectly satisfied contiguous allocation");
	mono_ios_jit_free (blocks [1], sizes [1]);
	blocks [1] = NULL;
	sizes [0] = 96;
	blocks [0] = mono_ios_jit_alloc (sizes [0]);
	MONO_IOS_VALIDATE (blocks [0] != NULL, "adjacent free ranges did not coalesce");
	errno = 0;
	mono_ios_jit_free (blocks [0], 32);
	MONO_IOS_VALIDATE (errno == EINVAL, "mismatched free size was not rejected");
	mono_ios_jit_free (blocks [0], sizes [0]);
	blocks [0] = NULL;
	mono_ios_jit_free (blocks [3], sizes [3]);
	blocks [3] = NULL;
	sizes [0] = mono_ios_validation_pool_size;
	blocks [0] = mono_ios_jit_alloc (sizes [0]);
	MONO_IOS_VALIDATE (blocks [0] != NULL, "fully freed pool did not coalesce to original capacity");
	mono_ios_jit_free (blocks [0], sizes [0]);
	blocks [0] = NULL;

	sizes [0] = 64;
	blocks [0] = mono_ios_jit_alloc (sizes [0]);
	MONO_IOS_VALIDATE (blocks [0] != NULL, "native execution allocation failed");
	code = (uint8_t *)blocks [0];
	mono_ios_jit_write_memory (code, instructions, sizeof (instructions));
	mono_arch_flush_icache (code, sizeof (instructions));
	MONO_IOS_VALIDATE (mono_ios_validation_call (code) == 0x1357, "first emitted instruction execution failed");
	memcpy (unaligned + 1, &changed_instruction, sizeof (changed_instruction));
	mono_ios_jit_write_memory (code, unaligned + 1, sizeof (changed_instruction));
	mono_arch_flush_icache (code, sizeof (instructions));
	MONO_IOS_VALIDATE (mono_ios_validation_call (code) == 0x2468, "32-bit instruction rewrite after execution returned stale result");
	mono_ios_jit_write_memory (code + 8, instructions, sizeof (instructions));
	mono_ios_jit_write_memory (code + 16, thunk_instructions, sizeof (thunk_instructions));
	literal = code + 24;
	MONO_IOS_VALIDATE ((uintptr_t)literal % sizeof (uint64_t) == 0 && (uintptr_t)mono_ios_jit_write_address (literal) % sizeof (uint64_t) == 0, "native 64-bit target slot is misaligned");
	target = (uintptr_t)code;
	mono_ios_jit_write_memory (literal, &target, sizeof (target));
	mono_arch_flush_icache (code, 32);
	MONO_IOS_VALIDATE (mono_ios_validation_call (code + 16) == 0x2468, "native indirect target execution failed");
	target = (uintptr_t)(code + 8);
	memcpy (unaligned + 1, &target, sizeof (target));
	mono_ios_jit_write_memory (literal, unaligned + 1, sizeof (target));
	mono_arch_flush_icache (literal, sizeof (target));
	MONO_IOS_VALIDATE (mono_ios_validation_call (code + 16) == 0x1357, "64-bit target rewrite after execution returned stale result");

finish:
	for (int index = 0; index < 4; ++index)
		if (blocks [index])
			mono_ios_jit_free (blocks [index], sizes [index]);
	if (failure) {
		if (owns_pool)
			mono_ios_jit_cleanup ();
		fprintf (stderr, "FAIL native: %s; prepare=%d errno=%d\n", failure, prepare_error, errno);
		return 1;
	}
	printf ("PASS native: execute/rewrite32, indirect-target/rewrite64, invalid sizes, exact fit, exhaustion, fragmentation, coalescing, reuse, zeroing; 32 MiB pool retained\n");
	return 0;

#undef MONO_IOS_VALIDATE
}

#include <mono/jit/jit.h>
#include <mono/metadata/appdomain.h>
#include <mono/metadata/assembly.h>
#include <mono/metadata/class.h>
#include <mono/metadata/loader.h>
#include <mono/metadata/mono-config.h>
#include <mono/metadata/mono-gc.h>
#include <mono/metadata/object.h>
#include <mono/metadata/threads.h>
#include <mono/Scripts/mono-ios-jit.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern "C" {
typedef struct _LivenessState LivenessState;
LivenessState *mono_unity_liveness_allocate_struct (MonoClass *, unsigned int, void (*) (void **, int, void *), void *, void *(*) (void *, int, void *));
void mono_unity_liveness_calculation_from_root (MonoObject *, LivenessState *);
void mono_unity_liveness_finalize (LivenessState *);
void mono_unity_liveness_free_struct (LivenessState *);
int mono_ios_validation_native (void);
int mono_ios_validation_thunks (MonoDomain *, MonoClass *);
}

static MonoMethod *
checked_method (MonoClass *checks, const char *name, int argument_count)
{
	MonoMethod *method = mono_class_get_method_from_name (checks, name, argument_count);
	void *code = method ? mono_compile_method (method) : NULL;
	MonoJitInfo *info = code ? mono_jit_info_table_find (mono_domain_get (), code) : NULL;
	int size = info ? mono_jit_info_get_code_size (info) : 0;
	if (!method || !code || !info || mono_jit_info_get_method (info) != method || size <= 0 ||
	    mono_jit_info_get_code_start (info) != code || !mono_ios_jit_contains_code (code, (size_t)size)) {
		fprintf (stderr, "FAIL method JIT identity: %s\n", name);
		return NULL;
	}
	return method;
}

static int
invoke_integer (MonoMethod *method, void **arguments, int expected, const char *name)
{
	MonoObject *exception = NULL;
	MonoObject *result = mono_runtime_invoke (method, NULL, arguments, &exception);
	if (exception) {
		fprintf (stderr, "FAIL %s: managed exception %s\n", name, mono_class_get_name (mono_object_get_class (exception)));
		return 0;
	}
	if (!result || mono_object_get_class (result) != mono_get_int32_class () || *(int32_t *)mono_object_unbox (result) != expected) {
		fprintf (stderr, "FAIL %s: unexpected return value\n", name);
		return 0;
	}
	return 1;
}

static int
invoke_native_callback (void *address, int value)
{
	if (!address || !mono_ios_jit_contains_code (address, sizeof (uint32_t)))
		return -1;
	return ((int (*) (int))address) (value);
}

static int
thunk_native (int value)
{
	return value * 3 + 1;
}

static int
managed_checks (MonoClass *checks)
{
	int passed = 1;
	int input = 10;
	void *basic_arguments [] = { &input };
	MonoMethod *basic = checked_method (checks, "Basic", 1);
	if (!basic || !invoke_integer (basic, basic_arguments, 42, "Basic"))
		passed = 0;
	else
		printf ("PASS managed Basic\n");
	const struct { const char *name; int expected; } cases [] = {
		{ "Generics", 37 }, { "DynamicMethods", 42 },
		{ "Delegates", 37 }, { "ReverseCallback", 38 }, { "Exceptions", 42 }, { "Thunks", 268 }, { "NativeThunks", 268 }
	};
	for (size_t i = 0; i < sizeof (cases) / sizeof (cases [0]); ++i) {
		MonoMethod *method = checked_method (checks, cases [i].name, 0);
		if (!method || !invoke_integer (method, NULL, cases [i].expected, cases [i].name))
			passed = 0;
		else
			printf ("PASS managed %s\n", cases [i].name);
	}
	MonoMethod *throws = checked_method (checks, "ThrowExpected", 0);
	if (!throws)
		return 0;
	MonoObject *exception = NULL;
	mono_runtime_invoke (throws, NULL, NULL, &exception);
	if (!exception || strcmp (mono_class_get_name (mono_object_get_class (exception)), "InvalidOperationException") != 0) {
		fprintf (stderr, "FAIL native exception capture\n");
		return 0;
	}
	printf ("PASS native exception capture\n");
	return passed;
}

struct ThreadRun {
	MonoDomain *domain;
	MonoMethod *method;
	pthread_mutex_t mutex;
	pthread_cond_t condition;
	int ready;
	int start;
};

struct ThreadCall {
	ThreadRun *run;
	int seed;
	int passed;
};

static void
thread_result (int result, const char *operation)
{
	if (result) {
		fprintf (stderr, "FAIL %s: pthread error %d\n", operation, result);
		abort ();
	}
}

static void *
thread_checks (void *argument)
{
	ThreadCall *call = (ThreadCall *)argument;
	MonoThread *thread = mono_thread_attach (call->run->domain);
	thread_result (pthread_mutex_lock (&call->run->mutex), "worker mutex lock");
	++call->run->ready;
	thread_result (pthread_cond_broadcast (&call->run->condition), "worker ready broadcast");
	while (!call->run->start)
		thread_result (pthread_cond_wait (&call->run->condition, &call->run->mutex), "worker start wait");
	thread_result (pthread_mutex_unlock (&call->run->mutex), "worker mutex unlock");
	if (thread) {
		void *arguments [] = { &call->seed };
		call->passed = invoke_integer (call->run->method, arguments, 32 * call->seed + 496, "attached pthread allocation/collection");
		mono_thread_detach (thread);
	}
	return NULL;
}

static int
attached_threads (MonoDomain *domain, MonoClass *checks)
{
	MonoMethod *method = checked_method (checks, "ThreadWork", 1);
	if (!method)
		return 0;
	ThreadRun run = { domain, method, PTHREAD_MUTEX_INITIALIZER, PTHREAD_COND_INITIALIZER, 0, 0 };
	ThreadCall calls [2] = { { &run, 11, 0 }, { &run, 19, 0 } };
	pthread_t threads [2];
	int created = 0;
	int generation = mono_gc_max_generation ();
	int collections = mono_gc_collection_count (generation);
	while (created < 2) {
		if (pthread_create (&threads [created], NULL, thread_checks, &calls [created]) != 0)
			break;
		++created;
	}
	thread_result (pthread_mutex_lock (&run.mutex), "main mutex lock");
	while (run.ready != created)
		thread_result (pthread_cond_wait (&run.condition, &run.mutex), "main ready wait");
	run.start = 1;
	thread_result (pthread_cond_broadcast (&run.condition), "main start broadcast");
	thread_result (pthread_mutex_unlock (&run.mutex), "main mutex unlock");
	for (int i = 0; i < created; ++i)
		thread_result (pthread_join (threads [i], NULL), "worker join");
	thread_result (pthread_cond_destroy (&run.condition), "condition destroy");
	thread_result (pthread_mutex_destroy (&run.mutex), "mutex destroy");
	if (created != 2 || !calls [0].passed || !calls [1].passed || generation < 1 || mono_gc_collection_count (generation) <= collections) {
		fprintf (stderr, "FAIL SGen attached-thread collection\n");
		return 0;
	}
	printf ("PASS SGen attached-thread allocation, roots, collection and detach\n");
	return 1;
}

struct LivenessProbe {
	MonoObject *expected [4];
	unsigned int seen;
	int invalid;
	int blocks_used;
	union Block { void *alignment; unsigned char bytes [8192]; } blocks [2];
};

static void *
liveness_allocate (void *previous, int size, void *argument)
{
	LivenessProbe *probe = (LivenessProbe *)argument;
	if (!size)
		return NULL;
	if (previous || size != 8192 || probe->blocks_used == 2)
		__builtin_trap ();
	return probe->blocks [probe->blocks_used++].bytes;
}

static void
liveness_objects (void **objects, int count, void *argument)
{
	LivenessProbe *probe = (LivenessProbe *)argument;
	for (int i = 0; i < count; ++i) {
		int index = 0;
		while (index < 3 && objects [i] != probe->expected [index])
			++index;
		if (index == 3 || (probe->seen & (1u << index)))
			probe->invalid = 1;
		else
			probe->seen |= 1u << index;
	}
}

static int
liveness_checks (MonoImage *image, MonoClass *checks)
{
	MonoMethod *create = checked_method (checks, "CreateGraph", 0);
	MonoMethod *check = checked_method (checks, "CheckGraph", 1);
	MonoClass *node = mono_class_from_name (image, "MonoIosValidation", "Node");
	if (!create || !check || !node)
		return 0;
	MonoObject *exception = NULL;
	MonoObject *graph = mono_runtime_invoke (create, NULL, NULL, &exception);
	if (!graph || exception) {
		fprintf (stderr, "FAIL liveness graph creation\n");
		return 0;
	}
	uint32_t handle = mono_gchandle_new (graph, 1);
	mono_gc_collect (mono_gc_max_generation ());
	LivenessProbe probe = {};
	LivenessState *state = mono_unity_liveness_allocate_struct (node, 4, liveness_objects, &probe, liveness_allocate);
	if (!state) {
		mono_gchandle_free (handle);
		fprintf (stderr, "FAIL liveness state creation\n");
		return 0;
	}
	MonoArray *values = (MonoArray *)mono_gchandle_get_target (handle);
	int shape_ok = values && mono_array_length (values) == 4;
	if (shape_ok) {
		mono_gc_stop_world ();
		for (int i = 0; i < 4; ++i)
			probe.expected [i] = *(MonoObject **)mono_array_addr_with_size (values, sizeof (MonoObject *), (uintptr_t)i);
		mono_unity_liveness_calculation_from_root (probe.expected [0], state);
		mono_unity_liveness_finalize (state);
		mono_gc_restart_world ();
	}
	mono_unity_liveness_free_struct (state);
	mono_gc_collect (mono_gc_max_generation ());
	graph = mono_gchandle_get_target (handle);
	void *arguments [] = { graph };
	int passed = shape_ok && !probe.invalid && probe.seen == 7 && invoke_integer (check, arguments, 110, "graph after liveness and GC");
	mono_gchandle_free (handle);
	if (!passed) {
		fprintf (stderr, "FAIL Unity liveness roots, recursion, deduplication or mark cleanup\n");
		return 0;
	}
	printf ("PASS Unity liveness cycle, unrelated-node exclusion, mark cleanup and GC\n");
	return 1;
}

extern "C" int
mono_ios_validation_run (const char *managed_directory, const char *config_directory, const char *validation_assembly_path)
{
	static int invoked;
	if (!managed_directory || !config_directory || !validation_assembly_path) {
		fprintf (stderr, "FAIL validation paths must be supplied\n");
		return 1;
	}
	if (mono_get_root_domain () || __atomic_exchange_n (&invoked, 1, __ATOMIC_ACQ_REL)) {
		fprintf (stderr, "FAIL validation requires one invocation in a fresh process before Unity or Mono startup\n");
		return 1;
	}
	printf ("runtime-patch-sha256=%s\n", MONO_IOS_VALIDATION_PATCH_SHA256);
	if (mono_ios_validation_native () != 0) {
		fprintf (stderr, "FAIL native code-pool validation; Mono was not initialized\n");
		return 1;
	}
	mono_set_dirs (managed_directory, config_directory);
	mono_set_assemblies_path (managed_directory);
	mono_config_parse (NULL);
	MonoDomain *domain = mono_jit_init_version ("mono-ios-validation", "v4.0.30319");
	if (!domain) {
		fprintf (stderr, "FAIL Mono initialization\n");
		mono_ios_jit_cleanup ();
		return 1;
	}
	mono_add_internal_call ("MonoIosValidation.Checks::InvokeNativeCallback", (const void *)invoke_native_callback);
	mono_add_internal_call ("MonoIosValidation.Checks::ThunkNative", (const void *)thunk_native);
	MonoAssembly *assembly = mono_domain_assembly_open (domain, validation_assembly_path);
	MonoImage *image = assembly ? mono_assembly_get_image (assembly) : NULL;
	MonoClass *checks = image ? mono_class_from_name (image, "MonoIosValidation", "Checks") : NULL;
	int passed = 0;
	if (checks) {
		printf ("PASS managed DLL loading\n");
		int managed_passed = managed_checks (checks);
		int threads_passed = attached_threads (domain, checks);
		int liveness_passed = liveness_checks (image, checks);
		int thunks_passed = mono_ios_validation_thunks (domain, checks) == 0;
		passed = managed_passed && threads_passed && liveness_passed && thunks_passed;
	} else {
		fprintf (stderr, "FAIL managed DLL loading or validation class lookup\n");
	}
	mono_jit_cleanup (domain);
	printf ("%s iOS Mono diagnostic validation\n", passed ? "PASS" : "FAIL");
	return passed ? 0 : 1;
}
''',
    "mono-ios-validation-thunks.c": r'''#include <config.h>
#include <mono/metadata/domain-internals.h>
#include <mono/metadata/class.h>
#include <mono/metadata/loader.h>
#include <mono/metadata/object.h>
#include <mono/Scripts/mono-ios-jit.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const size_t mono_ios_validation_thunk_size = 16;
static const size_t mono_ios_validation_target_offset = 8;
static const uint32_t mono_ios_validation_ldr_x16_literal = 0x58000050u;
static const uint32_t mono_ios_validation_br_x16 = 0xd61f0200u;

typedef struct {
	unsigned method_count;
	unsigned slot_count;
	unsigned live_slot_count;
	int failed;
} MonoIosThunkValidation;

static void
mono_ios_validation_inspect_thunks (MonoDomain *domain, MonoMethod *method, MonoJitInfo *jinfo, void *user_data)
{
	MonoIosThunkValidation *validation = user_data;
	MonoThunkJitInfo *thunks;
	uintptr_t code;
	uintptr_t start;
	const char *name;
	size_t size;
	(void)domain;
	if (validation->failed || !jinfo || jinfo->is_trampoline || jinfo->from_aot || jinfo->is_interp || !jinfo->has_thunk_info)
		return;
	name = method ? mono_method_get_name (method) : "<unknown>";
	thunks = mono_jit_info_get_thunk_info (jinfo);
	code = (uintptr_t)mono_jit_info_get_code_start (jinfo);
	if (!thunks || thunks->thunks_offset < jinfo->code_size || thunks->thunks_size <= 0 || thunks->thunks_size % mono_ios_validation_thunk_size || (uintptr_t)thunks->thunks_offset > UINTPTR_MAX - code) {
		fprintf (stderr, "FAIL thunks: invalid metadata for %s; code_size=%d\n", name, jinfo->code_size);
		validation->failed = 1;
		return;
	}
	start = code + (uintptr_t)thunks->thunks_offset;
	size = (size_t)thunks->thunks_size;
	if (!mono_ios_jit_contains_code ((void *)start, size)) {
		fprintf (stderr, "FAIL thunks: %s thunk range lies outside prepared arena; offset=%d size=%d\n", name, thunks->thunks_offset, thunks->thunks_size);
		validation->failed = 1;
		return;
	}
	++validation->method_count;
	for (size_t offset = 0; offset < size; offset += mono_ios_validation_thunk_size) {
		uint32_t instructions [2];
		uint64_t target;
		void *literal = (void *)(start + offset + mono_ios_validation_target_offset);
		void *writable = mono_ios_jit_write_address (literal);
		++validation->slot_count;
		if ((uintptr_t)literal % sizeof (target) || (uintptr_t)writable % sizeof (target) || writable == literal) {
			fprintf (stderr, "FAIL thunks: %s target slot is misaligned or lacks writable alias; code_size=%d thunk_offset=%d slot_offset=%zu RX=%p RW=%p\n", name, jinfo->code_size, thunks->thunks_offset, offset, literal, writable);
			validation->failed = 1;
			return;
		}
		memcpy (instructions, (void *)(start + offset), sizeof (instructions));
		if (!instructions [0])
			continue;
		memcpy (&target, literal, sizeof (target));
		if (instructions [0] != mono_ios_validation_ldr_x16_literal || instructions [1] != mono_ios_validation_br_x16 || !target) {
			fprintf (stderr, "FAIL thunks: unexpected populated ARM64 thunk for %s; slot_offset=%zu instructions=%08x,%08x target=%llx\n", name, offset, instructions [0], instructions [1], (unsigned long long)target);
			validation->failed = 1;
			return;
		}
		++validation->live_slot_count;
	}
}

int
mono_ios_validation_thunks (MonoDomain *domain, MonoClass *checks)
{
	MonoIosThunkValidation validation = { 0, 0, 0, 0 };
	unsigned parity_mask = 0;
	unsigned caller_count = 0;
	const char *prefixes [2] = { "ThunkCaller", "NativeThunkCaller" };
	for (unsigned family = 0; family < 2; ++family) {
		for (unsigned index = 0; index < 8; ++index) {
			char name [32];
			MonoMethod *method;
			MonoJitInfo *jinfo;
			void *compiled;
			int code_size;
			snprintf (name, sizeof (name), "%s%u", prefixes [family], index);
			method = mono_class_get_method_from_name (checks, name, 1);
			compiled = method ? mono_compile_method (method) : NULL;
			jinfo = compiled ? mono_jit_info_table_find (domain, compiled) : NULL;
			if (!jinfo || jinfo->from_aot || jinfo->is_interp || jinfo->is_trampoline || mono_jit_info_get_method (jinfo) != method) {
				fprintf (stderr, "FAIL thunks: %s has no matching native JIT body\n", name);
				return 1;
			}
			code_size = mono_jit_info_get_code_size (jinfo);
			if (code_size <= 0 || code_size % 4 || !mono_ios_jit_contains_code (mono_jit_info_get_code_start (jinfo), (size_t)code_size)) {
				fprintf (stderr, "FAIL thunks: %s has invalid native code range; code_size=%d\n", name, code_size);
				return 1;
			}
			parity_mask |= 1u << ((unsigned)code_size % 8 / 4);
			++caller_count;
		}
	}
	mono_domain_jit_foreach (domain, mono_ios_validation_inspect_thunks, &validation);
	if (validation.failed)
		return 1;
	if (parity_mask != 3 || !validation.live_slot_count) {
		fprintf (stderr, "INCOMPLETE thunks: callers=%u code_length_parities=%u thunk_methods=%u reserved_slots=%u populated_slots=%u; require both 0/4 modulo 8 code lengths and populated far thunk\n", caller_count, parity_mask, validation.method_count, validation.slot_count, validation.live_slot_count);
		return 2;
	}
	printf ("PASS thunks: callers=%u both code-length parities; methods=%u reserved_slots=%u populated_slots=%u; actual RX/RW target alignment verified\n", caller_count, validation.method_count, validation.slot_count, validation.live_slot_count);
	return 0;
}''',
}


def build_patch():
    source_directory = Path(__file__).resolve().parent
    patch = PATCH
    for name in ASSET_NAMES:
        source = (source_directory / name).read_text(encoding="utf-8")
        if not source:
            raise ValueError(f"Required source file is empty: {name}")
        if not source.endswith("\n"):
            source += "\n"
        destination = f"mono/Scripts/{name}"
        patch += f"diff --git a/{destination} b/{destination}\nnew file mode 100644\n"
        patch += "".join(unified_diff(
            [], source.splitlines(keepends=True),
            fromfile="/dev/null", tofile=f"b/{destination}",
        ))
    return patch


def run_git(checkout, *arguments, patch=None):
    return subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        input=patch.encode("utf-8") if patch is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def checked_checkout(path):
    checkout = path.resolve(strict=True)
    if not checkout.is_dir():
        raise ValueError("Checkout must be a directory.")
    result = run_git(checkout, "rev-parse", "--show-toplevel")
    if result.returncode:
        raise ValueError("Checkout must be an existing Git checkout of Unity Mono.")
    git_root = Path(result.stdout.decode("utf-8").strip()).resolve(strict=True)
    if checkout != git_root:
        raise ValueError("Run from the Mono checkout root, or pass its path.")
    for name in PATCHED_PATHS:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Invalid patch destination: {name}")
        destination = checkout / relative
        if destination.resolve() != destination:
            raise ValueError(f"Patch destination uses a redirected path: {name}")
        parent = destination
        while parent != checkout:
            if parent.is_symlink():
                raise ValueError(f"Patch destination uses a symbolic link: {name}")
            parent = parent.parent
        if destination.exists() and not destination.is_file():
            raise ValueError(f"Patch destination is not a file: {name}")
    return checkout


def apply_changes(checkout, check_only, patch):
    forward = run_git(checkout, "apply", "--check", "--whitespace=nowarn", "-", patch=patch)
    if forward.returncode:
        reverse = run_git(checkout, "apply", "--reverse", "--check", "--whitespace=nowarn", "-", patch=patch)
        if reverse.returncode == 0:
            print("SGen iOS JIT and Unity liveness changes already applied.")
            return 0
        sys.stderr.write("Mono source differs from the expected base or is partially patched. No changes applied.\n")
        sys.stderr.write(forward.stderr.decode("utf-8", errors="replace"))
        return 1
    if check_only:
        print(f"Ready to update {len(PATCHED_PATHS)} files for SGen iOS JIT and Unity liveness.")
        return 0
    applied = run_git(checkout, "apply", "--whitespace=nowarn", "-", patch=patch)
    if applied.returncode:
        sys.stderr.write(applied.stderr.decode("utf-8", errors="replace"))
        return applied.returncode
    print(f"Applied SGen iOS JIT and Unity liveness changes to {checkout}.")
    print(f"Added C++ sources: {checkout / 'mono' / 'Scripts'}")
    return 0


def emit_validation(repository, patch):
    repository = repository.resolve(strict=True)
    if not repository.is_dir():
        raise ValueError("Validation repository must be an existing directory.")
    directory = repository / "mono" / "Scripts"
    for parent in (repository / "mono", directory):
        if parent.resolve() != parent or parent.is_symlink():
            raise ValueError(f"Validation destination uses a redirected path: {parent}")
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"Validation destination is not a directory: {parent}")
    sources = dict(VALIDATION_SOURCES)
    digest = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    sources["mono-ios-validation.cpp"] = (
        f'#define MONO_IOS_VALIDATION_PATCH_SHA256 "{digest}"\n'
        + sources["mono-ios-validation.cpp"]
    )
    pending = []
    for name, source in sources.items():
        destination = directory / name
        if destination.resolve() != destination or destination.is_symlink():
            raise ValueError(f"Validation destination uses a redirected path: {destination}")
        content = source.encode("utf-8")
        if destination.exists():
            if not destination.is_file() or destination.read_bytes() != content:
                raise ValueError(f"Validation source conflict; no files written: {destination}")
        else:
            pending.append((destination, content))
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for destination, content in pending:
            with destination.open("xb") as output:
                created.append(destination)
                output.write(content)
    except OSError:
        for destination in reversed(created):
            destination.unlink()
        raise
    print(f"Validation sources ready in {directory}.")
    print("Run only in a fresh diagnostic app process before Unity or Mono initialization.")
    print("Sources emitted; no compilation or device execution performed.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=f"Patch original Unity Mono {BASE_BRANCH} sources, based on {BASE_REVISION}, for ARM64 iOS SGen JIT with Unity liveness."
    )
    parser.add_argument("checkout", nargs="?", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Validate applicability without changing files.")
    action.add_argument("--emit-validation", type=Path, metavar="REPOSITORY", help="Emit opt-in device validation sources into REPOSITORY/mono/Scripts without patching Mono.")
    arguments = parser.parse_args()
    if arguments.emit_validation is not None and arguments.checkout is not None:
        parser.error("--emit-validation cannot be combined with a checkout argument.")
    try:
        patch = build_patch()
        if arguments.emit_validation is not None:
            return emit_validation(arguments.emit_validation, patch)
        checkout = checked_checkout(arguments.checkout or Path.cwd())
        return apply_changes(checkout, arguments.check, patch)
    except (OSError, ValueError, UnicodeError) as error:
        sys.stderr.write(f"Cannot prepare Mono: {error}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
