using System.Runtime.CompilerServices;

namespace IL2CPP2MONO;

public class App
{
    public string InternalPath {  [MethodImpl(MethodImplOptions.InternalCall)] get; }
}
/*public class IOS
{
    [MethodImpl(MethodImplOptions.InternalCall)]
    private static extern int NativeApply(IntPtr source, IntPtr target);

    [MethodImpl(MethodImplOptions.InternalCall)]
    private static extern int NativeBackup(IntPtr source, IntPtr buffer, uint size);

    [MethodImpl(MethodImplOptions.InternalCall)]
    private static extern int NativeRestore(IntPtr buffer, IntPtr destination, uint size);
}*/
