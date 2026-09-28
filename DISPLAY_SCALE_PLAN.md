# Display scale support: proposed follow-up

This is a design note; the EP39 update does not change coordinate handling.

## Current findings

- `main.py` imports the UI before requesting per-monitor DPI awareness with
  `SetProcessDpiAwareness(2)`. Imported libraries may initialize DPI handling
  earlier. The HRESULT is not checked, so a rejected request can go unnoticed.
- Click calibration stores window-relative coordinates, then subtracts the
  current border/title-bar offset. OCR regions use client-relative coordinates.
- `guarded_input` checks window-relative points against client dimensions before
  conversion. This can reject otherwise valid points near the bottom/right edge.
- OCR regions record client size and refuse capture after a size change. Click
  coordinates do not record their calibration size or DPI.
- Capturing a position currently polls the mouse and reads its location after
  release. Movement between press and release can affect calibration independently
  of display scaling.

## Recommended implementation order

1. Establish process DPI awareness before UI/window-related imports or calls.
   Prefer a PerMonitorV2 application manifest for the packaged executable; use
   `SetProcessDpiAwarenessContext` with checked return values for script startup
   and a documented fallback on older Windows. Check compatibility with Tk and
   CustomTkinter scaling so the bot UI is not scaled twice.
2. Standardize new click points and OCR regions on **client coordinates in
   physical pixels**, converting with Win32 screen/client APIs under a consistent
   DPI context. Check boundaries after conversion. Read DPI awareness and window
   DPI for diagnostics; Windows may virtualize coordinates for other contexts.
3. Store coordinate space, calibration client size, window DPI and schema version
   alongside every point/ROI. Preserve legacy profiles explicitly; migrate only
   when their calibration context is known, otherwise request recalibration.
4. Support per-layout calibration profiles (client size, DPI and in-game UI scale).
   A Windows scale change does not necessarily scale a Direct3D game's controls.
   Do not blindly multiply every coordinate by `new_dpi / old_dpi` or window-size
   ratios. Reuse positions only when the game's layout is verified unchanged.
5. If automatic adaptation is desired, locate stable popup/button anchors in the
   current screenshot, validate the layout, then resolve points and OCR regions
   relative to those anchors. Stop before input if the layout cannot be verified.

## Verification

- Test 100%, 125%, 150%, 175% and 200% scaling and mixed-DPI monitors, including
  moving windows between monitors with negative desktop coordinates.
- Test windowed/borderless modes, changed borders, resized client areas and
  in-game UI scaling separately.
- Verify calibration -> client -> screen round trips and all four client edges.
- Verify OCR crops align with the stat text, and click locations with a benign
  test window before validating the game's actual button response.
- Keep legacy profile behavior explicit and test cancellation during conversion.

## References

- Microsoft: [Setting the default DPI awareness for a process](https://learn.microsoft.com/en-us/windows/win32/hidpi/setting-the-default-dpi-awareness-for-a-process)
- Microsoft: [SetProcessDpiAwarenessContext](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setprocessdpiawarenesscontext)
- Microsoft: [DPI awareness contexts](https://learn.microsoft.com/en-us/windows/win32/hidpi/dpi-awareness-context)

## EP39 OCR behavior in this update

Convert -> OCR -> confirmed target: Cancel then stop; clear non-target: OK;
unclear/blank: retry (up to three reads, 350 ms apart), then stop and warn while
leaving the game's popup open. A target requires two consecutive identical
normalized reads. Conflicting target confirmation never authorizes OK in that
popup. Old profiles must add the Cancel position before starting.

Clear new stat names are allowed without catalog membership. The live reader
uses one fresh Tesseract TSV pass (3x image, PSM 6) for both text and word
confidence. Alphabetic tokens below 65 confidence, obvious symbol noise and
fragment-like tokens trigger review. Recognized game abbreviations are accepted.
This is a heuristic, not a dictionary: confidently misread plausible words may
pass, and unfamiliar abbreviations may require review. Confidence thresholds need
validation against actual game screenshots; they are not success percentages.
