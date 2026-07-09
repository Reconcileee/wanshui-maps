"""用 ARGB 渲染 cache/1/0_0.xwmc 的 560 个 chunks

假设:
- 每 chunk 1024 bytes ARGB (16x16 像素)
- cache/1: 560 chunks, 24x24 tile = 576, 缺 16 个
- 24 chunks per side, 16 pixels per chunk = 384x384 像素 per tile

验证: 如果是 24x24 = 576 chunks, 但只有 560 个有数据 (稀疏)
那数据格式应该是: 有数据的 chunks 按顺序排列, trailing 记录哪些 chunk 有数据

或者: 格式是 576 chunks, 但未探索的 chunks 用 0 填充
576 * 1024 = 589824 bytes
但 pixel_data 只有 574261 bytes, 不够

让我直接渲染看看结果
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def get_pixel_start(raw):
    first = raw.find(b'minecraft:')
    off = first - 1
    while off < len(raw):
        slen = raw[off]
        if slen < 10 or slen > 64:
            # 找下一个 minecraft:
            nxt = raw[off+1:].find(b'minecraft:')
            if nxt >= 0:
                off = off + 1 + nxt - 1
                continue
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        off += 1 + slen
    return off

# 渲染 cache/1/0_0.xwmc
fn = BASE / "1" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

px_start = get_pixel_start(raw)
pixel_data = raw[px_start:]
n_chunks = len(pixel_data) // 1024
rem = len(pixel_data) % 1024
print(f"cache/1/0_0.xwmc: {n_chunks} chunks, rem={rem}")

# 渲染为 24x24 chunks (384x384 像素) - 假设按行优先, 稀疏
# 但 560 != 576, 所以不是完整的

# 试试渲染为连续的 w x h, 看哪个比例合理
# 560 chunks = 28x20 = 560? 28*20=560
# 或 35x16 = 560? 
# 或 40x14 = 560?
# 或 56x10 = 560?

# 试试几个
for ncols, nrows, name in [(24, 24, "24x24"), (28, 20, "28x20"), (35, 16, "35x16"), (40, 14, "40x14"), (56, 10, "56x10")]:
    w = ncols * 16
    h = nrows * 16
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for ci in range(min(n_chunks, ncols * nrows)):
        chunk_off = ci * 1024
        cx = ci % ncols
        cz = ci // ncols
        for py in range(16):
            for px in range(16):
                idx = chunk_off + (py * 16 + px) * 4
                if idx + 3 < len(pixel_data):
                    a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    if abs_x < w and abs_y < h:
                        img.putpixel((abs_x, abs_y), (r, g, b, a))
    out_file = OUT / f"level1_{name}.png"
    img.save(out_file)
    print(f"  saved {name} ({w}x{h}): {out_file.name}")

# 也渲染 cache/2 的 160 chunks
fn2 = BASE / "2" / "0_0.xwmc"
with zipfile.ZipFile(fn2) as z:
    raw2 = z.read("cache.xaero")
px_start2 = get_pixel_start(raw2)
pd2 = raw2[px_start2:]
nc2 = len(pd2) // 1024
print(f"\ncache/2/0_0.xwmc: {nc2} chunks")

for ncols, nrows, name in [(12, 14, "12x14"), (16, 10, "16x10"), (20, 8, "20x8"), (24, 7, "24x7"), (10, 16, "10x16")]:
    if ncols * nrows != nc2:
        continue
    w = ncols * 16
    h = nrows * 16
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for ci in range(nc2):
        chunk_off = ci * 1024
        cx = ci % ncols
        cz = ci // ncols
        for py in range(16):
            for px in range(16):
                idx = chunk_off + (py * 16 + px) * 4
                if idx + 3 < len(pd2):
                    a, r, g, b = pd2[idx], pd2[idx+1], pd2[idx+2], pd2[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    if abs_x < w and abs_y < h:
                        img.putpixel((abs_x, abs_y), (r, g, b, a))
    out_file = OUT / f"level2_{name}.png"
    img.save(out_file)
    print(f"  saved {name} ({w}x{h}): {out_file.name}")

# cache/3: 40 chunks
fn3 = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(fn3) as z:
    raw3 = z.read("cache.xaero")
px_start3 = get_pixel_start(raw3)
pd3 = raw3[px_start3:]
nc3 = len(pd3) // 1024
print(f"\ncache/3/0_0.xwmc: {nc3} chunks")

for ncols, nrows, name in [(8, 5, "8x5"), (10, 4, "10x4"), (5, 8, "5x8"), (4, 10, "4x10"), (20, 2, "20x2")]:
    if ncols * nrows != nc3:
        continue
    w = ncols * 16
    h = nrows * 16
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for ci in range(nc3):
        chunk_off = ci * 1024
        cx = ci % ncols
        cz = ci // ncols
        for py in range(16):
            for px in range(16):
                idx = chunk_off + (py * 16 + px) * 4
                if idx + 3 < len(pd3):
                    a, r, g, b = pd3[idx], pd3[idx+1], pd3[idx+2], pd3[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    if abs_x < w and abs_y < h:
                        img.putpixel((abs_x, abs_y), (r, g, b, a))
    out_file = OUT / f"level3_{name}.png"
    img.save(out_file)
    print(f"  saved {name} ({w}x{h}): {out_file.name}")
