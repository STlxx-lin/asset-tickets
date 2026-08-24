import os
import struct
import sys
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, Qt

def png_to_ico(source_png: str, target_ico: str, sizes=None):
    """
    将 PNG 图片转为包含多尺寸标准图层的 Windows ICO 文件。
    支持 Vista+ 原生 PNG 封装的 ICO 格式（包含 16, 24, 32, 48, 64, 128, 256 分辨率）。
    """
    if sizes is None:
        sizes = [16, 24, 32, 48, 64, 128, 256]

    if not os.path.exists(source_png):
        raise FileNotFoundError(f"源图片不存在: {source_png}")

    orig_image = QImage(source_png)
    if orig_image.isNull():
        raise ValueError(f"无法读取源图片: {source_png}")

    images_data = []
    for s in sizes:
        scaled = orig_image.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        # 居中放置到正方形透明背景画布
        square_img = QImage(s, s, QImage.Format.Format_ARGB32_Premultiplied)
        square_img.fill(0)
        from PySide6.QtGui import QPainter
        painter = QPainter(square_img)
        x = (s - scaled.width()) // 2
        y = (s - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.end()

        # 导出为 PNG 字节流
        from PySide6.QtGui import QImageWriter
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        writer = QImageWriter(buffer, b"PNG")
        if not writer.write(square_img):
            raise RuntimeError(f"无法写入尺寸为 {s} 的 PNG 数据: {writer.errorString()}")
        buffer.close()
        png_bytes = bytes(byte_array.data())
        images_data.append((s, png_bytes))

    # 组装 ICO 二进制结构
    # ICONDIR: idReserved (2), idType (2), idCount (2)
    num_images = len(images_data)
    icondir = struct.pack("<HHH", 0, 1, num_images)

    # 计算图像数据起始偏移
    # 头部大小 = 6 (ICONDIR) + 16 * num_images (ICONDIRENTRYs)
    current_offset = 6 + 16 * num_images
    entries = []
    data_payload = bytearray()

    for size, png_bytes in images_data:
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        bytes_in_res = len(png_bytes)
        # ICONDIRENTRY: bWidth (1), bHeight (1), bColorCount (1), bReserved (1), wPlanes (2), wBitCount (2), dwBytesInRes (4), dwImageOffset (4)
        entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, bytes_in_res, current_offset)
        entries.append(entry)
        data_payload.extend(png_bytes)
        current_offset += bytes_in_res

    with open(target_ico, "wb") as f:
        f.write(icondir)
        for entry in entries:
            f.write(entry)
        f.write(data_payload)

    print(f"成功生成多尺寸 ICO 图标: {target_ico} (包含尺寸: {sizes})")
    return target_ico

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_png = os.path.join(project_root, "logo-ykohqv-s3wb4i-pck6c0.png")
    dst_ico = os.path.join(project_root, "app_icon.ico")
    png_to_ico(src_png, dst_ico)
