# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows build.

Run from the repository root:

    python -m PyInstaller ct-win.spec

Produces dist/ComicTranslate/ComicTranslate.exe.
"""
import os

block_cipher = None

# Paths are resolved against the repository root so the spec can be run from
# anywhere.
ROOT = os.path.abspath(os.getcwd())

datas = [
    ('resources', 'resources'),
]

# Loaded at runtime rather than by the import graph, so PyInstaller needs to be
# told about them explicitly.
hiddenimports = [
    'onnxruntime',
    'onnxruntime.capi._pybind_state',
    'shapely',
    'pyclipper',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageQt',
    'psutil',
    # Photoshop support is imported lazily behind an availability check.
    'PhotoshopAPI',
    # OCR backends are selected at runtime by language.
    'modules.ocr.manga_ocr.onnx_engine',
    'modules.ocr.pororo.onnx_engine',
    'modules.ocr.ppocr.engine',
    # Detector / inpainter backends likewise chosen at runtime.
    'modules.detection.rtdetr_v2_onnx',
    'modules.detection.ppocr_lines',
    'modules.detection.script_detection',
    'modules.inpainting.lama',
    'modules.inpainting.aot',
    'modules.inpainting.mi_gan',
]

excludes = [
    # Bundled Qt modules the app never touches; dropping them keeps the
    # executable from ballooning.
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
    'PySide6.Qt3DCore',
    'PySide6.Qt3DRender',
    'PySide6.QtBluetooth',
    'PySide6.QtCharts',
    'PySide6.QtDataVisualization',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'PySide6.QtQuick',
    'PySide6.QtQuick3D',
    'PySide6.QtQml',
    'PySide6.QtQuickWidgets',
    'PySide6.QtDesigner',
    'PySide6.QtHelp',
    'PySide6.QtSql',
    'PySide6.QtTest',
    'PySide6.QtWebSockets',
    'PySide6.QtPdf',
    'PySide6.QtPdfWidgets',
    'PySide6.QtSpatialAudio',
    'PySide6.QtSerialPort',
    'PySide6.QtPositioning',
    'PySide6.QtRemoteObjects',
    'PySide6.QtScxml',
    'PySide6.QtSensors',
    'PySide6.QtTextToSpeech',
    'PySide6.QtWebChannel',
    'PySide6.QtWebSockets',
    'tkinter',
    'test',
    'unittest',
]

a = Analysis(
    ['comic.py'],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ComicTranslate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'resources', 'icons', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ComicTranslate',
)