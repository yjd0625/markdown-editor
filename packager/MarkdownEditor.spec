# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['webview', 'webview.platforms.edgechromium']
hiddenimports += collect_submodules('webview')


a = Analysis(
    ['C:\\Users\\zpmc\\WorkBuddy\\2026-07-21-10-16-14\\packager\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\zpmc\\WorkBuddy\\2026-07-21-10-16-14\\packager\\..\\index.html', '.'), ('C:\\Users\\zpmc\\WorkBuddy\\2026-07-21-10-16-14\\packager\\..\\vendor', 'vendor')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
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
    name='MarkdownEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
