# -*- mode: python ; coding: utf-8 -*-
"""
mikrotik.spec
PyInstaller build spec for MikroTik Auto Login.
Works for Linux and Windows (run PyInstaller on the target OS).

Build commands:
  Linux  :  pyinstaller mikrotik.spec
  Windows:  pyinstaller mikrotik.spec
"""

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Collect kivy and cryptography dynamic submodules
hidden_imports = (
    collect_submodules('kivy')
    + collect_submodules('cryptography')
    + ['pkg_resources.py2_warn']
)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('data', 'data'),          # icon.png, developer.png, config.json, .secret.key
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['selenium', 'matplotlib', 'numpy', 'pandas', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MikroTikAutoLogin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,         # No terminal window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='data/icon.png',  # .ico on Windows, .png/.icns on Linux/macOS
)
