from pathlib import Path

def edit(path, old, new, expected=1):
  text = path.read_text()
  if text.count(old) != expected:
    raise RuntimeError(
        f"{path}: expected {expected} matches for {old!r}, found {count}"
    )
  path.write_text(text.replace(old, new))
    
path = Path("mono/metadata/mono-gc.h")
edit(path, "void mono_gc_stop_world (void);", "MONO_API void mono_gc_stop_world (void);")
edit(path, "void mono_gc_restart_world (void);", "MONO_API void mono_gc_restart_world (void);")

path = Path("mono/metadata/Makefile.am")

old = (
  "libmonoruntimesgen_la_SOURCES = "
  "$(common_sources) $(icall_tables_sources) "
  "$(ilgen_sources) $(gc_dependent_sources) $(sgen_sources)"
)

new = (
  "libmonoruntimesgen_la_SOURCES = "
  "$(common_sources) $(icall_tables_sources) "
  "$(ilgen_sources) $(gc_dependent_sources) "
  "$(unity_gc_dependent_sources) $(sgen_sources)"
)

edit(path, old, new)

path = Path("mono/sgen/sgen-marksweep.c")

edit(
    path,
    "scan_func (object, sgen_obj_get_descriptor (object), queue);",
    "scan_func (object, sgen_obj_get_descriptor_safe (object), queue);"
)


path = Path("mono/sgen/sgen-cardtable.c")

edit(
    path,
    "ctx.ops->scan_object (obj, sgen_obj_get_descriptor (obj), ctx.queue);",
    "ctx.ops->scan_object (obj, sgen_obj_get_descriptor_safe (obj), ctx.queue);",
    expected=2
)
