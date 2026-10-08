"""Prepare platform-specific app icons from the canonical PNG masters."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
ICON_ROOT = ROOT / "resources" / "icons"
MAC_SOURCE_PNG = ICON_ROOT / "DubbingManager-macOS-1024.png"
WIN_SOURCE_PNG = ICON_ROOT / "DubbingManager-Windows-1024.png"
ICONSET = ICON_ROOT / "DubbingManager.iconset"
ICNS_PATH = ICON_ROOT / "DubbingManager.icns"
ICO_PATH = ICON_ROOT / "DubbingManager.ico"

ICONSET_SIZES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}

ICO_SIZES = (16, 20, 24, 30, 32, 40, 48, 60, 64, 72, 96, 128, 256)
ICNS_TYPES = {
    16: b"ic04",
    32: b"ic05",
    64: b"ic06",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
    1024: b"ic10",
}


def load_source(path: Path) -> QImage:
    if not path.exists():
        raise FileNotFoundError(f"Icon source not found: {path}")

    image = QImage(str(path))
    if image.isNull():
        raise RuntimeError(f"Could not read icon source: {path}")
    return image


def scaled_png_bytes(image: QImage, size: int) -> bytes:
    scaled = image.scaled(
        size,
        size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    if not scaled.save(buffer, "PNG"):
        raise RuntimeError(f"Could not encode {size}x{size} PNG")
    return bytes(buffer.data())


def write_iconset(image: QImage) -> None:
    ICONSET.mkdir(parents=True, exist_ok=True)
    for filename, size in ICONSET_SIZES.items():
        target = ICONSET / filename
        data = scaled_png_bytes(image, size)
        target.write_bytes(data)


def write_ico(image: QImage) -> None:
    images = [(size, scaled_png_bytes(image, size)) for size in ICO_SIZES]
    header_size = 6 + 16 * len(images)
    offset = header_size
    entries = []

    for size, data in images:
        width = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                width,
                width,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        offset += len(data)

    payload = [
        struct.pack("<HHH", 0, 1, len(images)),
        *entries,
        *(data for _size, data in images),
    ]
    ICO_PATH.write_bytes(b"".join(payload))


def write_icns(image: QImage) -> None:
    chunks = []
    for size, icon_type in ICNS_TYPES.items():
        data = scaled_png_bytes(image, size)
        chunks.append(icon_type + struct.pack(">I", len(data) + 8) + data)

    body = b"".join(chunks)
    ICNS_PATH.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> None:
    mac_image = load_source(MAC_SOURCE_PNG)
    win_image = load_source(WIN_SOURCE_PNG)
    write_iconset(mac_image)
    write_ico(win_image)
    write_icns(mac_image)
    print(f"Prepared macOS app icon from {MAC_SOURCE_PNG}")
    print(f"Prepared Windows app icon from {WIN_SOURCE_PNG}")


if __name__ == "__main__":
    main()
