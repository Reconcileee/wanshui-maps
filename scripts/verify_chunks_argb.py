"""发现: RLE count 都在 64-128 之间, 16x16 chunk 每像素 4 bit biome index?

等等, 让我重新思考:
- cache/3/0_0.xwmc 有 41057 bytes pixel_data
- 之前假设 RLE, 但 count 都在 64-128
- 16x16 chunk = 256 像素, 如果每像素 4 bit biome index, 每 chunk 128 bytes
- 每 4 bytes = 8 个 4-bit 值
- count=64 可能意味着 64 个 4-bit 值 = 32 bytes?
- 不对

另一个角度:
- 第一个 chunk 用了 26 RLE runs, 共 1853 像素
- 1853 像素 / 16 = 115.8 行
- 不对, 16x16 只有 256 像素

让我重新看 cache/3/0_0.xwmc
pixel_data = 41057 bytes
如果每 chunk 1024 bytes, 40 chunks = 40960 bytes, 剩 97 bytes

每 chunk 1024 bytes 存 16x16 = 256 像素, 每像素 4 bytes = 1024 bytes
对! 16x16x4 = 1024

但 RLE 只解码了 1853 像素就遇到了 count=0
这意味着 count=0 不是结束, 而是格式的一部分

让我重新看: 每 chunk 1024 bytes ARGB
但第一个 1024 bytes 中, offset 104 开始全是 0
104 bytes = 26 个 4-byte 值 = 26 个像素是有色的, 其余 230 个像素是 0 (透明)
对! 26 个有色像素 + 230 个透明像素 = 256 像素
每个像素 4 bytes = 1024 bytes

等等, 1024 / 4 = 256, 正好是 16x16
所以格式就是: 每 chunk 1024 bytes = 256 个 ARGB 像素
顺序是 row-major

那 40 个 chunks = 40 * 1024 = 40960 bytes
剩余 41057 - 40960 = 97 bytes 是 trailing metadata

让我验证: 40 个 chunks, 每个 16x16 ARGB = 1024 bytes
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def get_pixel_data(raw):
    """从 cache.xaero 提取 pixel_data 起始位置"""
    first_mc = raw.find(b'minecraft:')
    pal_start = first_mc - 1
    off = pal_start
    while off < len(raw):
        slen = raw[off]
        if slen < 10 or slen > 64:
            if raw[off+1:].find(b'minecraft:') >= 0:
                off += 1
                continue
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        off += 1 + slen
    # 跳过末尾 0
    px_start = off
    while px_start < len(raw) and raw[px_start] == 0:
        px_start += 1
    return px_start

# 验证 cache/3/0_0.xwmc: 40 chunks of 1024 bytes ARGB
fn = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

px_start = get_pixel_data(raw)
pixel_data = raw[px_start:]
print(f"cache/3/0_0.xwmc: pixel_start={px_start}, pixel_data={len(pixel_data)}")
print(f"40 chunks * 1024 = {40 * 1024}, remainder = {len(pixel_data) - 40 * 1024}")

# 渲染 40 chunks 为 8x5 网格 (128x80)
img = Image.new('RGBA', (8 * 16, 5 * 16), (0, 0, 0, 0))
for ci in range(40):
    chunk_off = ci * 1024
    if chunk_off + 1024 > len(pixel_data):
        break
    cx = ci % 8
    cz = ci // 8
    for py in range(16):
        for px in range(16):
            idx = chunk_off + (py * 16 + px) * 4
            if idx + 3 < len(pixel_data):
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                abs_x = cx * 16 + px
                abs_y = cz * 16 + py
                img.putpixel((abs_x, abs_y), (r, g, b, a))

img.save(OUT / "chunks40_8x5_argb.png")
print("saved: chunks40_8x5_argb.png")

# 也试 5x8
img2 = Image.new('RGBA', (5 * 16, 8 * 16), (0, 0, 0, 0))
for ci in range(40):
    chunk_off = ci * 1024
    if chunk_off + 1024 > len(pixel_data):
        break
    cx = ci % 5
    cz = ci // 5
    for py in range(16):
        for px in range(16):
            idx = chunk_off + (py * 16 + px) * 4
            if idx + 3 < len(pixel_data):
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                abs_x = cx * 16 + px
                abs_y = cz * 16 + py
                img2.putpixel((abs_x, abs_y), (r, g, b, a))
img2.save(OUT / "chunks40_5x8_argb.png")
print("saved: chunks40_5x8_argb.png")

# 试 10x4
img3 = Image.new('RGBA', (10 * 16, 4 * 16), (0, 0, 0, 0))
for ci in range(40):
    chunk_off = ci * 1024
    if chunk_off + 1024 > len(pixel_data):
        break
    cx = ci % 10
    cz = ci // 10
    for py in range(16):
        for px in range(16):
            idx = chunk_off + (py * 16 + px) * 4
            if idx + 3 < len(pixel_data):
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                abs_x = cx * 16 + px
                abs_y = cz * 16 + py
                img3.putpixel((abs_x, abs_y), (r, g, b, a))
img3.save(OUT / "chunks40_10x4_argb.png")
print("saved: chunks40_10x4_argb.png")

# 现在看 trailing 97 bytes - 应该包含 chunk 坐标
trailing = pixel_data[40 * 1024:]
print(f"\ntrailing: {len(trailing)} bytes")
print(f"hex: {trailing.hex()}")

# 关键验证: 如果 tile 是 24x24 chunks, 而每个 .xwmc 文件只包含部分 chunks (稀疏)
# 那 trailing 应该是 chunk 坐标列表
# 40 chunks * 2 bytes (cx, cz) = 80 bytes
# 97 - 80 = 17 bytes header?

# 或者: trailing 开头有 chunk count
# 97 bytes = 1 byte count + 40 * 2 bytes coords + 16 bytes?
# 不对, 40 * 2 = 80, + 1 = 81, 剩 16 bytes

# 让我看看 trailing 中是否有 cx, cz 在 0-23 范围 (24 chunks)
print(f"\n--- trying 2-byte coords (cx, cz) 0-23 ---")
# 跳过前 N bytes header
for header_size in [0, 1, 2, 4, 8, 16, 17]:
    coords_data = trailing[header_size:]
    n_pairs = len(coords_data) // 2
    valid = 0
    coords = []
    for i in range(n_pairs):
        cx = coords_data[i*2]
        cz = coords_data[i*2 + 1]
        if 0 <= cx <= 23 and 0 <= cz <= 23:
            valid += 1
            coords.append((cx, cz))
    if valid > 30:  # 至少 30 个有效坐标
        print(f"  header_size={header_size}: {valid}/{n_pairs} valid coords (0-23)")
        print(f"    coords: {coords[:10]}...")

# 也试试带符号 (-128 ~ 127)
print(f"\n--- trying 2-byte signed coords ---")
for header_size in [0, 1, 2, 4, 8, 16, 17]:
    coords_data = trailing[header_size:]
    n_pairs = len(coords_data) // 2
    valid = 0
    coords = []
    for i in range(n_pairs):
        cx = coords_data[i*2]
        cz = coords_data[i*2 + 1]
        if cx >= 128:
            cx -= 256
        if cz >= 128:
            cz -= 256
        if -24 <= cx <= 23 and -24 <= cz <= 23:
            valid += 1
            coords.append((cx, cz))
    if valid > 30:
        print(f"  header_size={header_size}: {valid}/{n_pairs} valid coords (±24)")
        print(f"    coords: {coords[:10]}...")
