#!/usr/bin/env python3
"""Build an arm64 iOS dynamic MonoRuntime.framework from adjacent static archives.

Place the input .a files beside this script and run it on macOS with Xcode installed.
The resulting MonoRuntime.framework is also written beside this script.
"""

import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FRAMEWORK_NAME = "MonoRuntime"
FRAMEWORK_VERSION = "1.0.0"
MIN_IOS_VERSION = "17.4"
ARCH = "arm64"
BUNDLE_ID = "com.il2cpp2mono.MonoRuntime"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FRAMEWORK = SCRIPT_DIR / f"{FRAMEWORK_NAME}.framework"

# System dependencies previously needed by the Mono static archives.
SYSTEM_FRAMEWORKS = ["Foundation"]
SYSTEM_LIBRARIES = ["-lc++", "-lz", "-liconv"]


def run_cmd(args):
    args = [str(arg) for arg in args]
    print("Executing:", " ".join(args))
    result = subprocess.run(args, text=True, capture_output=True)
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        raise RuntimeError(f"Command failed with exit code {result.returncode}")
    if result.stderr.strip():
        # Apple tools may emit harmless linker warnings on stderr.
        print(result.stderr.rstrip(), file=sys.stderr)
    return result.stdout.strip()


def write_framework_plist(framework_dir):
    plist = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleExecutable": FRAMEWORK_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": FRAMEWORK_NAME,
        "CFBundlePackageType": "FMWK",
        "CFBundleShortVersionString": FRAMEWORK_VERSION,
        "CFBundleVersion": FRAMEWORK_VERSION,
        "CFBundleSignature": "????",
        "MinimumOSVersion": MIN_IOS_VERSION,
        "CFBundleSupportedPlatforms": ["iPhoneOS"],
    }
    with (framework_dir / "Info.plist").open("wb") as file:
        plistlib.dump(plist, file, fmt=plistlib.FMT_XML, sort_keys=False)


def main():
    static_libs = sorted(
        (
            path for path in SCRIPT_DIR.glob("*.a")
            if path.is_file()
        ),
        key=lambda path: path.name,
    )
    if not static_libs:
        raise RuntimeError(f"No .a static libraries found next to the script: {SCRIPT_DIR}")

    print(f"Found {len(static_libs)} static libraries beside the script:")
    for library in static_libs:
        print(f"  - {library.name}")

    sdk_path = run_cmd(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"])
    clang = ["xcrun", "--sdk", "iphoneos", "clang"]

    with tempfile.TemporaryDirectory(prefix=".MonoRuntime-build-", dir=SCRIPT_DIR) as temp_name:
        temp_root = Path(temp_name)
        framework_dir = temp_root / f"{FRAMEWORK_NAME}.framework"
        framework_dir.mkdir()
        (framework_dir / "lib").mkdir()
        binary_path = framework_dir / FRAMEWORK_NAME

        link_cmd = clang + [
            "-dynamiclib",
            "-arch", ARCH,
            "-isysroot", sdk_path,
            f"-miphoneos-version-min={MIN_IOS_VERSION}",
            "-Wl,-install_name,@rpath/MonoRuntime.framework/MonoRuntime",
            f"-Wl,-current_version,{FRAMEWORK_VERSION}",
            f"-Wl,-compatibility_version,{FRAMEWORK_VERSION}",
        ]

        for framework in SYSTEM_FRAMEWORKS:
            link_cmd += ["-framework", framework]
        link_cmd += SYSTEM_LIBRARIES

        link_cmd += ["-Wl,-undefined,dynamic_lookup"]

        for library in static_libs:
            link_cmd.append(f"-Wl,-force_load,{library.resolve()}")

        link_cmd += ["-o", binary_path]
        run_cmd(link_cmd)
        write_framework_plist(framework_dir)

        run_cmd(["xcrun", "--sdk", "iphoneos", "lipo", binary_path, "-verify_arch", ARCH])

        if OUTPUT_FRAMEWORK.exists():
            if OUTPUT_FRAMEWORK.is_dir() and not OUTPUT_FRAMEWORK.is_symlink():
                shutil.rmtree(OUTPUT_FRAMEWORK)
            else:
                OUTPUT_FRAMEWORK.unlink()
        shutil.move(str(framework_dir), str(OUTPUT_FRAMEWORK))

try:
    main()
except (OSError, RuntimeError, subprocess.SubprocessError) as error:
    print(f"Error: {error}", file=sys.stderr)
    sys.exit(1)
