import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def find_pixel_start_v1(raw):
    """旧方法: 找第一个 minecraft: 之前的位置"""
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
    px_start = off
    while px_start < len(raw) and raw[px_start] == 0:
        px_start += 1
    return px_start

def find_pixel_start_v2(raw):
    """新方法: 找最后一个 minecraft: 之后的位置"""
    pos = 16
    last_biome_end = 16
    while True:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1:
            break
        if idx > 0:
            slen = raw[idx-1]
            if 10 <= slen <= 64:
                name = raw[idx:idx+slen].decode('utf-8', errors='replace')
                if name.startswith('minecraft:'):
                    last_biome_end = idx + slen
                    pos = last_biome_end
                    continue
        pos = idx + 1
    px_start = last_biome_end
    while px_start < len(raw) and raw[px_start] == 0:
        px_start += 1
    return px_start

# 测试 cache/3/0_0.xwmc
raw = read_xwmc(3, 0, 0)
print(f"Total size: {len(raw)}")

v1 = find_pixel_start_v1(raw)
v2 = find_pixel_start_v2(raw)
print(f"v1 px_start: {v1}")
print(f"v2 px_start: {v2}")

# 用 v1 试试
pixel_data_v1 = raw[v1:]
print(f"\nv1 pixel_data size: {len(pixel_data_v1)}")
n_chunks_v1 = len(pixel_data_v1) // 1024
rem_v1 = len(pixel_data_v1) % 1024
print(f"v1: {n_chunks_v1} chunks, rem={rem_v1}")

# 用 v2 试试
pixel_data_v2 = raw[v2:]
print(f"\nv2 pixel_data size: {len(pixel_data_v2)}")
n_chunks_v2 = len(pixel_data_v2) // 1024
rem_v2 = len(pixel_data_v2) % 1024
print(f"v2: {n_chunks_v2} chunks, rem={rem_v2}")

# 用 v1 渲染第一个 chunk 看看
img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
chunk0 = pixel_data_v1[:1024]
for y in range(16):
    for x in range(16):
        idx = (y * 16 + x) * 4
        if idx + 3 < len(chunk0):
            a, r, g, b = chunk0[idx], chunk0[idx+1], chunk0[idx+2], chunk0[idx+3]
            img.putpixel((x, y), (r, g, b, a))
opaque = sum(1 for y in range(16) for x in range(16) if img.getpixel((x, y))[3] > 0)
print(f"\nv1 chunk0 opaque: {opaque}/256")
img.save(OUT / "v1_chunk0.png")

# 用 v2 渲染第一个 chunk
img2 = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
chunk0_v2 = pixel_data_v2[:1024]
for y in range(16):
    for x in range(16):
        idx = (y * 16 + x) * 4
        if idx + 3 < len(chunk0_v2):
            a, r, g, b = chunk0_v2[idx], chunk0_v2[idx+1], chunk0_v2[idx+2], chunk0_v2[idx+3]
            img2.putpixel((x, y), (r, g, b, a))
opaque2 = sum(1 for y in range(16) for x in range(16) if img2.getpixel((x, y))[3] > 0)
print(f"v2 chunk0 opaque: {opaque2}/256")
img2.save(OUT / "v2_chunk0.png")

# 看看 v1 的 trailing
trail_v1 = pixel_data_v1[n_chunks_v1 * 1024:]
print(f"\nv1 trailing: {len(trail_v1)} bytes")
print(f"  first 32: {trail_v1[:32].hex()}")

# 看看 v2 的 trailing
trail_v2 = pixel_data_v2[n_chunks_v2 * 1024:]
print(f"\nv2 trailing: {len(trail_v2)} bytes")
print(f"  first 32: {trail_v2[:32].hex()}")
