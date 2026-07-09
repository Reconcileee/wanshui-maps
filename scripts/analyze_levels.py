"""分析不同 zoom level 的文件大小关系

cache/3: 7 个文件, 每个 ~41KB
cache/2: 10 个文件, 每个 ~164KB
cache/1: 21 个文件, 每个 ~492KB

尺寸比例:
cache/2 vs cache/3: 164/41 = 4x (正好 4 倍!)
cache/1 vs cache/2: 492/164 = 3x? 不太对, 492/164=3

但如果每个 zoom level 是 2x 分辨率, 面积应该是 4x
41 * 4 = 164 * 4 = 656 (但 cache/1 是 492, 不是 656)

等等, 让我精确计算
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

for level in ["3", "2", "1"]:
    d = BASE / level
    files = sorted(d.glob("*.xwmc"))
    sizes = []
    for fn in files:
        with zipfile.ZipFile(fn) as z:
            raw = z.read("cache.xaero")
        sizes.append(len(raw))
    avg = sum(sizes) / len(sizes) if sizes else 0
    print(f"cache/{level}/: {len(files)} files, sizes={sizes[:5]}{'...' if len(sizes)>5 else ''}, avg={avg:.0f}")

# 如果 zoom 3 是 24 chunks * 24 chunks, 每个 chunk 16x16 = 384x384 像素
# zoom 2 应该是 48x48 chunks? 不对, 低 zoom 应该是少 chunks
# 但 cache/2 文件比 cache/3 大 4 倍, 说明 cache/2 分辨率更高

# 实际上: Xaero 的 zoom level 数字越小, 分辨率越高
# cache/1/ 是最详细的 (每像素 1 block?)
# cache/3/ 是缩小的

# 但文件数量: cache/1/ 21 个, cache/2/ 10 个, cache/3/ 7 个
# 高 zoom (低分辨率) 应该需要更少的 tile, 符合

# 让我直接渲染 ARGB 数据看看
print("\n=== Rendering ARGB data ===")
for level, fname in [("3", "0_0.xwmc"), ("2", "0_0.xwmc"), ("1", "0_0.xwmc")]:
    fn = BASE / level / fname
    if not fn.exists():
        print(f"{fn} not found")
        continue
    with zipfile.ZipFile(fn) as z:
        raw = z.read("cache.xaero")

    # 找 palette end
    biome_count = (raw[12] << 8) | raw[13]
    off = 16
    for i in range(biome_count):
        if off >= len(raw):
            break
        slen = raw[off]
        off += 1
        off += slen
        if off + 1 < len(raw) and raw[off] == 0 and raw[off+1] == 0:
            off += 2

    pixel_start = off
    pixel_data = raw[pixel_start:]
    n_pixels = len(pixel_data) // 4
    extra = len(pixel_data) % 4

    print(f"\n{level}/{fname}: total={len(raw)}, pixel_start={pixel_start}, pixel_data={len(pixel_data)} = {n_pixels}px + {extra}b extra")
    print(f"  extra bytes: {pixel_data[n_pixels*4:].hex() if extra else 'none'}")

    # 尝试渲染为不同尺寸
    OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
    OUT.mkdir(exist_ok=True)

    # 试 256x?
    for w in [256, 384, 512, 1024]:
        h = n_pixels // w
        if h > 0 and h < 5000:
            print(f"  try {w}x{h} = {w*h}px")
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            for i in range(w * h):
                a, r, g, b = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
                img.putpixel((i % w, i // w), (r, g, b, a))
            img.save(OUT / f"level{level}_{w}x{h}.png")
