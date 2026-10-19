using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor.Android;
using UnityEditor;
using UnityEditor.Callbacks;
using UnityEditor.iOS.Xcode;
using UnityEditor.iOS.Xcode.Extensions;
using UnityEngine;
using Debug = UnityEngine.Debug;
public class InjectMonoShim : IPostGenerateGradleAndroidProject
{
    private static void RecreateDirectory(string path)
    {
        if (Directory.Exists(path))
            Directory.Delete(path, true);
        Directory.CreateDirectory(path);
    }
    private const int CallbackOrder = 999;
    public int callbackOrder => CallbackOrder; // run late, after Unity finishes writing the project

    private const string MonoZip = "mono.zip";
    private const string ManagedZip = "Managed.zip";
    public void OnPostGenerateGradleAndroidProject(string path)
    {
        string assetsRoot = Application.dataPath;
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
        
        string jniLibsDir = Path.Combine(path, "src/main/jniLibs/arm64-v8a");
        foreach (var file in Directory.GetFiles(assetsRoot+"/Editor/Android/Libs/").Where((s => s.EndsWith(".so"))))
        {
            File.Copy(file, Path.Combine(jniLibsDir, Path.GetFileName(file)), true);
        }

        // Copy the assets (Managed.zip, mono.zip) into the apk's assets folder
        string assetsDir = Path.Combine(path, "src/main/assets/Mono");
        Directory.CreateDirectory(assetsDir);
        
        File.Copy(assetsRoot+$"/Editor/Android/{MonoZip}",
            Path.Combine(assetsDir, MonoZip), true);

        string Managed = Path.GetDirectoryName(Path.GetDirectoryName(path)) + "/Il2CppBackup/Managed";
        File.Delete(Path.Combine(assetsDir, ManagedZip));
        ZipFile.CreateFromDirectory(Managed, Path.Combine(assetsDir, ManagedZip));
        
        Debug.Log("[IL2CPP2MONO] Successfully installed.");
    }
    
    private const string NativeInputsRelative = "Libraries/NativeRuntimeInputs";
    private const string AssetsRelative = NativeInputsRelative + "/Assets";
    [PostProcessBuild(CallbackOrder)]
    public static void OnPostGenerateXCodeProject(BuildTarget target, string xcodeProjectPath)
    {
        if (target != BuildTarget.iOS)
            return;

        string assetsRoot = Application.dataPath;
        ConfigurePList(xcodeProjectPath);

        string iosSource = Path.Combine(assetsRoot, "Editor", "IOS");
        string archiveSource = Path.Combine(iosSource, "libil2cpp.a");
        string monoZipSource = Path.Combine(iosSource, MonoZip);
        string managedSource = Path.GetFullPath(
            Path.Combine(assetsRoot, "..", "Library", "Bee", "artifacts", "iOS", "ManagedStripped"));

        string replacementArchive = Path.Combine(xcodeProjectPath, "Libraries", "libil2cpp.a");
        File.Copy(archiveSource, replacementArchive, true);

        string assetStage = Path.Combine(xcodeProjectPath, AssetsRelative);
        RecreateDirectory(assetStage);
        File.Copy(monoZipSource, Path.Combine(assetStage, MonoZip), true);
        
        string managedZip = Path.Combine(assetStage, ManagedZip);
        ZipFile.CreateFromDirectory(managedSource, managedZip);

        string pbxProjectPath = PBXProject.GetPBXProjectPath(xcodeProjectPath);
        var project = new PBXProject();
        project.ReadFromFile(pbxProjectPath);

        string frameworkTarget = project.GetUnityFrameworkTargetGuid();
        string mainTarget = project.GetUnityMainTargetGuid();
        string gameAssemblyTarget = project.TargetGuidByName("GameAssembly");

        ConfigureGetTaskAllowEntitlement(project, xcodeProjectPath, mainTarget);
        
        string generatedCppDirectory = Path.Combine(
            xcodeProjectPath, "Il2CppOutputProject", "Source", "il2cppOutput");
        string nativeGlueRelative = "Libraries/NativeRuntimeGlue";
        string nativeGlueDirectory = Path.Combine(xcodeProjectPath, nativeGlueRelative);
        Directory.CreateDirectory(nativeGlueDirectory);

        string beeIosArtifacts = Path.GetFullPath(Path.Combine(
            assetsRoot, "..", "Library", "Bee", "artifacts", "iOS"));

        foreach (string glueName in new[]
                 {
                     "UnityClassRegistration.cpp",
                     "UnityICallRegistration.cpp"
                 })
        {
            string glueSource = Path.Combine(generatedCppDirectory, glueName);
            if (!File.Exists(glueSource) && Directory.Exists(beeIosArtifacts))
            {
                glueSource = Directory.GetFiles(beeIosArtifacts, glueName, SearchOption.AllDirectories)
                    .FirstOrDefault();
            }

            string stagedRelative = nativeGlueRelative + "/" + glueName;
            string stagedAbsolute = Path.Combine(nativeGlueDirectory, glueName);
            File.Copy(glueSource, stagedAbsolute, true);

            string glueGuid = project.FindFileGuidByProjectPath(stagedRelative);
            if (string.IsNullOrEmpty(glueGuid))
                glueGuid = project.AddFile(stagedRelative, stagedRelative, PBXSourceTree.Source);
            project.AddFileToBuild(frameworkTarget, glueGuid);
        }
        project.AddBuildProperty(
            frameworkTarget,
            "OTHER_LDFLAGS",
            "-all_load");
        if (!project.ContainsFramework(frameworkTarget, "GSS.framework"))
            project.AddFrameworkToProject(
                frameworkTarget, "GSS.framework", false);
        
        string initialPbxText = project.WriteToString();
        string gameAssemblyProductRef = GetPropertyValue(
            GetPbxObject(initialPbxText, gameAssemblyTarget), "productReference");

        if (!string.IsNullOrEmpty(gameAssemblyProductRef))
            project.RemoveFileFromBuild(frameworkTarget, gameAssemblyProductRef);

        project.AddBuildProperty(frameworkTarget, "OTHER_LDFLAGS", "-lz");
        project.AddBuildProperty(frameworkTarget, "OTHER_LDFLAGS", "-liconv");
        project.SetBuildProperty(
            frameworkTarget,
            "GCC_SYMBOLS_PRIVATE_EXTERN",
            "NO");

        project.SetBuildProperty(
            frameworkTarget,
            "DEAD_CODE_STRIPPING",
            "NO");
        
        string projectText = project.WriteToString();
        if (!projectText.Contains("name = \"Copy Mono Runtime Assets\";"))
        {
            string copyAssetsScript =
                "set -eu\n" +
                "SRC=\"${PROJECT_DIR}/" + AssetsRelative + "\"\n" +
                "RESOURCES=\"${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}\"\n" +
                "DEST=\"${RESOURCES}/Data/Raw/Mono\"\n" +
                "mkdir -p \"$DEST\"\n" +
                "cp \"$SRC/" + MonoZip + "\" \"$DEST/" + MonoZip + "\"\n" +
                "cp \"$SRC/" + ManagedZip + "\" \"$DEST/" + ManagedZip + "\"\n";

            project.AddShellScriptBuildPhase(
                mainTarget,
                "Copy Mono Runtime Assets",
                "/bin/sh",
                copyAssetsScript);
        }

        project.WriteToFile(pbxProjectPath);

        // Keep the GameAssembly target object intact. Only detach it from the build graph;
        // deleting the whole target with hand-written pbxproj edits was too destructive.
        string lastValidPbxText = File.ReadAllText(pbxProjectPath);
        string rawPbxText = DetachTargetFromBuildGraph(lastValidPbxText, gameAssemblyTarget);
        rawPbxText = RemoveGeneratedCppProjectReferences(rawPbxText);

        File.WriteAllText(pbxProjectPath, rawPbxText);
        RemoveGameAssemblyFromSchemes(xcodeProjectPath, gameAssemblyTarget);

        if (Directory.Exists(generatedCppDirectory))
        {
            Directory.Delete(generatedCppDirectory, true);
            string sourceDirectory = Path.GetDirectoryName(generatedCppDirectory);
            if (Directory.Exists(sourceDirectory) && !Directory.EnumerateFileSystemEntries(sourceDirectory).Any())
                Directory.Delete(sourceDirectory, false);
        }

        Debug.Log("[IL2CPP2MONO] Successfully installed.");
    }
    private static void ConfigurePList(string buildPath)
    {
        string plistPath = Path.Combine(buildPath, "Info.plist");

        var plist = new PlistDocument();
        plist.ReadFromFile(plistPath);
        plist.root.SetBoolean("UIFileSharingEnabled", true);
        plist.root.SetBoolean("LSSupportsOpeningDocumentsInPlace", true);
        plist.WriteToFile(plistPath);
    }

    // The signing profile must permit get-task-allow=true.
    private static void ConfigureGetTaskAllowEntitlement(PBXProject project, string projectPath, string target)
    {
        string path = project.GetBuildPropertyForAnyConfig(target, "CODE_SIGN_ENTITLEMENTS");
        if (string.IsNullOrWhiteSpace(path))
        {
            path = NativeInputsRelative + "/App.entitlements";
            project.SetBuildProperty(target, "CODE_SIGN_ENTITLEMENTS", path);
        }

        path = path.Trim().Trim('"')
            .Replace("$(SRCROOT)/", "").Replace("${SRCROOT}/", "")
            .Replace("$(PROJECT_DIR)/", "").Replace("${PROJECT_DIR}/", "")
            .Replace("$(PROJECT_ROOT)/", "").Replace("${PROJECT_ROOT}/", "")
            .Replace('/', Path.DirectorySeparatorChar);
        if (path.Contains("$(") || path.Contains("${"))
            throw new Exception("Cannot resolve CODE_SIGN_ENTITLEMENTS: " + path);

        string absolutePath = Path.GetFullPath(Path.IsPathRooted(path) ? path : Path.Combine(projectPath, path));
        Directory.CreateDirectory(Path.GetDirectoryName(absolutePath));
        var plist = new PlistDocument();
        if (File.Exists(absolutePath)) plist.ReadFromFile(absolutePath);
        plist.root.SetBoolean("get-task-allow", true);
        plist.WriteToFile(absolutePath);
    }
    
    //Gotta love how just 5 lines for android is about 250 fucking lines for ios
    private static string DetachTargetFromBuildGraph(string pbxText, string targetGuid)
    {
        var dependencyIds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var proxyIds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (PbxObject obj in EnumeratePbxObjects(pbxText))
        {
            if (obj.Block.Contains("isa = PBXTargetDependency;") &&
                string.Equals(GetPropertyValue(obj.Block, "target"), targetGuid,
                    StringComparison.OrdinalIgnoreCase))
            {
                dependencyIds.Add(obj.Guid);
                string proxyGuid = GetPropertyValue(obj.Block, "targetProxy");
                if (!string.IsNullOrEmpty(proxyGuid))
                    proxyIds.Add(proxyGuid);
            }

            if (obj.Block.Contains("isa = PBXContainerItemProxy;") &&
                string.Equals(GetPropertyValue(obj.Block, "remoteGlobalIDString"), targetGuid,
                    StringComparison.OrdinalIgnoreCase))
            {
                proxyIds.Add(obj.Guid);
            }
        }

        // Remove only target dependency entries from target dependency arrays.
        if (dependencyIds.Count > 0)
            pbxText = RemoveGuidsFromAllArrays(pbxText, dependencyIds, "dependencies");

        var objectsToRemove = new HashSet<string>(dependencyIds, StringComparer.OrdinalIgnoreCase);
        objectsToRemove.UnionWith(proxyIds);
        if (objectsToRemove.Count > 0)
            pbxText = RemovePbxObjects(pbxText, objectsToRemove);

        return pbxText;
    }

    private static string RemoveGeneratedCppProjectReferences(string pbxText)
    {
        var removeIds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (PbxObject obj in EnumeratePbxObjects(pbxText))
        {
            if (obj.Block.Contains("isa = PBXFileReference;") &&
                Regex.IsMatch(obj.Block,
                    @"\bpath\s*=\s*""?Il2CppOutputProject/Source/il2cppOutput/"))
            {
                removeIds.Add(obj.Guid);
            }
        }

        bool addedGroup;
        do
        {
            addedGroup = false;
            foreach (PbxObject obj in EnumeratePbxObjects(pbxText))
            {
                if (!obj.Block.Contains("isa = PBXGroup;") || removeIds.Contains(obj.Guid))
                    continue;

                List<string> children = GetArrayGuids(obj.Block, "children");
                if (children.Count > 0 && children.All(id => removeIds.Contains(id)))
                {
                    removeIds.Add(obj.Guid);
                    addedGroup = true;
                }
            }
        } while (addedGroup);

        if (removeIds.Count == 0)
            return pbxText;

        pbxText = RemoveGuidsFromAllArrays(pbxText, removeIds,
            "children", "files", "buildPhases", "targets", "dependencies");
        return RemovePbxObjects(pbxText, removeIds);
    }

    private static string RemoveGuidsFromAllArrays(
        string pbxText, IEnumerable<string> guids, params string[] arrayNames)
    {
        var ids = new HashSet<string>(guids, StringComparer.OrdinalIgnoreCase);
        foreach (PbxObject obj in EnumeratePbxObjects(pbxText).ToArray())
        {
            string block = GetPbxObject(pbxText, obj.Guid);
            if (block == null)
                continue;

            string updated = block;
            foreach (string arrayName in arrayNames)
                updated = RemoveGuidLinesFromArray(updated, arrayName, ids);

            if (!string.Equals(block, updated, StringComparison.Ordinal))
                pbxText = ReplacePbxObject(pbxText, obj.Guid, updated);
        }
        return pbxText;
    }

    private static string RemoveGuidLinesFromArray(
        string objectBlock, string arrayName, IEnumerable<string> guids)
    {
        var ids = new HashSet<string>(guids, StringComparer.OrdinalIgnoreCase);
        if (ids.Count == 0)
            return objectBlock;

        Match match = Regex.Match(objectBlock,
            @"(?s)(\b" + Regex.Escape(arrayName) + @"\s*=\s*\()(.*?)(\);)");
        if (!match.Success)
            return objectBlock;

        string filtered = string.Join("\n", match.Groups[2].Value.Split('\n')
            .Where(line => !ids.Any(id => Regex.IsMatch(
                line, @"\b" + Regex.Escape(id) + @"\b"))));

        string replacement = match.Groups[1].Value + filtered + match.Groups[3].Value;
        return objectBlock.Substring(0, match.Index) + replacement +
               objectBlock.Substring(match.Index + match.Length);
    }

    private static string RemovePbxObjects(string pbxText, IEnumerable<string> guids)
    {
        var wanted = new HashSet<string>(guids, StringComparer.OrdinalIgnoreCase);
        var spans = EnumeratePbxObjects(pbxText)
            .Where(obj => wanted.Contains(obj.Guid))
            .Select(obj =>
            {
                TryGetObjectSpan(pbxText, obj.Guid, out int start, out int length);
                return new { Start = start, Length = length };
            })
            .OrderByDescending(span => span.Start)
            .ToArray();

        foreach (var span in spans)
        {
            int start = span.Start;
            int length = span.Length;
            if (start + length < pbxText.Length && pbxText[start + length] == '\r') length++;
            if (start + length < pbxText.Length && pbxText[start + length] == '\n') length++;
            pbxText = pbxText.Remove(start, length);
        }
        return pbxText;
    }

    private sealed class PbxObject
    {
        public string Guid;
        public string Block;
    }

    private static IEnumerable<PbxObject> EnumeratePbxObjects(string pbxText)
    {
        var results = new List<PbxObject>();
        foreach (Match header in Regex.Matches(pbxText,
                     @"(?m)^[ \t]*(?<guid>[A-Fa-f0-9]{24})(?:[ \t]*/\*.*?\*/)?[ \t]*=[ \t]*\{"))
        {
            string guid = header.Groups["guid"].Value;
            if (TryGetObjectSpan(pbxText, guid, out int start, out int length))
                results.Add(new PbxObject { Guid = guid, Block = pbxText.Substring(start, length) });
        }
        return results;
    }

    private static string GetPbxObject(string pbxText, string guid)
    {
        if (string.IsNullOrEmpty(guid) || !TryGetObjectSpan(pbxText, guid, out int start, out int length))
            return null;
        return pbxText.Substring(start, length);
    }

    private static string ReplacePbxObject(string pbxText, string guid, string replacement)
    {
        if (!TryGetObjectSpan(pbxText, guid, out int start, out int length))
            throw new Exception("Could not locate Xcode project object " + guid);
        return pbxText.Substring(0, start) + replacement + pbxText.Substring(start + length);
    }

    private static bool TryGetObjectSpan(string text, string guid, out int start, out int length)
    {
        start = length = 0;
        Match header = Regex.Match(text,
            @"(?m)^[ \t]*" + Regex.Escape(guid) + @"(?:[ \t]*/\*.*?\*/)?[ \t]*=[ \t]*\{");
        if (!header.Success) return false;

        start = header.Index;
        int depth = 0, open = text.IndexOf('{', header.Index, header.Length);
        bool quoted = false, escaped = false, comment = false;
        for (int i = open; i < text.Length; i++)
        {
            char c = text[i], next = i + 1 < text.Length ? text[i + 1] : '\0';
            if (comment) { if (c == '*' && next == '/') { comment = false; i++; } continue; }
            if (quoted)
            {
                if (escaped) escaped = false;
                else if (c == '\\') escaped = true;
                else if (c == '"') quoted = false;
                continue;
            }
            if (c == '/' && next == '*') { comment = true; i++; }
            else if (c == '"') quoted = true;
            else if (c == '{') depth++;
            else if (c == '}' && --depth == 0)
            {
                int end = i + 1;
                while (end < text.Length && (text[end] == ' ' || text[end] == '\t')) end++;
                if (end < text.Length && text[end] == ';') end++;
                length = end - start;
                return true;
            }
        }
        return false;
    }

    private static string GetPropertyValue(string objectBlock, string propertyName)
    {
        if (objectBlock == null)
            return null;
        Match match = Regex.Match(objectBlock,
            @"\b" + Regex.Escape(propertyName) + @"\s*=\s*([A-Fa-f0-9]{24})(?:\s*/\*.*?\*/)?\s*;");
        return match.Success ? match.Groups[1].Value : null;
    }

    private static List<string> GetArrayGuids(string objectBlock, string arrayName)
    {
        var result = new List<string>();
        if (objectBlock == null)
            return result;

        Match match = Regex.Match(objectBlock,
            @"(?s)\b" + Regex.Escape(arrayName) + @"\s*=\s*\((.*?)\);");
        if (match.Success)
        {
            result.AddRange(Regex.Matches(match.Groups[1].Value, @"\b[A-Fa-f0-9]{24}\b")
                .Select(m => m.Value));
        }
        return result;
    }

    private static void RemoveGameAssemblyFromSchemes(string xcodeProjectPath, string gameAssemblyGuid)
    {
        foreach (string schemePath in Directory.GetFiles(xcodeProjectPath, "*.xcscheme", SearchOption.AllDirectories))
        {
            string xml = File.ReadAllText(schemePath);
            string updated = Regex.Replace(xml, @"(?s)<BuildActionEntry\b.*?</BuildActionEntry>", match =>
            {
                string entry = match.Value;
                return entry.Contains("BlueprintName=\"GameAssembly\"") ||
                       entry.Contains("BlueprintIdentifier=\"" + gameAssemblyGuid + "\"")
                    ? string.Empty
                    : entry;
            });

            if (!string.Equals(xml, updated, StringComparison.Ordinal))
                File.WriteAllText(schemePath, updated);
        }
    }
}