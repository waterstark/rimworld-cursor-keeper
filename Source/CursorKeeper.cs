// CursorKeeper: works around a macOS fullscreen bug where the system silently
// replaces an app's custom cursor with the default arrow (for example after the
// pointer enters the band at the top of the screen). Unity is not told, so the
// game cursor stays lost until the window loses focus.
//
// The mod remembers the NSCursor that Unity installed for the game cursor and
// compares it with the cursor macOS is really showing: every frame for half a
// second after the pointer returns from a screen edge, otherwise twice a second.
// When they differ while the game is focused and the pointer is inside the game,
// it installs the game cursor again.

using System;
using System.Runtime.InteropServices;
using HarmonyLib;
using UnityEngine;
using Verse;

namespace CursorKeeper
{
    [StaticConstructorOnStartup]
    public static class CursorKeeperStartup
    {
        static CursorKeeperStartup()
        {
            if (Application.platform != RuntimePlatform.OSXPlayer)
            {
                Log.Message("[CursorKeeper] Not macOS, doing nothing.");
                return;
            }
            try
            {
                var harmony = new Harmony("waterstark.cursorkeeper");
                foreach (var m in typeof(Cursor).GetMethods())
                {
                    if (m.Name == "SetCursor")
                    {
                        var ps = m.GetParameters();
                        if (ps.Length > 0 && ps[0].ParameterType == typeof(Texture2D))
                            harmony.Patch(m, postfix: new HarmonyMethod(typeof(CursorKeeperStartup), nameof(SetCursorPostfix)));
                    }
                }
            }
            catch (Exception e)
            {
                Log.Warning("[CursorKeeper] Could not patch Cursor.SetCursor, will capture the cursor without it: " + e.Message);
            }

            var go = new GameObject("CursorKeeper");
            UnityEngine.Object.DontDestroyOnLoad(go);
            go.AddComponent<CursorKeeperBehaviour>();
            Log.Message("[CursorKeeper] Started.");
        }

        public static void SetCursorPostfix(Texture2D texture)
        {
            CursorKeeperBehaviour.OnGameSetCursor(texture != null);
        }
    }

    public class CursorKeeperBehaviour : MonoBehaviour
    {
        // Asking macOS which cursor is on screen costs about 0.07 ms, so it is
        // done rarely in general and every frame only for a short burst right
        // after the pointer comes back from a screen edge (top band, Dock),
        // which is where macOS swaps the cursor.
        const float IdleInterval = 0.5f;
        const float BurstDuration = 0.5f;
        const int EdgeMarginPx = 2;
        const int MaxLogLines = 15;

        static bool customWanted = true;   // the game uses its own cursor
        static bool needCapture = true;    // remember the cursor Unity installed
        static IntPtr saved = IntPtr.Zero; // retained NSCursor of the game cursor
        static int captureDelayFrames = 0;

        float nextCheck;
        float burstUntil;
        bool wasAtEdge;
        int restored;
        int logged;
        bool objcOk = true;

        public static void OnGameSetCursor(bool custom)
        {
            customWanted = custom;
            needCapture = custom;
            captureDelayFrames = 2; // let Unity apply the new cursor first
            if (!custom) ReleaseSaved();
        }

        static void ReleaseSaved()
        {
            if (saved != IntPtr.Zero)
            {
                ObjC.Send(saved, ObjC.SelRelease);
                saved = IntPtr.Zero;
            }
        }

        // Inside the game and not touching its edges.
        static bool PointerInsideGame()
        {
            Vector3 p = Input.mousePosition;
            return p.x >= EdgeMarginPx && p.y >= EdgeMarginPx
                && p.x < Screen.width - EdgeMarginPx && p.y < Screen.height - EdgeMarginPx;
        }

        void Update()
        {
            if (!objcOk || !customWanted || !Cursor.visible) return;
            if (!Application.isFocused) return;
            if (!PointerInsideGame())
            {
                wasAtEdge = true;
                return;
            }
            if (wasAtEdge)
            {
                wasAtEdge = false;
                burstUntil = Time.realtimeSinceStartup + BurstDuration;
            }

            try
            {
                if (needCapture)
                {
                    if (captureDelayFrames > 0) { captureDelayFrames--; return; }
                    IntPtr cur = ObjC.Send(ObjC.NSCursor, ObjC.SelCurrentCursor);
                    IntPtr arrow = ObjC.Send(ObjC.NSCursor, ObjC.SelArrowCursor);
                    if (cur != IntPtr.Zero && cur != arrow)
                    {
                        ReleaseSaved();
                        saved = ObjC.Send(cur, ObjC.SelRetain);
                        needCapture = false;
                        NSPoint h = ObjC.SendPoint(saved, ObjC.SelHotSpot);
                        Note("captured game cursor, hotspot " + h.x + "," + h.y);
                    }
                    return;
                }

                if (saved == IntPtr.Zero) return;
                float now = Time.realtimeSinceStartup;
                if (now >= burstUntil)
                {
                    if (now < nextCheck) return;
                    nextCheck = now + IdleInterval;
                }

                IntPtr sys = ObjC.Send(ObjC.NSCursor, ObjC.SelCurrentSystemCursor);
                if (sys == IntPtr.Zero) return;
                NSPoint hs = ObjC.SendPoint(sys, ObjC.SelHotSpot);
                NSPoint hg = ObjC.SendPoint(saved, ObjC.SelHotSpot);
                if (Math.Abs(hs.x - hg.x) < 0.5 && Math.Abs(hs.y - hg.y) < 0.5) return;

                // macOS shows another cursor: put the game cursor back.
                ObjC.Send(saved, ObjC.SelSet);
                restored++;
                Note("restored game cursor (#" + restored + "), system cursor hotspot was " + hs.x + "," + hs.y);
            }
            catch (Exception e)
            {
                objcOk = false;
                Log.Warning("[CursorKeeper] Disabled after error: " + e);
            }
        }

        void Note(string msg)
        {
            if (logged >= MaxLogLines) return;
            logged++;
            Log.Message("[CursorKeeper] " + msg + (logged == MaxLogLines ? " (further messages muted)" : ""));
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct NSPoint { public double x; public double y; }

    static class ObjC
    {
        const string Lib = "/usr/lib/libobjc.A.dylib";

        [DllImport(Lib)] static extern IntPtr objc_getClass(string name);
        [DllImport(Lib)] static extern IntPtr sel_registerName(string name);
        [DllImport(Lib, EntryPoint = "objc_msgSend")] public static extern IntPtr Send(IntPtr receiver, IntPtr selector);
        [DllImport(Lib, EntryPoint = "objc_msgSend")] public static extern NSPoint SendPoint(IntPtr receiver, IntPtr selector);

        public static readonly IntPtr NSCursor = objc_getClass("NSCursor");
        public static readonly IntPtr SelCurrentCursor = sel_registerName("currentCursor");
        public static readonly IntPtr SelCurrentSystemCursor = sel_registerName("currentSystemCursor");
        public static readonly IntPtr SelArrowCursor = sel_registerName("arrowCursor");
        public static readonly IntPtr SelHotSpot = sel_registerName("hotSpot");
        public static readonly IntPtr SelSet = sel_registerName("set");
        public static readonly IntPtr SelRetain = sel_registerName("retain");
        public static readonly IntPtr SelRelease = sel_registerName("release");
    }
}
