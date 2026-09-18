# IL2CPP2MONO
a unity mod that adds support for mono on arm64 (android). will be made useless once coreclr is added to android lolll

# how does it work?

it works by replacing the original libil2cpp with a fake, a larper if you will. this fake forwards the calls to mono. and also handles the dlls and stuff.
most il2cpp types can just be the same as mono. but i made the MethodInfo and the class seperate because they are special. (class can be merged though, il think about it)

to install it, you need to create a folder in the apk assets folder called Mono. put a Managed.zip in there that directly contains all your dlls. and put mono.zip, it stores the config and the native libs.
monosgen2.0 should be placed in the lib folder though.

if you are building the game in the unity editor however, use the editor script. have a folder called Libs in the Editor folder that has libil2cpp.so (replacement) and libmonosgen there. and have mono.zip in the Editor folder as well.

the mono build used for this is Unity's one. godot DOES NOT WORK. i have a github action here that can build it.
