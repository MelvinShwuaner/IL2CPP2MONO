from pathlib import Path
import shutil
import subprocess
import sys

# Whoever wrote this must've been smoking some hot shit ngl
# :wbstupid:

PATCH = r"""diff --git a/configure.ac b/configure.ac
--- a/configure.ac
+++ b/configure.ac
@@ -5083,6 +5083,12 @@
 
 AM_CONDITIONAL(TARGET_OSX, test x$target_osx = xyes)
 
+AC_ARG_ENABLE(ios-jit, [  --enable-ios-jit          Enable the ARM64 iOS JIT code pool], [], [enable_ios_jit=no])
+if test "x$enable_ios_jit" = "xyes"; then
+	AC_DEFINE(ENABLE_IOS_JIT, 1, [Enable the ARM64 iOS JIT code pool])
+fi
+AM_CONDITIONAL(ENABLE_IOS_JIT, test x$enable_ios_jit = xyes)
+
 AC_SUBST(SIZEOF_VOID_P,[$ac_cv_sizeof_void_p])
 
 if test "x$target_byte_order" = "xG_BIG_ENDIAN"; then
diff --git a/mono/arch/arm64/arm64-codegen.h b/mono/arch/arm64/arm64-codegen.h
--- a/mono/arch/arm64/arm64-codegen.h
+++ b/mono/arch/arm64/arm64-codegen.h
@@ -12,6 +12,10 @@
 #define __ARM64_CODEGEN_H__
 
 #include <glib.h>
+
+#ifdef ENABLE_IOS_JIT
+#include <mono/utils/mono-codeman.h>
+#endif
 
 enum {
 	ARMREG_R0 = 0,
@@ -123,13 +127,22 @@
 	ARMSIZE_X = 0x3
 } ARMSize;
 
+#ifdef ENABLE_IOS_JIT
+#define arm_emit(p, ins) do { guint32 _arm_instruction = (ins); mono_codeman_write_memory ((p), &_arm_instruction, sizeof (_arm_instruction)); (p) += 4; } while (0)
+#else
 #define arm_emit(p, ins) do { *(guint32*)(p) = (ins); (p) += 4; } while (0)
+#endif
 
 /* Overwrite bits [offset,offset+nbits] with value */
 static G_GNUC_UNUSED inline void
 arm_set_ins_bits (void *p, int offset, int nbits, guint32 value)
 {
+#ifdef ENABLE_IOS_JIT
+	guint32 instruction = (*(guint32*)p & ~(((1 << nbits) - 1) << offset)) | (value << offset);
+	mono_codeman_write_memory (p, &instruction, sizeof (instruction));
+#else
 	*(guint32*)p = (*(guint32*)p & ~(((1 << nbits) - 1) << offset)) | (value << offset);
+#endif
 }
 
 /*
diff --git a/mono/metadata/Makefile.am b/mono/metadata/Makefile.am
--- a/mono/metadata/Makefile.am
+++ b/mono/metadata/Makefile.am
@@ -476,6 +476,9 @@
 libmonoruntime_la_LIBADD = libmonoruntime-config.la $(culture_libraries) $(support_libraries) $(shim_libraries)
 
 libmonoruntimesgen_la_SOURCES = $(common_sources) $(icall_tables_sources) $(ilgen_sources) $(gc_dependent_sources) $(sgen_sources)
+if ENABLE_IOS_JIT
+libmonoruntimesgen_la_SOURCES += $(unity_gc_dependent_sources)
+endif
 # Add CXX_ADD_CFLAGS per-library until/unless https://github.com/dotnet/corefx/pull/31342.
 libmonoruntimesgen_la_CFLAGS = $(SGEN_DEFINES) $(GLOBALIZATION_SHIM_DEFINES) @CXX_ADD_CFLAGS@
 libmonoruntimesgen_la_LIBADD = libmonoruntime-config.la $(culture_libraries) $(support_libraries) $(shim_libraries)
diff --git a/mono/metadata/icall-signatures.h b/mono/metadata/icall-signatures.h
--- a/mono/metadata/icall-signatures.h
+++ b/mono/metadata/icall-signatures.h
@@ -57,7 +57,6 @@
 // mono_icall_sig_void_int32
 // mono_icall_sig_void_object
 // mono_icall_sig_void_ptr
-// mono_icall_sig_bool_ptr_ptrref
 // mono_icall_sig_double_double_double
 // mono_icall_sig_float_float_float
 // mono_icall_sig_int_obj_ptr
@@ -94,7 +93,6 @@
 // mono_icall_sig_void_ptr_ptr
 // mono_icall_sig_void_ptr_ptrref
 // mono_icall_sig_void_uint32_ptrref
-// mono_icall_sig_bool_ptr_int32_ptrref
 // mono_icall_sig_int32_int32_ptr_ptrref
 // mono_icall_sig_int32_ptr_int32_ptr
 // mono_icall_sig_int32_ptr_int32_ptrref
@@ -182,7 +180,7 @@
 ICALL_SIG (2, (void, int32))			\
 ICALL_SIG (2, (void, object))			\
 ICALL_SIG (2, (void, ptr))			\
-ICALL_SIG (3, (bool, ptr, ptrref))		\
+ICALL_SIG (3, (boolean, ptr, ptrref))		\
 ICALL_SIG (3, (double, double, double))		\
 ICALL_SIG (3, (float, float, float))		\
 ICALL_SIG (3, (int, obj, ptr))			\
@@ -220,7 +218,7 @@
 ICALL_SIG (3, (void, ptr, ptr))			\
 ICALL_SIG (3, (void, ptr, ptrref))		\
 ICALL_SIG (3, (void, uint32, ptrref))		\
-ICALL_SIG (4, (bool, ptr, int32, ptrref))	\
+ICALL_SIG (4, (boolean, ptr, int32, ptrref))	\
 ICALL_SIG (4, (int32, int32, ptr, ptrref))	\
 ICALL_SIG (4, (int32, ptr, int32, ptr))		\
 ICALL_SIG (4, (int32, ptr, int32, ptrref))	\
diff --git a/mono/metadata/mono-gc.h b/mono/metadata/mono-gc.h
--- a/mono/metadata/mono-gc.h
+++ b/mono/metadata/mono-gc.h
@@ -135,8 +135,8 @@
 /*
  * Only supported under SGen. These two with Sgen will take and release the LOCK_GC
  */
-void mono_gc_stop_world (void);
-void mono_gc_restart_world (void);
+MONO_API void mono_gc_stop_world (void);
+MONO_API void mono_gc_restart_world (void);
 
 MONO_END_DECLS
 
diff --git a/mono/metadata/sgen-mono.c b/mono/metadata/sgen-mono.c
--- a/mono/metadata/sgen-mono.c
+++ b/mono/metadata/sgen-mono.c
@@ -845,6 +845,9 @@
 {
 	LOCK_GC;
 	sgen_stop_world (0, FALSE);
+#ifdef ENABLE_IOS_JIT
+	sgen_finish_concurrent_work ("liveness", FALSE);
+#endif
 }
 
 void
diff --git a/mono/metadata/unity-liveness.c b/mono/metadata/unity-liveness.c
--- a/mono/metadata/unity-liveness.c
+++ b/mono/metadata/unity-liveness.c
@@ -347,7 +347,9 @@
 	MonoClass *p;
 	gboolean added_objects = FALSE;
 
+#ifndef DISABLE_REMOTING
 	if (!isStruct && mono_class_has_parent_fast(klass, mono_defaults.real_proxy_class)) return FALSE;
+#endif
 
 	g_assert(object);
 
@@ -400,7 +402,9 @@
 	MonoClass* p;
 	gboolean added_objects = FALSE;
 
+#ifndef DISABLE_REMOTING
 	if (!isStruct && mono_class_has_parent_fast(klass, mono_defaults.real_proxy_class)) return FALSE;
+#endif
 
 	g_assert(object);
 
diff --git a/mono/mini/aot-compiler.c b/mono/mini/aot-compiler.c
--- a/mono/mini/aot-compiler.c
+++ b/mono/mini/aot-compiler.c
@@ -13740,8 +13740,8 @@
 
 #ifndef MONO_ARCH_HAVE_INTERP_ENTRY_TRAMPOLINE
 static MonoMethodSignature * const * const interp_in_static_sigs [] = {
-    &mono_icall_sig_bool_ptr_int32_ptrref,
-    &mono_icall_sig_bool_ptr_ptrref,
+    &mono_icall_sig_boolean_ptr_int32_ptrref,
+    &mono_icall_sig_boolean_ptr_ptrref,
     &mono_icall_sig_int32_int32_ptrref,
     &mono_icall_sig_int32_int32_ptr_ptrref,
     &mono_icall_sig_int32_ptr_int32_ptr,
diff --git a/mono/mini/debugger-agent.c b/mono/mini/debugger-agent.c
--- a/mono/mini/debugger-agent.c
+++ b/mono/mini/debugger-agent.c
@@ -1855,8 +1855,9 @@
 }
 
 static void
-buffer_add_byte (Buffer *buf, guint8 val)
-{
+buffer_add_byte (void *buffer, guint8 val)
+{
+	Buffer *buf = (Buffer *)buffer;
 	buffer_make_room (buf, 1);
 	buf->p [0] = val;
 	buf->p++;
@@ -1872,8 +1873,9 @@
 }
 
 static void
-buffer_add_int (Buffer *buf, guint32 val)
-{
+buffer_add_int (void *buffer, guint32 val)
+{
+	Buffer *buf = (Buffer *)buffer;
 	buffer_make_room (buf, 4);
 	buf->p [0] = (val >> 24) & 0xff;
 	buf->p [1] = (val >> 16) & 0xff;
@@ -1890,8 +1892,9 @@
 }
 
 static void
-buffer_add_id (Buffer *buf, int id)
-{
+buffer_add_id (void *buffer, int id)
+{
+	Buffer *buf = (Buffer *)buffer;
 	buffer_add_int (buf, (guint64)id);
 }
 
@@ -1919,8 +1922,9 @@
 }
 
 static void
-buffer_add_string (Buffer *buf, const char *str)
-{
+buffer_add_string (void *buffer, const char *str)
+{
+	Buffer *buf = (Buffer *)buffer;
 	int len;
 
 	if (str == NULL) {
diff --git a/mono/mini/driver.c b/mono/mini/driver.c
--- a/mono/mini/driver.c
+++ b/mono/mini/driver.c
@@ -2936,6 +2936,13 @@
 MonoDomain * 
 mono_jit_init_version (const char *domain_name, const char *runtime_version)
 {
+#ifdef ENABLE_IOS_JIT
+	int error = mono_ios_jit_prepare (0);
+	if (error) {
+		fprintf (stderr, "iOS JIT preparation failed: %s (%d). Check preceding Mono preparation mode/stage logs and MONO_IOS_JIT_POOL_MB before starting Mono.\n", g_strerror (error), error);
+		return NULL;
+	}
+#endif
 	MonoDomain *ret = mini_init (domain_name, runtime_version);
 	MONO_ENTER_GC_SAFE_UNBALANCED; //once it is not executing any managed code yet, it's safe to run the gc
 	return ret;
diff --git a/mono/mini/jit.h b/mono/mini/jit.h
--- a/mono/mini/jit.h
+++ b/mono/mini/jit.h
@@ -12,6 +12,12 @@
 #include <mono/metadata/appdomain.h>
 
 MONO_BEGIN_DECLS
+
+MONO_API int
+mono_ios_jit_prepare       (size_t capacity);
+
+MONO_API mono_bool
+mono_ios_jit_contains_code (const void *address, size_t size);
 
 MONO_API MONO_RT_EXTERNAL_ONLY MonoDomain * 
 mono_jit_init              (const char *file);
diff --git a/mono/mini/mini-arm64.c b/mono/mini/mini-arm64.c
--- a/mono/mini/mini-arm64.c
+++ b/mono/mini/mini-arm64.c
@@ -846,7 +846,11 @@
 
 	arm_ldrx_lit (code, ARMREG_IP0, code + 8);
 	arm_brx (code, ARMREG_IP0);
-	*(guint64*)code = (guint64)target;
+#ifdef ENABLE_IOS_JIT
+	g_assert ((gsize)code % sizeof (guint64) == 0);
+#endif
+	guint64 thunk_target = (guint64)target;
+	mono_codeman_write_memory (code, &thunk_target, sizeof (thunk_target));
 	code += sizeof (guint64);
 
 	mono_arch_flush_icache (p, code - p);
@@ -2046,6 +2050,9 @@
 #if __APPLE__
 G_BEGIN_DECLS
 void sys_icache_invalidate (void *start, size_t len);
+#ifdef ENABLE_IOS_JIT
+void sys_dcache_flush (void *start, size_t len);
+#endif
 G_END_DECLS
 #endif
 
@@ -2054,6 +2061,9 @@
 {
 #ifndef MONO_CROSS_COMPILE
 #if __APPLE__
+#ifdef ENABLE_IOS_JIT
+	sys_dcache_flush (mono_codeman_write_address (code), size);
+#endif
 	sys_icache_invalidate (code, size);
 #else
 	/* Don't rely on GCC's __clear_cache implementation, as it caches
diff --git a/mono/mini/mini-runtime.c b/mono/mini/mini-runtime.c
--- a/mono/mini/mini-runtime.c
+++ b/mono/mini/mini-runtime.c
@@ -1485,7 +1485,8 @@
 
 		mono_codeman_enable_write ();
 		for (i = 0; i < patch_info->data.table->table_size; i++) {
-			jump_table [i] = code + GPOINTER_TO_INT (patch_info->data.table->table [i]);
+			gpointer jump_target = code + GPOINTER_TO_INT (patch_info->data.table->table [i]);
+			mono_codeman_write_memory (&jump_table [i], &jump_target, sizeof (jump_target));
 		}
 		mono_codeman_disable_write ();
 
diff --git a/mono/mini/mini.c b/mono/mini/mini.c
--- a/mono/mini/mini.c
+++ b/mono/mini/mini.c
@@ -2116,13 +2116,15 @@
 			}
 
 			for (i = 0; i < patch_info->data.table->table_size; i++) {
+				gpointer target;
 				/* Might be NULL if the switch is eliminated */
 				if (patch_info->data.table->table [i]) {
 					g_assert (patch_info->data.table->table [i]->native_offset);
-					table [i] = GINT_TO_POINTER (patch_info->data.table->table [i]->native_offset);
+					target = GINT_TO_POINTER (patch_info->data.table->table [i]->native_offset);
 				} else {
-					table [i] = NULL;
+					target = NULL;
 				}
+				mono_codeman_write_memory (&table [i], &target, sizeof (target));
 			}
 			patch_info->data.table->table = (MonoBasicBlock**)table;
 			break;
@@ -2237,6 +2239,11 @@
 		unwindlen = mono_arch_unwindinfo_init_method_unwind_info (cfg);
 #endif
 
+#ifdef ENABLE_IOS_JIT
+	if (cfg->thunk_area)
+		cfg->code_size += (sizeof (guint64) - (cfg->code_size + unwindlen) % sizeof (guint64)) % sizeof (guint64);
+#endif
+
 	if (cfg->method->dynamic) {
 		/* Allocate the code into a separate memory pool so it can be freed */
 		cfg->dynamic_info = g_new0 (MonoJitDynamicMethodInfo, 1);
@@ -2259,11 +2266,11 @@
 	if (cfg->thunk_area) {
 		cfg->thunks_offset = cfg->code_size + unwindlen;
 		cfg->thunks = code + cfg->thunks_offset;
-		memset (cfg->thunks, 0, cfg->thunk_area);
+		mono_codeman_set_memory (cfg->thunks, 0, cfg->thunk_area);
 	}
 
 	g_assert (code);
-	memcpy (code, cfg->native_code, cfg->code_len);
+	mono_codeman_write_memory (code, cfg->native_code, cfg->code_len);
 	g_free (cfg->native_code);
 	cfg->native_code = code;
 	code = cfg->native_code + cfg->code_len;
diff --git a/mono/mini/tramp-arm64.c b/mono/mini/tramp-arm64.c
--- a/mono/mini/tramp-arm64.c
+++ b/mono/mini/tramp-arm64.c
@@ -27,7 +27,11 @@
 #endif
 #include "mono/utils/mono-tls-inline.h"
 
+#ifdef ENABLE_IOS_JIT
+#define JUMP_TRAMP_PATCH_OFFSET (8 * 4)
+#else
 #define JUMP_TRAMP_PATCH_OFFSET (7 * 4)
+#endif
 
 void
 mono_arch_patch_callsite (guint8 *method_start, guint8 *code_ptr, guint8 *addr)
@@ -42,7 +46,10 @@
 {
 	MINI_BEGIN_CODEGEN();
 	guint8* patch_addr = jump_tramp + JUMP_TRAMP_PATCH_OFFSET;
-	*(gpointer*)patch_addr = addr;
+#ifdef ENABLE_IOS_JIT
+	g_assert ((gsize)patch_addr % sizeof (guint64) == 0);
+#endif
+	mono_codeman_write_memory (patch_addr, &addr, sizeof (addr));
 	MINI_END_CODEGEN(patch_addr, 8, -1, NULL);
 }
 
@@ -354,11 +361,19 @@
 		arm_movkx(code, ARMREG_IP1, (imm >> 32) & 0xffff, 32);
 		arm_movkx(code, ARMREG_IP1, (imm >> 48) & 0xffff, 48);
 
-		arm_adrx(code, ARMREG_IP0, code + (3 * 4));
+		arm_adrx(code, ARMREG_IP0, buf + JUMP_TRAMP_PATCH_OFFSET);
 		arm_ldrx(code, ARMREG_IP0, ARMREG_IP0, 0);
 		code = mono_arm_emit_brx(code, ARMREG_IP0);
+#ifdef ENABLE_IOS_JIT
+		arm_nop (code);
+		g_assert ((gsize)code % sizeof (guint64) == 0);
+#endif
 		g_assert(code - buf == JUMP_TRAMP_PATCH_OFFSET);
-		*(guint64*)code = (guint64)(gsize)tramp;
+		guint64 trampoline_target = (guint64)(gsize)tramp;
+		mono_codeman_write_memory (code, &trampoline_target, sizeof (trampoline_target));
+#ifdef ENABLE_IOS_JIT
+		code += sizeof (guint64);
+#endif
 	}
 	else {
 		code = mono_arm_emit_imm64(code, ARMREG_IP1, (guint64)arg1);
diff --git a/mono/utils/Makefile.am b/mono/utils/Makefile.am
--- a/mono/utils/Makefile.am
+++ b/mono/utils/Makefile.am
@@ -325,6 +325,11 @@
 libmonoutils_la_CFLAGS = $(JEMALLOC_CFLAGS) @CXX_ADD_CFLAGS@
 libmonoutils_la_LDFLAGS = $(JEMALLOC_LDFLAGS)
 
+if ENABLE_IOS_JIT
+libmonoutils_la_SOURCES += ../Scripts/mono-ios-jit.cpp ../Scripts/mono-ios-jit.h
+libmonoutils_la_CXXFLAGS = $(JEMALLOC_CFLAGS) $(CXXFLAGS_COMMON)
+endif
+
 endif # !ENABLE_MSVC_ONLY
 
 libmonoutilsincludedir = $(includedir)/mono-$(API_VER)/mono/utils
diff --git a/mono/utils/mono-codeman.c b/mono/utils/mono-codeman.c
--- a/mono/utils/mono-codeman.c
+++ b/mono/utils/mono-codeman.c
@@ -19,6 +19,12 @@
 
 #include "mono-codeman.h"
 #include "mono-mmap.h"
+#ifdef ENABLE_IOS_JIT
+#include <errno.h>
+#include <libkern/OSCacheControl.h>
+#include <mono/Scripts/mono-ios-jit.h>
+#include "mono-mmap-internals.h"
+#endif
 #include "mono-counters.h"
 #if _WIN32
 static void* mono_code_manager_heap;
@@ -112,6 +118,23 @@
 static void*
 codechunk_valloc (void *preferred, guint32 size)
 {
+#ifdef ENABLE_IOS_JIT
+	if (!mono_valloc_can_alloc (size)) {
+		g_error ("iOS JIT code allocation of %u bytes exceeds the runtime memory limit", size);
+		return NULL;
+	}
+	void *ptr = mono_ios_jit_alloc (size);
+	if (!ptr) {
+		int allocation_error = errno;
+		if (allocation_error == EPERM)
+			g_error ("iOS JIT requires successful mono_ios_jit_prepare before Mono initialization; check preceding preparation mode/stage logs");
+		else
+			g_error ("iOS JIT code allocation of %u bytes failed: %s. Check the prepared code-pool capacity and available memory", size, g_strerror (allocation_error));
+		return NULL;
+	}
+	mono_account_mem (MONO_MEM_ACCOUNT_CODE, size);
+	return ptr;
+#else
 	void *ptr;
 	GSList *freelist;
 
@@ -139,11 +162,16 @@
 	}
 	mono_os_mutex_unlock (&valloc_mutex);
 	return ptr;
+#endif
 }
 
 static void
 codechunk_vfree (void *ptr, guint32 size)
 {
+#ifdef ENABLE_IOS_JIT
+	mono_ios_jit_free (ptr, size);
+	mono_account_mem (MONO_MEM_ACCOUNT_CODE, -(ssize_t)size);
+#else
 	GSList *freelist;
 
 	mono_os_mutex_lock (&valloc_mutex);
@@ -155,6 +183,7 @@
 		mono_vfree (ptr, size, MONO_MEM_ACCOUNT_CODE);
 	}
 	mono_os_mutex_unlock (&valloc_mutex);
+#endif
 }		
 
 static void
@@ -192,6 +221,9 @@
 mono_code_manager_cleanup (void)
 {
 	codechunk_cleanup ();
+#ifdef ENABLE_IOS_JIT
+	mono_ios_jit_cleanup ();
+#endif
 }
 
 void
@@ -204,7 +236,9 @@
 int
 mono_codeman_allocation_type (MonoCodeManager const *cman)
 {
-#ifdef FORCE_MALLOC
+#ifdef ENABLE_IOS_JIT
+	return CODE_FLAG_MMAP;
+#elif defined(FORCE_MALLOC)
 	return CODE_FLAG_MALLOC;
 #else
 	return cman->dynamic ? CODE_FLAG_MALLOC : CODE_FLAG_MMAP;
@@ -355,6 +389,16 @@
 	g_free (cman);
 }
 
+static void
+invalidate_code_chunk (CodeChunk *chunk, int fill_value)
+{
+	mono_codeman_set_memory (chunk->data, fill_value, chunk->size);
+#ifdef ENABLE_IOS_JIT
+	sys_dcache_flush (mono_codeman_write_address (chunk->data), chunk->size);
+	sys_icache_invalidate (chunk->data, chunk->size);
+#endif
+}
+
 /**
  * mono_code_manager_invalidate:
  * \param cman a code manager
@@ -374,9 +418,9 @@
 #endif
 
 	for (chunk = cman->current; chunk; chunk = chunk->next)
-		memset (chunk->data, fill_value, chunk->size);
+		invalidate_code_chunk (chunk, fill_value);
 	for (chunk = cman->full; chunk; chunk = chunk->next)
-		memset (chunk->data, fill_value, chunk->size);
+		invalidate_code_chunk (chunk, fill_value);
 }
 
 /**
@@ -502,7 +546,11 @@
 		if (flags == CODE_FLAG_MALLOC)
 			mono_codeman_free (ptr);
 		else
+#ifdef ENABLE_IOS_JIT
+			codechunk_vfree (ptr, chunk_size);
+#else
 			mono_vfree (ptr, chunk_size, MONO_MEM_ACCOUNT_CODE);
+#endif
 		return NULL;
 	}
 	chunk->next = NULL;
@@ -696,3 +744,23 @@
 	}
 #endif
 }
+
+#ifdef ENABLE_IOS_JIT
+void*
+mono_codeman_write_address (void *address)
+{
+	return mono_ios_jit_write_address (address);
+}
+
+void
+mono_codeman_write_memory (void *address, const void *source, size_t size)
+{
+	mono_ios_jit_write_memory (address, source, size);
+}
+
+void
+mono_codeman_set_memory (void *address, int value, size_t size)
+{
+	mono_ios_jit_set_memory (address, value, size);
+}
+#endif
diff --git a/mono/utils/mono-codeman.h b/mono/utils/mono-codeman.h
--- a/mono/utils/mono-codeman.h
+++ b/mono/utils/mono-codeman.h
@@ -44,5 +44,15 @@
 void mono_codeman_enable_write (void);
 void mono_codeman_disable_write (void);
 
+#ifdef ENABLE_IOS_JIT
+void *mono_codeman_write_address (void *address);
+void mono_codeman_write_memory (void *address, const void *source, size_t size);
+void mono_codeman_set_memory (void *address, int value, size_t size);
+#else
+#define mono_codeman_write_address(address) (address)
+#define mono_codeman_write_memory(address, source, size) memcpy ((address), (source), (size))
+#define mono_codeman_set_memory(address, value, size) memset ((address), (value), (size))
+#endif
+
 #endif /* __MONO_CODEMAN_H__ */
 
diff --git a/mono/utils/mono-sigcontext.h b/mono/utils/mono-sigcontext.h
--- a/mono/utils/mono-sigcontext.h
+++ b/mono/utils/mono-sigcontext.h
@@ -495,7 +495,7 @@
 
 #ifndef UCONTEXT_REG_SET_PC
 #define UCONTEXT_REG_SET_PC(ctx, val) do { \
-	UCONTEXT_REG_PC (ctx) = (val); \
+	UCONTEXT_REG_PC (ctx) = (host_mgreg_t)(val); \
 	 } while (0)
 #define UCONTEXT_REG_SET_SP(ctx, val) do { \
 	UCONTEXT_REG_SP (ctx) = (val); \
diff --git a/mono/utils/mono-threads-mach-helper.c b/mono/utils/mono-threads-mach-helper.c
--- a/mono/utils/mono-threads-mach-helper.c
+++ b/mono/utils/mono-threads-mach-helper.c
@@ -57,13 +57,7 @@
 static void
 mono_dead_letter_dealloc (id self, SEL _cmd)
 {
-	struct objc_super super;
-	super.receiver = self;
-#if !defined(__cplusplus) && !__OBJC2__
-	super.class = nsobject;
-#else
-	super.super_class = nsobject;
-#endif
+	struct objc_super super = { self, nsobject };
 	void (*objc_msgSendSuper_op)(struct objc_super *, SEL) = (void (*)(struct objc_super *, SEL)) objc_msgSendSuper;
 	objc_msgSendSuper_op (&super, dealloc);
 
diff --git a/sdks/builds/ios.mk b/sdks/builds/ios.mk
--- a/sdks/builds/ios.mk
+++ b/sdks/builds/ios.mk
@@ -123,6 +123,13 @@
 	--disable-cooperative-suspend \
 	--disable-hybrid-suspend \
 	--disable-crash-reporting
+
+ifeq ($(1),target64)
+_ios-$(1)_CONFIGURE_FLAGS := $$(filter-out --disable-icall-tables --enable-minimal=% --with-lazy-gc-thread-creation=yes,$$(_ios-$(1)_CONFIGURE_FLAGS)) \
+	--enable-minimal=ssa,com,interpreter,portability,assembly_remapping,attach,verifier,full_messages,appdomains,security,sgen_remset,sgen_marksweep_par,sgen_marksweep_fixed,sgen_marksweep_fixed_par,sgen_copying,logging,remoting,shared_perfcounters,gac \
+	--enable-ios-jit --enable-unity-define --enable-icall-tables --with-sgen=yes \
+	--disable-llvm --disable-llvm-runtime --with-bitcode=no
+endif
 
 .stamp-ios-$(1)-toolchain:
 	touch $$@
diff --git a/mono/utils/mono-log-darwin.c b/mono/utils/mono-log-darwin.c
--- a/mono/utils/mono-log-darwin.c
+++ b/mono/utils/mono-log-darwin.c
@@ -94,10 +94,17 @@
 void
 mono_log_write_asl (const char *log_domain, GLogLevelFlags level, mono_bool hdr, const char *message)
 {
+#ifdef ENABLE_IOS_JIT
+#pragma clang diagnostic push
+#pragma clang diagnostic ignored "-Wdeprecated-declarations"
+#endif
 	asl_log (NULL, NULL, to_asl_priority (level), "%s%s%s\n",
 		log_domain != NULL ? log_domain : "",
 		log_domain != NULL ? ": " : "",
 		message);
+#ifdef ENABLE_IOS_JIT
+#pragma clang diagnostic pop
+#endif
 
 	if (level & G_LOG_LEVEL_ERROR)
 		g_assert_abort ();
diff --git a/mono/metadata/w32process-unix-osx.c b/mono/metadata/w32process-unix-osx.c
--- a/mono/metadata/w32process-unix-osx.c
+++ b/mono/metadata/w32process-unix-osx.c
@@ -185,7 +185,14 @@
 {
 	#if SIZEOF_VOID_P == 8
 	const struct mach_header_64 *hdr64 = (const struct mach_header_64 *)hdr32;
+#ifdef ENABLE_IOS_JIT
+#pragma clang diagnostic push
+#pragma clang diagnostic ignored "-Wdeprecated-declarations"
+#endif
 	const struct section_64 *sec = getsectbynamefromheader_64 (hdr64, SEG_DATA, SECT_DATA);
+#ifdef ENABLE_IOS_JIT
+#pragma clang diagnostic pop
+#endif
 	#else
 	const struct section *sec = getsectbynamefromheader (hdr32, SEG_DATA, SECT_DATA);
 	#endif
diff --git a/mono/metadata/icall-decl.h b/mono/metadata/icall-decl.h
--- a/mono/metadata/icall-decl.h
+++ b/mono/metadata/icall-decl.h
@@ -71,6 +71,10 @@
 #undef HANDLES_REUSE_WRAPPER
 #undef NOHANDLES
 #undef MONO_HANDLE_REGISTER_ICALL
+
+#ifdef DISABLE_REMOTING
+ICALL_EXPORT MonoBoolean ves_icall_IsTransparentProxy (MonoObject *proxy);
+#endif
 
 // This is sorted.
 // grep ICALL_EXPORT | sort | uniq
"""

checkout = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
src_dir = Path(__file__).resolve().parent
dst_dir = checkout / "mono/Scripts"
dst_dir.mkdir(parents=True, exist_ok=True)
for name in ("mono-ios-jit.cpp", "mono-ios-jit.h"):
    if (src_dir / name).resolve() != (dst_dir / name).resolve():
        shutil.copy2(src_dir / name, dst_dir / name)

subprocess.run(
    ["git", "-C", str(checkout), "apply", "--whitespace=nowarn", "-"],
    input=PATCH,
    text=True,
    check=True,
)


# ts shit was over 1k lines once ong