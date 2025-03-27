# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py',
     'srv/__init__.py', 'srv/app.py', 'srv/base.py', 'srv/cors.py', 'srv/model.py',
      'srv/home/__init__.py', 'srv/home/view.py', 'srv/util.py',
      'srv/proj/__init__.py', 'srv/proj/api.py', 'srv/proj/api_cb.py', 'srv/proj/view.py',
      'srv/proj/api_match.py', 'srv/proj/api_note.py', 'srv/proj/model.py',
      'srv/public/__init__.py', 'srv/public/invalid.py', 'srv/public/ui_module.py',
      'srv/user/__init__.py', 'srv/user/api.py', 'srv/user/model.py', 'srv/user/view.py'],
    pathex=[],
    binaries=[],
    datas=[('views', 'views'),
        ('doc', 'doc'),
        ('assets', 'assets'),
        ('app.yml', '.')],
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
    [],
    exclude_binaries=True,
    name='duidu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='duidu',
)
app = BUNDLE(
    coll,
    name='duidu.app',
    icon=None,
    bundle_identifier=None,
)
