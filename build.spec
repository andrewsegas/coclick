# PyInstaller spec for CoClick (onedir).
#
# Bundles the GUI + the bot engine and, if present, a vendored Tesseract-OCR
# under vendor/tesseract/ so the shipped exe needs no separate install.
# Build with:  py -m PyInstaller build.spec --noconfirm
import os
import sys

block_cipher = None

# PyInstaller can miss some low-level DLLs that Tcl/Tk (_tkinter) and ctypes
# depend on. On the build machine they load anyway because C:\PythonXX\DLLs is on
# PATH, so it "works here" but crashes on a clean machine with:
#   ImportError: DLL load failed while importing _tkinter
# Bundle them explicitly from the current Python so the shipped exe is standalone.
binaries = []
_pydlls = os.path.join(sys.base_prefix, "DLLs")
for _dll in ("zlib1.dll", "libffi-8.dll"):
    _p = os.path.join(_pydlls, _dll)
    if os.path.exists(_p):
        binaries.append((_p, "."))

# Heavy libraries that happen to be installed in the build environment but that
# CoClick never imports. pyautogui/pyscreeze pull cv2+numpy *optionally* for
# image matching (unused here), and others get dragged in transitively. Excluding
# them keeps the shipped package small.
excludes = [
    "torch", "torchvision", "torchaudio",
    "cv2", "opencv-python",
    "numpy", "scipy", "pandas", "sklearn", "matplotlib",
    "pyarrow",
    "imageio", "imageio_ffmpeg",
    "IPython", "notebook", "jupyter",
    "PyQt5", "PySide2", "PySide6", "PyQt6",
]

datas = []

# Ship a default config.ini (seeded next to the exe on first run).
if os.path.exists("config.ini"):
    datas.append(("config.ini", "."))

# Ship the whole vendored Tesseract folder (tesseract.exe + DLLs + tessdata)
# as data under "tesseract/". If it isn't vendored yet, the build still works,
# but the exe will fall back to a system Tesseract at runtime.
if os.path.isdir("vendor/tesseract"):
    datas.append(("vendor/tesseract", "tesseract"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=["pydirectinput", "PIL.ImageGrab"],
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
    name="CoClick",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX corrupts tkinter/tcl/tk DLLs -> intermittent "_tkinter DLL load failed"
    console=False,  # GUI app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="coclick.ico" if os.path.exists("coclick.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # see EXE(): UPX breaks tkinter DLLs
    upx_exclude=[],
    name="CoClick",
)
