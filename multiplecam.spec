# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['multiplecam.py'],
    pathex=[],
    binaries=[('libvlc.dll', '.'), ('libvlccore.dll', '.')],
    datas=[('16.png', '.'), ('32.png', '.'), ('48.png', '.'), ('64.png', '.'), ('cameras.json', '.'), ('plugins', 'plugins')],
    hiddenimports=[],
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
    name='multiplecam',
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
    icon=['logo.ico'],
)
