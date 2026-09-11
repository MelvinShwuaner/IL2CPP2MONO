using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor.Android;
using System.IO.Compression;


public class InjectMonoShim : IPostGenerateGradleAndroidProject
{
    public int callbackOrder => 999; // run late, after Unity finishes writing the project

    public void OnPostGenerateGradleAndroidProject(string path)
    {
        // 'path' is the unityLibrary module root
        string buildGradlePath = Path.Combine(path, "build.gradle");
        string buildGradle = File.ReadAllText(buildGradlePath);

        // Strip the externalNativeBuild block(s) so Gradle never invokes CMake/ndk-build at all
        buildGradle = Regex.Replace(
            buildGradle,
            @"externalNativeBuild\s*\{.*?\n\s*\}\s*\n",
            "",
            RegexOptions.Singleline
        );

        File.WriteAllText(buildGradlePath, buildGradle);

        // Delete the generated C++ source tree entirely — nothing left to compile,
        // and saves real disk space (Il2CppOutputProject can be huge)
        string cppDir = Path.Combine(path, "src/main/cpp");
        if (Directory.Exists(cppDir))
        {
            Directory.Delete(cppDir, true);
        }

        // Drop your prebuilt shim + Mono runtime straight into jniLibs —
        // AGP packages anything here into the APK with no compile step
        string jniLibsDir = Path.Combine(path, "src/main/jniLibs/arm64-v8a");
        foreach (var file in Directory.GetFiles("Assets/Editor/Libs/").Where((s => s.EndsWith(".so"))))
        {
            File.Copy(file, Path.Combine(jniLibsDir, Path.GetFileName(file)), true);
        }

        // Copy your assets (Managed.zip, MonoEtc.zip) into the module's assets folder
        string assetsDir = Path.Combine(path, "src/main/assets/Mono");
        Directory.CreateDirectory(assetsDir);
        
        File.Copy("Assets/Editor/Etc.zip",
                  Path.Combine(assetsDir, "Etc.zip"), true);

        string Managed = Path.GetDirectoryName(Path.GetDirectoryName(path)) + "/Il2CppBackup/Managed";
        File.Delete(Path.Combine(assetsDir, "Managed.zip"));
        ZipFile.CreateFromDirectory(Managed, Path.Combine(assetsDir, "Managed.zip"));
    }
}