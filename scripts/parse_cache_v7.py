"""渲染 40 chunks * 1024 bytes ARGB, 多种排列方式"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

# palette 占 16-254, pixel_data 从 254 开始
# 假设: 40 chunks * 1024 bytes ARGB = 40960 bytes, 然后 97 bytes trailing
pixel_data = raw[254:]
print(f"pixel_data: {len(pixel_data)} bytes")
print(f"40 chunks * 1024 = {40 * 1024}, trailing = {len(pixel_data) - 40960}")

# 渲染 40 chunks, 每 chunk 16x16, 按不同排列
# 假设 chunks 是按 row-major 顺序 (cx 从 0..N, cz 从 0..M)
arrangements = [
    (8, 5, "8x5"),   # 128x80
    (5, 8, "5x8"),   # 80x128
    (10, 4, "10x4"), # 160x64
    (4, 10, "4x10"), # 64x160
    (20, 2, "20x2"), # 320x32
    (40, 1, "40x1"), # 640x16
    (1, 40, "1x40"), # 16x640
]

for ncols, nrows, name in arrangements:
    w = ncols * 16
    h = nrows * 16
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for chunk_idx in range(40):
        chunk_off = chunk_idx * 1024
        if chunk_off + 1024 > len(pixel_data):
            break
        cx = chunk_idx % ncols
        cz = chunk_idx // ncols
        for py in range(16):
            for px in range(16):
                idx = chunk_off + (py * 16 + px) * 4
                if idx + 3 < len(pixel_data):
                    a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    img.putpixel((abs_x, abs_y), (r, g, b, a))
    out_file = OUT / f"arrange_{name}_{w}x{h}.png"
    img.save(out_file)
    print(f"saved: {out_file}")

# 也渲染单个 chunk (前 1024 bytes) 放大
img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
for py in range(16):
    for px in range(16):
        idx = (py * 16 + px) * 4
        if idx + 3 < 1024:
            a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
            img.putpixel((px, py), (r, g, b, a))
img.resize((256, 256), Image.NEAREST).save(OUT / "single_chunk0.png")

# 渲染第 5 个 chunk (offset 5120)
img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
for py in range(16):
    for px in range(16):
        idx = 5 * 1024 + (py * 16 + px) * 4
        if idx + 3 < len(pixel_data):
            a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
            img.putpixel((px, py), (r, g, b, a))
img.resize((256, 256), Image.NEAREST).save(OUT / "single_chunk5.png")

# 渲染第 20 个 chunk
img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
for py in range(16):
    for px in range(16):
        idx = 20 * 1024 + (py * 16 + px) * 4
        if idx + 3 < len(pixel_data):
            a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
            img.putpixel((px, py), (r, g, b, a))
img.resize((256, 256), Image.NEAREST).save(OUT / "single_chunk20.png")

# 看看 trailing 97 bytes
trailing = pixel_data[40960:]
print(f"\ntrailing {len(trailing)} bytes:")
print(f"hex: {trailing.hex()}")
print(f"dec: {list(trailing)}")

# 尝试解析 trailing 为 40 个 (cx, cz) 坐标对
# 假设 1: 40 * 2 bytes = 80 bytes, 剩 17 bytes
print(f"\n--- trailing as 40 (cx,cz) byte pairs ---")
for i in range(min(40, len(trailing) // 2)):
    cx = trailing[i * 2]
    cz = trailing[i * 2 + 1]
    if cx >= 128:
        cx -= 256
    if cz >= 128:
        cz -= 256
    print(f"  chunk {i}: cx={cx}, cz={cz}")

print(f"\nall PNGs saved to {OUT}")
