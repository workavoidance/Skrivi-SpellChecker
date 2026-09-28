# Local desktop build notices

Skrivi code is MIT; see the repository LICENSE. The family stylesheet is copied from
Skrivi-TTS `app/theme.py`, inspected at commit 47157cfe64279442551aae1016125b429b7d6941,
and retains its original attribution. Its native navigation follows Lytt/Snakk.

Qt for Python (PySide6 Essentials and Shiboken6) 6.11.2 is used under LGPLv3.
The license texts are included in licenses/. Qt libraries are dynamically loaded,
unmodified and separate from the executable. Users may replace compatible libraries
or rebuild this app with modified Qt; no restriction on that activity is imposed.
Upstream sources: https://code.qt.io/cgit/pyside/pyside-setup.git/ and
https://code.qt.io/cgit/qt/qtbase.git/ (version 6.11.2).
Python 3.14 is supplied by the packaging environment under the Python Software
Foundation license, copied into the packaged licenses directory.
PyInstaller uses its GPL license with bootloader distribution exception:
https://pyinstaller.org/en/stable/license.html

Nuspell, NorBERT and dictionaries are reused from the user's existing sandbox cache,
not bundled in this installer. They retain their respective notices and licenses.
Bokmaalsordboka: University of Bergen and the Language Council of Norway.
Dictionary redistribution clearance and a complete Store release audit remain
separate work; this package is a local test build, not a public release.
