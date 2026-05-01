"""Prepare app icons from the Icon Composer export."""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
ICON_ROOT = ROOT / "resources" / "icons"
ICON_EXPORTS = ICON_ROOT / "Icon Exports"
SOURCE_PNG = ICON_EXPORTS / "Icon-macOS-Default-1024x1024@1x.png"
SOURCE_COPY = ICON_ROOT / "dubbing-manager-icon-source.png"
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

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICNS_TYPES = {
    16: b"ic04",
    32: b"ic05",
    64: b"ic06",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
    1024: b"ic10",
}


def load_source() -> QImage:
    if not SOURCE_PNG.exists():
        raise FileNotFoundError(f"Icon source not found: {SOURCE_PNG}")

    image = QImage(str(SOURCE_PNG))
    if image.isNull():
        raise RuntimeError(f"Could not read icon source: {SOURCE_PNG}")
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
    image = load_source()
    shutil.copyfile(SOURCE_PNG, SOURCE_COPY)
    write_iconset(image)
    write_ico(image)
    write_icns(image)
    print(f"Prepared app icons from {SOURCE_PNG}")


if __name__ == "__main__":
    main()
