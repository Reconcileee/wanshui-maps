"""验证 RLE 假设: 1 byte count + 3 byte RGB

假设:
  每 chunk 1024 bytes, 内是 RLE 编码的 RGB 数据
  格式: count(1 byte) + R(1 byte) + G(1 byte) + B(1 byte)
  每个 run 代表 count 个相同颜色的像素
  共 256 像素 (16x16)

验证: 所有 chunk 的 RLE 解码后应正好 256 像素
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def decode_rle(data):
    """1 byte count + 3 bytes RGB, 解码为 256 像素列表"""
    pixels = []
    off = 0
    while off < len(data) and len(pixels) < 256:
        if off + 4 > len(data):
            break
        count = data[off]
        r, g, b = data[off+1], data[off+2], data[off+3]
        for _ in range(min(count, 256 - len(pixels))):
            pixels.append((r, g, b))
        off += 4
    return pixels, off

# 测试单个文件
f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

# 跳过 16 + palette
palette_end = 254
pixel_data = raw[palette_end:]
print(f"pixel_data size: {len(pixel_data)}")

# 验证 40 个 chunk
print("\n=== Verifying 40 chunks RLE ===")
all_chunks_ok = True
for chunk_idx in range(40):
    chunk_off = chunk_idx * 1024
    if chunk_off + 1024 > len(pixel_data):
        break
    chunk_data = pixel_data[chunk_off:chunk_off + 1024]
    pixels, used = decode_rle(chunk_data)
    is_256 = len(pixels) == 256
    if not is_256:
        all_chunks_ok = False
    print(f"  chunk {chunk_idx:2d}: {len(pixels)} pixels, used {used}/1024 bytes, OK={is_256}")

print(f"\nAll 256 pixels: {all_chunks_ok}")

# 渲染所有 40 chunks 为 8x5 网格
img = Image.new('RGB', (8*16, 5*16), (0, 0, 0))
for chunk_idx in range(40):
    chunk_off = chunk_idx * 1024
    if chunk_off + 1024 > len(pixel_data):
        break
    chunk_data = pixel_data[chunk_off:chunk_off + 1024]
    pixels, _ = decode_rle(chunk_data)
    cx = chunk_idx % 8
    cz = chunk_idx // 8
    for i, (r, g, b) in enumerate(pixels):
        px = cx * 16 + (i % 16)
        py = cz * 16 + (i // 16)
        if px < img.width and py < img.height:
            img.putpixel((px, py), (r, g, b))

out_file = OUT / "rle_8x5_chunks.png"
img.save(out_file)
print(f"saved: {out_file}")

# 也渲染 10x4 网格
img2 = Image.new('RGB', (10*16, 4*16), (0, 0, 0))
for chunk_idx in range(40):
    chunk_off = chunk_idx * 1024
    if chunk_off + 1024 > len(pixel_data):
        break
    chunk_data = pixel_data[chunk_off:chunk_off + 1024]
    pixels, _ = decode_rle(chunk_data)
    cx = chunk_idx % 10
    cz = chunk_idx // 10
    for i, (r, g, b) in enumerate(pixels):
        px = cx * 16 + (i % 16)
        py = cz * 16 + (i // 16)
        if px < img2.width and py < img2.height:
            img2.putpixel((px, py), (r, g, b))
out_file2 = OUT / "rle_10x4_chunks.png"
img2.save(out_file2)
print(f"saved: {out_file2}")

# 单个 chunk 放大
for ci in [0, 5, 20, 30]:
    chunk_off = ci * 1024
    chunk_data = pixel_data[chunk_off:chunk_off + 1024]
    pixels, _ = decode_rle(chunk_data)
    img = Image.new('RGB', (16, 16), (0, 0, 0))
    for i, (r, g, b) in enumerate(pixels):
        img.putpixel((i % 16, i // 16), (r, g, b))
    img.resize((256, 256), Image.NEAREST).save(OUT / f"rle_chunk{ci}.png")

print(f"\nall PNGs saved to {OUT}")
