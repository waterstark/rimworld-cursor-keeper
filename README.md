# Cursor Keeper (macOS)

A small RimWorld 1.6 mod that keeps the game cursor on macOS.

In fullscreen, macOS can silently replace an app's custom cursor with the system arrow after the pointer visits the band at the very top of the screen. The game gets no event, so the arrow stays until you switch to another app and back. If you scroll the map by pushing the mouse against the screen edge, this happens a lot.

The mod notices the swap and puts the RimWorld cursor back as soon as the pointer is inside the game again.

## The bug

- Run RimWorld fullscreen on macOS (seen on macOS 26.6, Apple Silicon).
- Move the pointer into the band at the very top of the screen, where the menu bar would appear. On MacBooks with a notch, this is the black strip above the game.
- Move it back down. The RimWorld cursor is now the macOS arrow and stays that way until you switch apps.

Other fullscreen apps with custom cursors hit the same kind of bug:

- **Chromium** fixed a similar case in March 2026 by checking `[NSCursor currentSystemCursor]` on mouse move and setting the cursor again when it differs: [issue 430116472](https://issues.chromium.org/issues/430116472), [commit 3975a5b](https://chromium.googlesource.com/chromium/src/+/3975a5b23cd803a6114ecc06e9fe4a4a2671d27d).
- A minimal Unity repro on macOS 26 and Unity 6000.3: [jasharpe/macos-cursor-unity-repro-76038](https://github.com/jasharpe/macos-cursor-unity-repro-76038).
- Godot: [#76038](https://github.com/godotengine/godot/issues/76038) (fullscreen), [#104892](https://github.com/godotengine/godot/issues/104892) (brushing the Dock).
- Apple Developer Forums: [thread 803069](https://developer.apple.com/forums/thread/803069), with no reply from Apple as of November 2026.

## How it works

The fix follows the same idea as Chromium's:

1. When the game sets its cursor (`UnityEngine.Cursor.SetCursor`, patched with Harmony), the mod remembers the `NSCursor` that Unity installed.
2. It asks macOS which cursor is really on screen (`[NSCursor currentSystemCursor]`) and compares the hotspots.
3. If they differ while the game is focused and the pointer is inside the game window, it calls `-[NSCursor set]` on the saved cursor.

Calls into AppKit go through `objc_msgSend` in `libobjc` via P/Invoke, so there is no native plugin.

### Performance

One check costs about **0.07 ms**, almost all of it in `[NSCursor currentSystemCursor]` (measured on an M4 Pro). To keep the cost near zero, the mod checks:

- **every frame for 0.5 s** after the pointer comes back into the game from its edge or from outside the window, which is when macOS swaps the cursor;
- **twice a second** the rest of the time, as a safety net.

In normal play that is about 0.15 ms per second, plus short bursts after edge visits. That is far below anything visible in FPS.

The mod does nothing while the pointer is outside the game window or at its very edge, or when the game is not focused.

## Install

1. Install [Harmony](https://github.com/pardeike/HarmonyRimWorld/releases/latest).
2. Download `CursorKeeper.zip` from [Releases](https://github.com/waterstark/rimworld-cursor-keeper/releases) and unpack it into your RimWorld `Mods` folder.
3. Enable **Cursor Keeper (macOS)** in the mod list, after Harmony.

On Windows and Linux the mod does nothing. It adds no defs and no save data, so it can be added to or removed from an existing save.

The game log (`Player.log`) gets a few lines tagged `[CursorKeeper]`: one when it starts and up to 15 about capturing and restoring the cursor.

## Build

Needs the .NET SDK (tested with .NET 11). The RimWorld, Unity and Harmony references come from NuGet ([Krafs.Rimworld.Ref](https://www.nuget.org/packages/Krafs.Rimworld.Ref), [Lib.Harmony.Ref](https://www.nuget.org/packages/Lib.Harmony.Ref)), so no game install is needed.

```bash
cd Source
dotnet build -c Release
```

The DLL is written to `1.6/Assemblies/`.

## Tested on

- RimWorld 1.6.4633 (Unity 2022.3.35f1), macOS 26.6, MacBook Pro M4 Pro (with a notch).
- With the Hardcore SK mod pack and the RimThemes cursor. The vanilla cursor goes through the same code path.

Not tested yet on Macs without a notch, where the top band overlaps the game itself, or on Intel Macs.

## Credits

The cursor in the preview image is the HSK theme cursor from RimThemesLite (Hardcore SK). The image is drawn by `Source/make_preview.py`.

## License

[MIT](LICENSE)
