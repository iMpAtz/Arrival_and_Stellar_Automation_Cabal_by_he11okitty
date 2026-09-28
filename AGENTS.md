# Repository Guidelines

## Project Structure & Module Organization

`unified_game_automation/` contains the Windows desktop application:

- `main.py`: application entry point; `replay.py`: offline OCR replay CLI.
- `ui/`: CustomTkinter tabs, main window, and Workbench.
- `automation/`: tool workflows, including Pet, Arrival, Stellar, and Macro.
- `core/`: run lifecycle, cancellation, guarded input, capture, OCR, and profiles.
- `data/`: stat catalogs, configuration, and logo assets; `Tesseract/`: bundled OCR runtime and language data.
- `tests/`: regression scripts and unittest suites; `summaries/`: generated reports.

Root dependency files and PyInstaller specifications define installation and packaging. `build/` and `dist/` are generated output.

## Build, Test, and Development Commands

Run from the repository root using PowerShell. Dependency pins were exercised on Windows with Python 3.14.4.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python unified_game_automation/main.py
```


```powershell
python -B -m unittest discover -s unified_game_automation/tests -p "test_*.py"
python -B unified_game_automation/tests/test_ocr_fixes.py
python -B unified_game_automation/tests/test_ui_smoke.py
```

These run unittest discovery, standalone OCR checks, and hidden-window UI verification. Discovery does not execute standalone function-based scripts; consult README verification commands.

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --workpath build/v6_1_0 --distpath dist/v6_1_0 main_updated.spec
```

Use `main_updated.spec`; `main.spec` is legacy.

## Coding Style & Naming Conventions

Use four-space indentation, UTF-8, `snake_case` functions/modules, and `PascalCase` classes. Follow neighboring code; no repository-wide formatter or linter configuration is present. Keep UI handling in `ui/`, workflow decisions in `automation/`, and reusable infrastructure in `core/`. Queue worker-originated widget updates through `post_ui` or `post_run_ui`.

## Testing Guidelines

Name tests `test_*.py`. Add meaningful regression coverage for changed decisions, cancellation, OCR ambiguity, and click ordering. Mock game attachment and input; tests must not click a live game. No numeric coverage threshold is configured. Report live-game validation separately from synthetic results.

## Commit & Pull Request Guidelines

History uses short, descriptive subjects without a consistent prefix scheme. Write focused imperative subjects, for example `Fix EP39 Cancel ordering`. PRs should explain behavior changes, list validation commands/results, and link related issues when applicable. Include screenshots for UI changes and migration notes for saved configurations.

## Runtime & Configuration Safety

Preserve existing local changes and calibration settings. Route input through connector guards and honor cancellation/dry-run behavior. Do not commit generated reports, personal settings, or build artifacts. Keep coordinate spaces explicit and retain compatible profile loading.
