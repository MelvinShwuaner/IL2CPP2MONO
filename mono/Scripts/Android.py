from pathlib import Path

def edit(path, old, new):
  text = path.read_text()
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

#edit(path, old, new)

path = Path("sdks/builds/android.mk")
text = path.read_text()

old = "\t--disable-boehm \\\n\t--disable-executables \\"
new = "\t--with-sgen=no \\\n\t--disable-executables \\"
edit(path, old, new)

path = Path("mono/metadata/unity-utils.h")
edit (path, """void
mono_class_set_allow_gc_aware_layout""", """MONO_API void
mono_class_set_allow_gc_aware_layout""")
