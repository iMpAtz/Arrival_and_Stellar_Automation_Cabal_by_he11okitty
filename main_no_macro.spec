# -*- mode: python ; coding: utf-8 -*-
import os


a = Analysis(
    ['unified_game_automation/main_no_macro.py'],
    pathex=[os.path.join(SPECPATH, 'unified_game_automation')],
    binaries=[],
    datas=[
        ('unified_game_automation/Tesseract', 'Tesseract'),
        ('unified_game_automation/data/logo.ico', 'data'),
        ('unified_game_automation/data/logo.png', 'data'),
        (os.path.join(os.path.dirname(__import__('customtkinter').__file__)), 'customtkinter'),
    ],
    hiddenimports=[
        'PIL', 'PIL.Image', 'PIL.ImageTk', 'pywinauto', 'keyboard', 'mouse',
        'win32gui', 'win32con', 'win32ui', 'threading', 'tkinter.ttk',
        'pytesseract', 'customtkinter', 'darkdetect', 'numpy', 'cv2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'pandas', 'matplotlib', 'scipy', 'tensorflow', 'IPython', 'pytest',
        'ui.macro_tab', 'automation.macro_automation',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HelloK1TTY_Automation_NoMacro_V6.1.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
    icon='logo.ico',
)
