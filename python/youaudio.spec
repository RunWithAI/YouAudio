# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Determine platform-specific settings
is_mac = sys.platform == 'darwin'
is_windows = sys.platform == 'win32'

# Base directory of your project
base_dir = os.getcwd()

# Get ffmpeg binary path based on platform
if is_mac:
    ffmpeg_binary = '/usr/local/bin/ffmpeg'  # Default Homebrew installation path
elif is_windows:
    ffmpeg_binary = 'ffmpeg\\ffmpeg.exe'  # Adjust this path for Windows

# Only include necessary static files
extra_files = [
    ('static/css/*.css', 'static/css'),
    ('static/js/*.js', 'static/js'),
    ('static/image/*', 'static/image'),  # Include all images
    ('templates/*.html', 'templates'),
    [(f'translations/{lang}/LC_MESSAGES/messages.mo', f'translations/{lang}/LC_MESSAGES') for lang in ['ko', 'en', 'es', 'fr']],
    ('config.json', '.'),
    (ffmpeg_binary, 'ffmpeg')  # Include ffmpeg binary
]

# Platform specific icon
if is_mac:
    icon_file = 'YouAudio.icns'
else:
    icon_file = 'icon.ico'

icon_src = os.path.join(base_dir, icon_file)

a = Analysis(
    ['server.py'],
    pathex=[base_dir],
    binaries=[],
    datas=[
        (ffmpeg_binary, 'ffmpeg'),
        ('static/css/*.css', 'static/css'),
        ('static/js/*.js', 'static/js'),
        ('static/image/*', 'static/image'),  # Include all images
        ('templates/*.html', 'templates'),
    ] + [
        (f'translations/{lang}/LC_MESSAGES/messages.mo', f'translations/{lang}/LC_MESSAGES') for lang in ['de', 'en', 'es', 'fr','it','ko', 'pt', 'zh_Hans', 'zh_Hant']
    ],
    hiddenimports=[
        'engineio.async_drivers.threading',
        'flask.app',
        'flask.helpers',
        'flask_cors',
        'flask_sock',
        'flask_babel',
        'Foundation',
        'AppKit',
        'objc',
        'PyObjC',
        'AppKit.NSApplication',
        'macos_app',
        'rumps',  # Add rumps for macOS menu
        'macos_menu'  # Add our menu module
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'notebook',
        'scipy',
        'pandas',
        'PIL.ImageQt',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'tkinter',
        'wx',
        'test',
        '_pytest',
        'IPython',
        'numpy',
        'cv2',
        'debugpy',
        'jedi',
        'setuptools',
        'pkg_resources',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove debug symbols and other unnecessary files
a.binaries = [x for x in a.binaries if not x[0].startswith('libpython')]
a.binaries = [x for x in a.binaries if not x[0].startswith('tcl')]
a.binaries = [x for x in a.binaries if not x[0].startswith('tk')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if is_mac:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='YouAudio',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,  # Strip debug symbols
        upx=True,
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon= icon_src if os.path.exists(icon_src) else None,
    )
    #icon=icon_src if os.path.exists(icon_src) else None,
    # Create the .app bundle with optimizations
    app = BUNDLE(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='YouAudio.app',
        icon= icon_src if os.path.exists(icon_src) else None,
        bundle_identifier='com.kejikeji.YouAudio',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'LSMinimumSystemVersion': '10.13.0',
            'LSApplicationCategoryType': 'public.app-category.music',
            'CFBundleDisplayName': 'YouAudio',
            'CFBundleName': 'YouAudio',
            'NSHighResolutionCapable': True,
            'NSAppTransportSecurity': {
                'NSAllowsArbitraryLoads': True
            },
            'CFBundleURLTypes': [{
                'CFBundleURLName': 'com.kejikeji.YouAudio',
                'CFBundleURLSchemes': ['youaudio']
            }],
            'NSSupportsAutomaticGraphicsSwitching': True,
            'LSUIElement': False  # This makes the app not show in dock
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,  # This ensures _internal directory creation
        name='YouAudio',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,  # Strip debug symbols
        upx=True,
        console=False,  # Set to False for windowed application
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_src if os.path.exists(icon_src) else None,
    )

    # Add COLLECT to bundle files in _internal directory
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=[],
        name='YouAudio'
    )