#include <config.h>

#if defined(ENABLE_IOS_JIT)

#define _DARWIN_C_SOURCE

#include "mono-ios-jit.h"

#include <errno.h>
#include <libkern/OSCacheControl.h>
#include <mach/mach.h>
#include <mach/vm_region.h>
#include <os/log.h>
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <unistd.h>

#define MONO_IOS_JIT_ALIGNMENT 16
#define MONO_IOS_JIT_MEGABYTE (1024u * 1024u)
#define MONO_IOS_JIT_DEFAULT_POOL_MB 128u
#define MONO_IOS_JIT_MOVZ_W0 0x52800000u
#define MONO_IOS_JIT_RET 0xd65f03c0u

typedef struct _MonoIosJitRange MonoIosJitRange;
typedef struct _MonoIosJitArena MonoIosJitArena;
struct _MonoIosJitRange {
	size_t offset;
	size_t size;
	MonoIosJitRange *next;
};

struct _MonoIosJitArena {
	void *execute_address;
	void *write_address;
	size_t capacity;
	MonoIosJitRange *free_ranges;
	MonoIosJitRange *allocations;
	MonoIosJitArena *next;
};

static MonoIosJitArena *arena_head;
static pthread_mutex_t arena_mutex = PTHREAD_MUTEX_INITIALIZER;

extern "C" {

static MonoIosJitArena *find_arena (void *address);
static void write_arena_memory (MonoIosJitArena *arena, void *address, const void *source, size_t size, int fill_value, int is_fill);
static int round_size (size_t size, size_t alignment, size_t *rounded_size);
static int startup_capacity (size_t *capacity);
static int debugger_status (int *is_attached);
static int verify_protection (void *address, size_t size, vm_prot_t protection, const char *stage);
static int verify_arena (MonoIosJitArena *arena, size_t page_size);
static int execute_probe (void *address);
static int mach_error_number (kern_return_t result);
static int report_prepare_error (const char *stage, int error, kern_return_t native_error = KERN_SUCCESS, const char *detail = "");
static void release_arena (MonoIosJitArena *arena);
static void release_ranges (MonoIosJitRange *range);

__attribute__((noinline, optnone, naked))
static void *
prepare_region (void *address __attribute__((unused)), size_t size __attribute__((unused)))
{
	__asm__ ("mov x16, #1\n"
	         "brk #0xf00d\n"
	         "ret");
}

__attribute__((noinline, optnone, naked))
static void
detach_debugger (void)
{
	__asm__ ("mov x16, #0\n"
	         "brk #0xf00d\n"
	         "ret");
}

int
mono_ios_jit_prepare (size_t capacity)
{
	MonoIosJitArena *arena;
	vm_address_t write_address = 0;
	vm_prot_t current_protection;
	vm_prot_t maximum_protection;
	kern_return_t result;
	int error;
	int is_attached;
	int page_size = getpagesize ();
	int use_startup_pool = capacity == 0;

	if (use_startup_pool) {
		if (__atomic_load_n (&arena_head, __ATOMIC_ACQUIRE))
			return 0;
		error = startup_capacity (&capacity);
		if (error)
			return report_prepare_error ("startup capacity", error, KERN_SUCCESS, "MONO_IOS_JIT_POOL_MB must be a positive whole number that fits in size_t");
	}

	if (page_size <= 0 || !round_size (capacity, (size_t)page_size, &capacity))
		return report_prepare_error ("page-aligned capacity", EINVAL);

	arena = (MonoIosJitArena *)calloc (1, sizeof (*arena));
	if (!arena)
		return report_prepare_error ("arena allocation", ENOMEM);
	arena->free_ranges = (MonoIosJitRange *)calloc (1, sizeof (*arena->free_ranges));
	if (!arena->free_ranges) {
		free (arena);
		return report_prepare_error ("free-range allocation", ENOMEM);
	}
	arena->capacity = capacity;
	arena->free_ranges->size = capacity;

	error = pthread_mutex_lock (&arena_mutex);
	if (error) {
		release_arena (arena);
		return report_prepare_error ("arena mutex", error);
	}
	if (use_startup_pool && __atomic_load_n (&arena_head, __ATOMIC_ACQUIRE)) {
		release_arena (arena);
		pthread_mutex_unlock (&arena_mutex);
		return 0;
	}
	error = debugger_status (&is_attached);
	if (error) {
		report_prepare_error ("debugger attach check", error, KERN_SUCCESS, "sysctl process status");
		goto fail;
	}
	if (!is_attached) {
		error = report_prepare_error ("debugger attach check", EPERM, KERN_SUCCESS, "P_TRACED is unset; attach StikDebug's universal script before Mono initialization");
		goto fail;
	}

	arena->execute_address = prepare_region (NULL, capacity);
	if (!arena->execute_address) {
		error = report_prepare_error ("StikDebug prepare_region", ENOMEM, KERN_SUCCESS, "debugger protocol returned NULL");
		goto detach;
	}
	if ((uintptr_t)arena->execute_address % (size_t)page_size != 0 ||
	    (uintptr_t)arena->execute_address > UINTPTR_MAX - capacity) {
		arena->execute_address = NULL;
		error = report_prepare_error ("StikDebug prepare_region", EFAULT, KERN_SUCCESS, "unaligned or overflowing executable region");
		goto detach;
	}

	result = vm_remap (mach_task_self (), &write_address, capacity, 0,
	                   VM_FLAGS_ANYWHERE, mach_task_self (),
	                   (vm_address_t)arena->execute_address, FALSE,
	                   &current_protection, &maximum_protection, VM_INHERIT_NONE);
	if (result != KERN_SUCCESS) {
		error = report_prepare_error ("vm_remap", mach_error_number (result), result);
		goto detach;
	}
	arena->write_address = (void *)write_address;
	if (!write_address || write_address % (size_t)page_size != 0 || write_address > UINTPTR_MAX - capacity) {
		error = report_prepare_error ("vm_remap address", EFAULT);
		goto detach;
	}
	result = vm_protect (mach_task_self (), write_address, capacity, FALSE,
	                     VM_PROT_READ | VM_PROT_WRITE);
	if (result != KERN_SUCCESS) {
		error = report_prepare_error ("vm_protect", mach_error_number (result), result);
		goto detach;
	}
	error = 0;

detach:
	detach_debugger ();
	if (!error) {
		error = debugger_status (&is_attached);
		if (error)
			report_prepare_error ("debugger detach check", error, KERN_SUCCESS, "sysctl process status");
		else if (is_attached)
			error = report_prepare_error ("debugger detach check", EBUSY, KERN_SUCCESS, "P_TRACED remains set after debugger detach");
		if (!error)
			error = verify_arena (arena, (size_t)page_size);
	}
	if (!error) {
		arena->next = __atomic_load_n (&arena_head, __ATOMIC_ACQUIRE);
		__atomic_store_n (&arena_head, arena, __ATOMIC_RELEASE);
		pthread_mutex_unlock (&arena_mutex);
		return 0;
	}
fail:
	release_arena (arena);
	pthread_mutex_unlock (&arena_mutex);
	return error;
}

mono_bool
mono_ios_jit_contains_code (const void *address, size_t size)
{
	MonoIosJitArena *arena;

	if (!address || !size)
		return 0;
	for (arena = __atomic_load_n (&arena_head, __ATOMIC_ACQUIRE); arena; arena = arena->next) {
		size_t offset = (uintptr_t)address - (uintptr_t)arena->execute_address;
		if (offset < arena->capacity && size <= arena->capacity - offset)
			return 1;
	}
	return 0;
}

void *
mono_ios_jit_alloc (size_t size)
{
	MonoIosJitArena *arena;
	int error;

	if (!round_size (size, MONO_IOS_JIT_ALIGNMENT, &size)) {
		errno = EINVAL;
		return NULL;
	}
	error = pthread_mutex_lock (&arena_mutex);
	if (error) {
		errno = error;
		return NULL;
	}
	for (arena = __atomic_load_n (&arena_head, __ATOMIC_ACQUIRE); arena; arena = arena->next) {
		MonoIosJitRange **free_link;
		for (free_link = &arena->free_ranges; *free_link; free_link = &(*free_link)->next) {
			MonoIosJitRange *range = *free_link;
			MonoIosJitRange *allocation;
			void *address;

			if (range->size < size)
				continue;
			if (range->size == size) {
				allocation = range;
				*free_link = range->next;
			} else {
				allocation = (MonoIosJitRange *)malloc (sizeof (*allocation));
				if (!allocation) {
					pthread_mutex_unlock (&arena_mutex);
					errno = ENOMEM;
					return NULL;
				}
				allocation->offset = range->offset;
				allocation->size = size;
				range->offset += size;
				range->size -= size;
			}
			allocation->next = arena->allocations;
			arena->allocations = allocation;
			address = (char *)arena->execute_address + allocation->offset;
			write_arena_memory (arena, address, NULL, size, 0, 1);
			pthread_mutex_unlock (&arena_mutex);
			return address;
		}
	}
	error = __atomic_load_n (&arena_head, __ATOMIC_ACQUIRE) ? ENOMEM : EPERM;
	pthread_mutex_unlock (&arena_mutex);
	errno = error;
	return NULL;
}

void
mono_ios_jit_free (void *address, size_t size)
{
	MonoIosJitArena *arena;
	int error;

	if (!address)
		return;
	if (!round_size (size, MONO_IOS_JIT_ALIGNMENT, &size)) {
		errno = EINVAL;
		return;
	}
	error = pthread_mutex_lock (&arena_mutex);
	if (error) {
		errno = error;
		return;
	}
	for (arena = __atomic_load_n (&arena_head, __ATOMIC_ACQUIRE); arena; arena = arena->next) {
		MonoIosJitRange **allocation_link;
		size_t offset = (uintptr_t)address - (uintptr_t)arena->execute_address;

		if (offset >= arena->capacity)
			continue;
		for (allocation_link = &arena->allocations; *allocation_link; allocation_link = &(*allocation_link)->next) {
			MonoIosJitRange *allocation = *allocation_link;
			MonoIosJitRange **free_link;
			MonoIosJitRange *previous = NULL;

			if (allocation->offset != offset || allocation->size != size)
				continue;
			*allocation_link = allocation->next;
			for (free_link = &arena->free_ranges; *free_link && (*free_link)->offset < offset; free_link = &(*free_link)->next)
				previous = *free_link;
			allocation->next = *free_link;
			*free_link = allocation;
			if (allocation->next && allocation->offset + allocation->size == allocation->next->offset) {
				MonoIosJitRange *next = allocation->next;
				allocation->size += next->size;
				allocation->next = next->next;
				free (next);
			}
			if (previous && previous->offset + previous->size == allocation->offset) {
				previous->size += allocation->size;
				previous->next = allocation->next;
				free (allocation);
			}
			pthread_mutex_unlock (&arena_mutex);
			return;
		}
		break;
	}
	pthread_mutex_unlock (&arena_mutex);
	errno = EINVAL;
}

void *
mono_ios_jit_write_address (void *address)
{
	MonoIosJitArena *arena = find_arena (address);

	if (arena) {
		size_t offset = (uintptr_t)address - (uintptr_t)arena->execute_address;
		return (char *)arena->write_address + offset;
	}
	return address;
}

void
mono_ios_jit_write_memory (void *address, const void *source, size_t size)
{
	MonoIosJitArena *arena;

	if (!size)
		return;
	arena = find_arena (address);
	if (arena)
		write_arena_memory (arena, address, source, size, 0, 0);
	else
		memcpy (address, source, size);
}

void
mono_ios_jit_set_memory (void *address, int value, size_t size)
{
	MonoIosJitArena *arena;

	if (!size)
		return;
	arena = find_arena (address);
	if (arena)
		write_arena_memory (arena, address, NULL, size, value, 1);
	else
		memset (address, value, size);
}

void
mono_ios_jit_cleanup (void)
{
	MonoIosJitArena *arena;
	int error = pthread_mutex_lock (&arena_mutex);

	if (error) {
		errno = error;
		return;
	}
	arena = __atomic_exchange_n (&arena_head, NULL, __ATOMIC_ACQ_REL);
	while (arena) {
		MonoIosJitArena *next = arena->next;
		release_arena (arena);
		arena = next;
	}
	pthread_mutex_unlock (&arena_mutex);
}

static MonoIosJitArena *
find_arena (void *address)
{
	MonoIosJitArena *arena;

	for (arena = __atomic_load_n (&arena_head, __ATOMIC_ACQUIRE); arena; arena = arena->next) {
		size_t offset = (uintptr_t)address - (uintptr_t)arena->execute_address;
		if (offset < arena->capacity)
			return arena;
	}
	return NULL;
}

static void
write_arena_memory (MonoIosJitArena *arena, void *address, const void *source, size_t size, int fill_value, int is_fill)
{
	size_t offset = (uintptr_t)address - (uintptr_t)arena->execute_address;
	void *destination;

	if (!arena->write_address || offset > arena->capacity || size > arena->capacity - offset)
		__builtin_trap ();
	destination = (char *)arena->write_address + offset;
	if (is_fill) {
		memset (destination, fill_value, size);
	} else {
		if (!source && size)
			__builtin_trap ();
		if (size == sizeof (uint32_t) && (uintptr_t)destination % sizeof (uint32_t) == 0) {
			uint32_t value;
			memcpy (&value, source, sizeof (value));
			__atomic_store_n ((uint32_t *)destination, value, __ATOMIC_RELAXED);
		} else if (size == sizeof (uint64_t) && (uintptr_t)destination % sizeof (uint64_t) == 0) {
			uint64_t value;
			memcpy (&value, source, sizeof (value));
			__atomic_store_n ((uint64_t *)destination, value, __ATOMIC_RELAXED);
		} else {
			memcpy (destination, source, size);
		}
	}
}

static int
round_size (size_t size, size_t alignment, size_t *rounded_size)
{
	if (!size || size > SIZE_MAX - (alignment - 1))
		return 0;
	*rounded_size = ((size + alignment - 1) / alignment) * alignment;
	return 1;
}

static int
startup_capacity (size_t *capacity)
{
	const char *setting = getenv ("MONO_IOS_JIT_POOL_MB");
	unsigned long long megabytes = MONO_IOS_JIT_DEFAULT_POOL_MB;

	if (setting) {
		char *end;
		if (*setting < '0' || *setting > '9')
			return EINVAL;
		errno = 0;
		megabytes = strtoull (setting, &end, 10);
		if (errno || *end || !megabytes)
			return EINVAL;
	}
	if (megabytes > SIZE_MAX / MONO_IOS_JIT_MEGABYTE)
		return EINVAL;
	*capacity = (size_t)megabytes * MONO_IOS_JIT_MEGABYTE;
	return 0;
}

static int
debugger_status (int *is_attached)
{
	int names [4] = { CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid () };
	struct kinfo_proc process;
	size_t size = sizeof (process);

	memset (&process, 0, sizeof (process));
	if (sysctl (names, 4, &process, &size, NULL, 0) != 0)
		return errno;
	if (size != sizeof (process))
		return EIO;
	*is_attached = (process.kp_proc.p_flag & P_TRACED) != 0;
	return 0;
}

static int
verify_protection (void *address, size_t size, vm_prot_t protection, const char *stage)
{
	uintptr_t cursor = (uintptr_t)address;
	uintptr_t end;

	if (size > UINTPTR_MAX - cursor)
		return report_prepare_error (stage, EFAULT, KERN_SUCCESS, "address range overflow");
	end = cursor + size;
	while (cursor < end) {
		vm_address_t region_address = cursor;
		vm_size_t region_size = 0;
		vm_region_basic_info_data_64_t information;
		mach_msg_type_number_t count = VM_REGION_BASIC_INFO_COUNT_64;
		mach_port_t object_name = MACH_PORT_NULL;
		kern_return_t result;

		result = vm_region_64 (mach_task_self (), &region_address, &region_size,
		                       VM_REGION_BASIC_INFO_64, (vm_region_info_t)&information,
		                       &count, &object_name);
		if (object_name != MACH_PORT_NULL)
			mach_port_deallocate (mach_task_self (), object_name);
		if (result != KERN_SUCCESS)
			return report_prepare_error (stage, mach_error_number (result), result, "vm_region_64");
		if (count != VM_REGION_BASIC_INFO_COUNT_64)
			return report_prepare_error (stage, EIO, KERN_SUCCESS, "unexpected region info size");
		if (!region_size || region_address > cursor || region_size > UINTPTR_MAX - region_address ||
		    cursor - region_address >= region_size)
			return report_prepare_error (stage, EFAULT, KERN_SUCCESS, "region gap or overflow");
		if ((information.protection & (VM_PROT_READ | VM_PROT_WRITE | VM_PROT_EXECUTE)) != protection) {
			os_log_error (OS_LOG_DEFAULT, "Mono iOS JIT protection mismatch: stage=%{public}s offset=%zu expected=%d actual=%d",
			              stage, cursor - (uintptr_t)address, protection, information.protection);
			return report_prepare_error (stage, EACCES, KERN_SUCCESS, "unexpected R/W/X permissions");
		}
		cursor = region_address + region_size;
	}
	return 0;
}

static int
verify_arena (MonoIosJitArena *arena, size_t page_size)
{
	int error = verify_protection (arena->execute_address, arena->capacity, VM_PROT_READ | VM_PROT_EXECUTE, "RX protection verification");

	if (error)
		return error;
	error = verify_protection (arena->write_address, arena->capacity, VM_PROT_READ | VM_PROT_WRITE, "RW protection verification");
	if (error)
		return error;
	for (size_t offset = 0; offset < arena->capacity; offset += page_size) {
		void *execute_address = (char *)arena->execute_address + offset;
		void *write_address = (char *)arena->write_address + offset;
		uint32_t value = (uint32_t)((offset / page_size) % 65534) + 1;
		uint32_t instructions [2] = { MONO_IOS_JIT_MOVZ_W0 | (value << 5), MONO_IOS_JIT_RET };

		for (int patch = 0; patch < 2; ++patch) {
			write_arena_memory (arena, execute_address, instructions,
			                    patch ? sizeof (instructions [0]) : sizeof (instructions), 0, 0);
			sys_dcache_flush (write_address, sizeof (instructions));
			sys_icache_invalidate (execute_address, sizeof (instructions));
			if (memcmp (execute_address, instructions, sizeof (instructions)) != 0) {
				os_log_error (OS_LOG_DEFAULT, "Mono iOS JIT alias readback mismatch: offset=%zu pass=%d", offset, patch);
				return report_prepare_error ("alias readback", EIO);
			}
			int actual = execute_probe (execute_address);
			if (actual != (int)value) {
				os_log_error (OS_LOG_DEFAULT, "Mono iOS JIT execution probe mismatch: offset=%zu pass=%d expected=%u actual=%d",
				              offset, patch, value, actual);
				return report_prepare_error ("execution probe", EIO);
			}
			++value;
			instructions [0] = MONO_IOS_JIT_MOVZ_W0 | (value << 5);
		}
	}
	return 0;
}

static int
execute_probe (void *address)
{
	return ((int (*)(void))address) ();
}

static int
mach_error_number (kern_return_t result)
{
	switch (result) {
	case KERN_NO_SPACE:
	case KERN_RESOURCE_SHORTAGE:
		return ENOMEM;
	case KERN_PROTECTION_FAILURE:
		return EACCES;
	case KERN_INVALID_ADDRESS:
		return EFAULT;
	case KERN_INVALID_ARGUMENT:
		return EINVAL;
	default:
		return EIO;
	}
}

static int
report_prepare_error (const char *stage, int error, kern_return_t native_error, const char *detail)
{
	int saved_errno = errno;
	os_log_error (OS_LOG_DEFAULT, "Mono iOS JIT preparation failed: stage=%{public}s errno=%d (%{public}s) mach=%d detail=%{public}s",
	              stage, error, strerror (error), native_error, detail ? detail : "");
	errno = saved_errno;
	return error;
}

static void
release_arena (MonoIosJitArena *arena)
{
	if (arena->write_address)
		vm_deallocate (mach_task_self (), (vm_address_t)arena->write_address, arena->capacity);
	if (arena->execute_address)
		vm_deallocate (mach_task_self (), (vm_address_t)arena->execute_address, arena->capacity);
	release_ranges (arena->free_ranges);
	release_ranges (arena->allocations);
	free (arena);
}

static void
release_ranges (MonoIosJitRange *range)
{
	while (range) {
		MonoIosJitRange *next = range->next;
		free (range);
		range = next;
	}
}

}

#endif
