"""解压并分析 .xwmc (ZIP) 内的 cache.xaero 格式。"""
import zipfile
import struct
import io
from pathlib import Path

f = Path("1.19.2TOBU0405/XaeroWorldMap/新的世界/null/cache/1/0_0.xwmc")

with zipfile.ZipFile(f, "r") as zf:
    print(f"ZIP 内容: {zf.namelist()}")
    inner = zf.read("cache.xaero")
    print(f"cache.xaero 大小: {len(inner)} bytes")
    print(f"前 128 字节 (hex): {inner[:128].hex()}")

    # 分析二进制结构
    print("\n逐字节分析前 64 字节:")
    for i in range(0, min(64, len(inner))):
        b = inner[i]
        c = chr(b) if 32 <= b < 127 else "."
        print(f"  [{i:3d}] {b:3d} (0x{b:02x}) {c}")

    # Xaero 格式可能是: magic + version + width + height + pixel data
    # 尝试读取 header
    print("\n尝试解析 header:")
    if len(inner) >= 8:
        # 尝试不同的大端/小端组合
        for fmt, name in [(">II", "BE int32x2"), ("<II", "LE int32x2"), (">HHHH", "BE shortx4"), ("<HHHH", "LE shortx4")]:
            try:
                vals = struct.unpack_from(fmt, inner, 0)
                print(f"  {name}: {vals}")
            except:
                pass

    # 检查是否有 PNG/JPEG 嵌入
    png_pos = inner.find(b"\x89PNG")
    jpg_pos = inner.find(b"\xff\xd8\xff")
    print(f"\nPNG 位置: {png_pos}")
    print(f"JPEG 位置: {jpg_pos}")

    # 尝试直接作为图片加载
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(inner))
        print(f"PIL 直接加载成功: {img.size} {img.mode}")
    except Exception as e:
        print(f"PIL 直接加载失败: {e}")

    # 跳过可能的 header 后尝试加载
    for offset in [4, 8, 12, 16, 20, 24, 28, 32]:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(inner[offset:]))
            print(f"PIL 从 offset {offset} 加载成功: {img.size} {img.mode}")
            break
        except:
            pass
