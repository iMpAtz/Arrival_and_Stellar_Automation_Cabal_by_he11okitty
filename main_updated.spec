# -*- mode: python ; coding: utf-8 -*-
import os


a = Analysis(
    ['unified_game_automation/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('unified_game_automation/Tesseract', 'Tesseract'),
        ('unified_game_automation/data', 'data'),  # เพิ่มโฟลเดอร์ data ที่มีรูป Hello Kitty
        (os.path.join(os.path.dirname(__import__('customtkinter').__file__)), 'customtkinter'),
    ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'pywinauto',
        'keyboard',
        'mouse',
        'win32gui',
        'win32con',
        'win32ui',
        'threading',
        'tkinter.ttk',
        'pytesseract',
        'customtkinter',
        'darkdetect',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='HelloK1TTY_Automation_V6.0.5',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_dir=r'C:\Users\Hello\Desktop\upx',
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
