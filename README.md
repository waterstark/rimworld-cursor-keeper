# Cursor Keeper (macOS)

A small RimWorld 1.6 mod that keeps the game cursor on macOS.

In fullscreen, macOS silently replaces an app's custom cursor with the system arrow when the pointer leaves the band at the top of the screen (and sometimes when it brushes the Dock). The game gets no event, so the arrow stays until you switch windows. If you scroll the map by pushing the mouse to the screen edge, this happens all the time.

The mod notices the swap and puts the RimWorld cursor back, usually within one frame of the pointer returning to the game.

## The bug

- Fullscreen RimWorld on macOS (seen on macOS 26.6, Apple Silicon).
- Move the pointer into the top band of the screen (above the game, where the menu bar would appear), then back down.
- The RimWorld cursor turns into the macOS arrow and stays that way. Switching to another app and back restores it.

This is not a RimWorld or mod bug. Any fullscreen app with a custom cursor is affected:

- **Chromium** hit the same bug and fixed it in March 2026 by checking `[NSCursor currentSystemCursor]` on mouse move and re-setting the cursor when it differs: [issue 430116472](https://issues.chromium.org/issues/430116472), [commit 3975a5b](https://chromium.googlesource.com/chromium/src/+/3975a5b23cd803a6114ecc06e9fe4a4a2671d27d).
- A minimal Unity repro on macOS 26 and Unity 6000.3: [jasharpe/macos-cursor-unity-repro-76038](https://github.com/jasharpe/macos-cursor-unity-repro-76038).
- Godot: [#76038](https://github.com/godotengine/godot/issues/76038) (top edge), [#104892](https://github.com/godotengine/godot/issues/104892) (Dock).
- Apple Developer Forums: [thread 803069](https://developer.apple.com/forums/thread/803069). No reply from Apple.

## How it works

The fix follows the same idea as Chromium's:

1. When the game sets its cursor (`UnityEngine.Cursor.SetCursor`, patched with Harmony), the mod remembers the `NSCursor` that Unity installed.
2. It asks macOS which cursor is really on screen (`[NSCursor currentSystemCursor]`) and compares the hotspots.
3. If they differ while the game is focused and the pointer is inside the game, it calls `-[NSCursor set]` on the saved cursor.

Calls into AppKit go through `objc_msgSend` from `libobjc` via P/Invoke, so there is no native plugin.

### Performance

One check costs about **0.07 ms** (most of it is the query to the window server). To keep the cost near zero, the mod checks:

- **every frame for 0.5 s** right after the pointer comes back from a screen edge (top band, Dock), which is where macOS swaps the cursor;
- **twice a second** the rest of the time, as a safety net.

That is about 0.15 ms per second in normal play, far below anything visible in FPS.

The mod does nothing over the top band and the Dock, where the arrow is expected, or when the game is not focused.

## Install

1. Install [Harmony](https://github.com/pardeike/HarmonyRimWorld/releases/latest).
2. Download `CursorKeeper.zip` from [Releases](https://github.com/waterstark/rimworld-cursor-keeper/releases) and unpack it into `RimWorld/Mods/`, or clone this repository there.
3. Enable **Cursor Keeper (macOS)** in the mod list. Load it after Harmony.

It works with the vanilla cursor and with themed cursors, for example RimThemes. On Windows and Linux it does nothing. It can be added to or removed from an existing save.

The mod writes up to 15 lines tagged `[CursorKeeper]` to `Player.log`, so you can see when it restores the cursor.

## Build

Needs the .NET SDK (any recent version builds `net472`) and a RimWorld install.

```bash
cd Source
dotnet build -c Release
```

The project expects the game at `~/Desktop/RimWorldMac.app`. Adjust `GameManaged` and `HarmonyDir` in `Source/CursorKeeper.csproj` if yours is elsewhere. The DLL is written to `1.6/Assemblies/`.

## Tested on

- RimWorld 1.6.4633 (Unity 2022.3.35f1), macOS 26.6, MacBook Pro M4 Pro.
- With the Hardcore SK mod pack and with RimThemes cursors on and off.

## License

[MIT](LICENSE)
