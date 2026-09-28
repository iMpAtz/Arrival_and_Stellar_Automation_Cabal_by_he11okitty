# CABAL Automation Tool - v6.1.0

Developed by Hello Kitty Gang. Windows desktop automation for CABAL Online.

## What changed

The seven existing tools remain available: Arrival, Stellar, Heil, Mail, Pet, Image Clicker, and Macro. A new **Workbench** provides diagnostics, game-window selection, calibration previews, screenshot replay, dry run, run limits, and portable profiles.

The main window now opens on Workbench, with a wider layout, a persistent connection refresh action, a visible active-tool status pill, and an always-available **STOP ALL** control. Repeated Start/Stop controls include hover guidance, while diagnostics and observation output are grouped into read-only cards so inspection is clearly separated from live actions.

- Each run owns a unique ID and cancellation event. Restart is refused until its previous worker exits.
- Escape signals cancellation immediately; GUI cleanup runs through the UI event queue.
- Stellar and Arrival require two consistent, valid OCR readings before evaluating or rerolling. Four unsuccessful observations stop with `needs_review`, without additional clicks.
- Pet Standard checks OCR before each action. EP39 uses Convert, OK, and Cancel: confirmed targets are cancelled before stopping; clear non-target text may continue even for new stat names. Unclear/blank OCR is retried up to three reads, then stops with the game popup open and a bot warning.
- OCR recognizes grouped thousands, uses complete stat names, and distinguishes Penetration / Ignore Penetration / Cancel Ignore Penetration.
- Tesseract uses the bundled language directory through `TESSDATA_PREFIX`, including paths containing spaces. Calls have a four-second timeout.
- Exact-pixel OCR caching has a short expiry and bounded size. Live reroll verification always requests a fresh OCR reading; actions invalidate cached results.
- Every mouse path passes through an input guard. Image Clicker defers its clicks for the entire duration of a shared-tool run.
- Image Clicker supports per-template scale ranges (default 1.0-1.0), rejects flat templates, shares captures within a scan, and invalidates those captures after a click.
- Run reports retain statistics and stop reasons. Optional review screenshots are disabled by default.

## Run from source

The dependency versions in this checkout were exercised with **Windows and Python 3.14.4**. Use a virtual environment; older Python versions have not been validated against these pins.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python unified_game_automation/main.py
```


Run the tool at the same privilege level as the game. The app does not silently elevate itself.

## First use

1. Open **Workbench**, refresh the available game windows, and attach the intended client.
2. Configure click positions, detection regions, and target stats in the tool's tab.
3. Use **Preview game + regions** to check alignment. Red marks the detection region; yellow marks click targets.
4. Use **Read live crop** to inspect raw text, parsed stats, and the decision without clicking. For Pet, choose Pet OCR or Pet EP39.
5. Optionally enable **Dry run**. It suppresses all mouse input through the shared connector. Reroll tools stop after a proposed cycle; Mail, Heil, Macro and Image Clicker run until stopped or limited.
6. Set limits and apply them while idle. Defaults are 30 minutes and 10,000 input attempts per run. Escape stops shared tools and Image Clicker; F6 toggles Image Clicker.

Stellar and Arrival now **inspect the current result before changing it**. Start with the configured stat region visible. An unreadable dialog is not permission to reroll. Pet also needs a readable configured region during its sequence; unexpected scenes stop for review rather than being dismissed automatically.

A stop request is nonblocking. A worker already inside a native operation exits when that operation returns or times out. The app will not start a replacement shared run while the old worker remains active.

## Calibration and profiles

New OCR regions are stored in client-relative coordinates with the calibrated client size. Moving the window is supported; resizing requires recalibration. Existing list-based regions remain supported as absolute screen coordinates. Existing click positions remain window-relative and are checked against client bounds before native input.

Save settings in each tool's tab before using **Export saved settings**. Profile export copies referenced images to an adjacent assets folder. Keep that folder with the exported JSON. Missing assets are reported instead of silently omitted.

Import validates the profile version and allowed config destinations, copies assets into the local data directory, and backs up overwritten JSON files as `.json.bak`. Restart the app to load imported settings. Active runs cannot import profiles.

## Replay without game input

Open a saved **crop** in Workbench, or use the command line:

```powershell
python unified_game_automation/replay.py crop.png --tool Arrival --target Defense --minimum 200
python unified_game_automation/replay.py crop.png --tool Stellar --target Penetration --minimum 15
```

Replay uses the same parser and evaluator as the live reroll workers. It returns `matched`, `absent`, or `unknown`. Replay does not run a game's action sequence.

Workbench also provides **Pet OCR** (Standard) and **Pet EP39**. EP39 previews only its three click positions and reads crops using EP39 text-quality rules. Results describe the next action; a single target reading still requires confirmation during a live run. Workbench inspection never clicks or dismisses the game popup.

Pet settings save only OCR configuration. Older profiles retain their OCR targets, regions, and click positions; obsolete detector settings are ignored. EP39 requires the Cancel position before starting.

## Reports

Source runs write reports under `unified_game_automation/summaries/`; packaged runs write beside the executable under `summaries/`. Each `run_<id>.json` contains the tool, stop reason, elapsed time, action/observation counts, bounded transition history, and available statistics. Stellar and Arrival also retain their human-readable tab summaries.

With review screenshots enabled, a failed Stellar/Arrival verification saves at most one `review_<id>.png` per run. OCR metrics in Workbench show invocation count, exact-cache hits, and total extraction time.

## Architecture

```text
main.py -> MainWindow / tool tabs / Workbench
                 -> start, cancel, queued UI events
              BotCore + RunSession
                 ->
    VerifiedReroll (Stellar/Arrival) | gated Pet sequence | simple click sequences
                 ->
    GameConnector input guard / client region resolution / GDI capture
                 ->
    Tesseract + structured observations | scaled OpenCV templates
```

Image Clicker retains an independent worker and session. Its clicks share the same guard. `core/observations.py` is the shared parsing contract; `core/replay.py` exposes it to Workbench and the CLI. `core/profiles.py` handles portable bundles and atomic JSON writes.

## Verification

```powershell
python -B unified_game_automation/tests/test_runtime_upgrade.py
python -B unified_game_automation/tests/test_pet_ocr_matching.py
python -B unified_game_automation/tests/test_ocr_fixes.py
python -B unified_game_automation/tests/test_bug_fixes.py
python -B unified_game_automation/tests/test_ui_smoke.py
```

The runtime tests cover cancellation/restart, watchdog behavior, input suppression, unknown-frame handling, stat aliases and thousands, reports, cache invalidation, real bundled Tesseract extraction, region movement, portable profiles, and scaled templates. The GUI smoke test constructs hidden windows with game attachment and hotkeys disabled.

Live game behavior, a long-duration GDI resource soak require testing against the intended game client. Synthetic and mocked tests do not establish those properties.

## Build

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --workpath build/v6_1_0 --distpath dist/v6_1_0 main_updated.spec
```

Output: `dist/v6_1_0/HelloK1TTY_Automation_V6.1.0.exe`.

The build bundles Tesseract, language data, GUI assets and runtime dependencies. It excludes unrelated installed ML/data-analysis packages and does not embed personal tab JSON settings. The older `main.spec` remains a legacy build definition; use `main_updated.spec` for this release.

```powershell
.\dist\v6_1_0\HelloK1TTY_Automation_V6.1.0.exe --self-test
```

The packaged self-test constructs a hidden UI and checks real OCR with game attachment, hotkeys, and game input disabled.
