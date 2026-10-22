# IL2CPP2MONO
a unity mod that adds support for mono on mobile.

# how does it work?

it works by replacing the original libil2cpp with a fake, a larper if you will. this fake forwards the calls to mono. and also handles the dlls and stuff.
<img width="1378" height="576" alt="image" src="https://files.catbox.moe/jjc25v.png" />

the mono build used for this is Unity's one. i have a github action here that can build it.
the sgen version of mono GC is used.

on IOS, to make monomod work, there are now some internal calls which process detours directly

# Status

75 of the 241 API calls have NOT been implemented. (basically all of them do nothing or havent been used yet)

It now works on ios. tested on 18.7 (non-txm) and 26 (txm)

# Installation (ANDROID)

to install it, you need to create a folder in the apk assets folder called Mono. put a Managed.zip in there that directly contains all your dlls. and put mono.zip, it stores the config and the native libs.
monosgen-2.0.so and the replacement libil2cpp.so are placed in the lib folder.

if you are building the game in the unity editor however, use the editor script. have a folder called Libs in Editor/Android that has libil2cpp.so (replacement) and monosgen there. and have mono.zip in Editor/Android folder as well.

# Installation (IOS)

on ios, you arent going to be able to just modify the ipa or something. you will have to use the editor script.
in Editor/IOS. have libil2cpp.a, which is il2cpp2mono merged with mono libraries. and have mono.zip

it will require some form of a JIT enabler, like stikdebug
