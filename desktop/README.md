# Skrivi Rett 0.1.0 — local Windows application

Skrivi Rett is the first native desktop version of the Norwegian spelling sandbox.
Its layout follows Skrivi Lytt and Snakk: warm orange/cream styling, a focused main
window, and a separate Settings window with General, Shortcuts, Models, Privacy and
About tabs (displayed in Norwegian in this first version).

## Install and try

Run `dist/installer/Skrivi-Rett-0.1.0-local-setup.exe`. It installs for the current
Windows user without administrator rights and creates a Start-menu entry **Skrivi
Rett**, with an optional desktop shortcut. This is an unsigned local test build.
The installer is generated locally and is not published as a GitHub release.

This build is intended for the existing development/test PC. It requires the
previously installed Norwegian sandbox cache at `%LOCALAPPDATA%\Skrivi` (or
`SKRIVI_CACHE_DIR`), including its Python 3.12 runtime, NorBERT3 Small, Nuspell,
Ordbank, the base-form help index and dictionary index. No model or dictionary is
bundled or downloaded. It is not yet an installer for a clean PC.

1. Write, paste or open a UTF-8 text file.
2. Choose **Sjekk teksten** (Ctrl+Enter).
3. Select a marked word. Read the definition/example, hear it with the existing
   Norwegian Windows voice, then choose a replacement or **Behold**.
4. **Flere forslag** exposes remaining eligible candidates. **Angre retting** restores
   an earlier decision. **Skriv videre** returns to free writing.
5. Copy or explicitly save the result. There is no automatic text history.

On wide windows suggestions appear beside the text. On narrow windows they move
below it. Suggestions never replace text automatically. **Husk ordet** stores the
selected word in the existing personal word list; undoing a review decision does
not remove that persistent preference.

## Model behaviour

The desktop app uses the existing `nuspell_context` engine plus the measured
extended soft-hyphen ordering policy from 25 September. Unsupported newly
hyphenated candidates are demoted, not discarded. The old browser sandbox is
unchanged. The desktop has no experimental mode selector.

Longer documents are checked in bounded windows of up to 80 word tokens / 3,500
characters, preferring sentence boundaries. Maximum input is 20,000 characters.
Context cannot cross those windows. This avoids the old 100-word rejection but
is not a new accuracy benchmark; long-document performance remains to be measured.
A check can be cancelled, and a 180-second timeout preserves the text for retry.

Definitions come from the existing direct dictionary index. They are labelled as
possible meanings, not automatically selected senses. Some suggestions still lack
help. Compound-help and expanded-importer experiments are not promoted here.

## Data and installation

- App: `%LOCALAPPDATA%\SkriviRett\app`.
- Models, runtime, dictionary and remembered words: existing `%LOCALAPPDATA%\Skrivi`.
- Text-size preference: Windows user settings under `HKCU\Software\Skrivi\Rett`.
- Text stays in memory unless explicitly saved or copied to the Windows clipboard.
- Closing warns about text not saved to a file. Closing exits the app; no tray mode.
- Uninstall through Windows Installed apps. Cache and preferences remain intact.

## Build

Use an isolated Python 3.14 build environment with the packages in
`desktop/requirements-build.txt`. Do not add another app's site-packages to
PYTHONPATH: mixing environments caused a packaged Qt startup failure in development.
Inno Setup 6.7.3 is the tested compiler. Commit changes before building:

```powershell
python tools/build_desktop.py --compiler C:\path\to\ISCC.exe
```

The builder only includes an explicit runtime-module allowlist and no corpora,
model weights, cached databases or test results. It records the source commit and
package hashes in `package.json`, and writes the installer hash beside the setup
file. The GUI executable supports `--check-startup` and `--self-test <result.json>`
for local package verification. The latter checks a fixed, authored sentence.

## Verification on 28 September 2026

- 56 lightweight tests passed; seven resource-dependent tests skipped.
- Native UI test passed: real cached inference and dictionary lookup, exact-word
  replacement and undo, extra-candidate selection, responsive layout and settings.
- Packaged executable and temporary installed copy passed the same authored-sentence
  check, definition lookup and replacement/undo self-test.
- Temporary installation and uninstallation succeeded. Hashes of 27 cached model,
  dictionary and personal-resource files were unchanged.
- Wide/narrow review and settings screenshots inspected locally.

These are functional checks, not a fresh spelling-accuracy evaluation or a test on
an independent clean PC. Signing, Store/MSIX packaging, automatic updates, clean-PC
resource setup, UI language selection and public dictionary licensing clearance
remain unfinished. The app deliberately has no English spelling mode.
