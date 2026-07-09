"""测试 biome index 的 bitsPerEntry: 4 vs 13
同时渲染像素数据验证地图可读性
"""
import zipfile
import struct
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"d:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def read_bitarray_longs(raw, pos, n_longs):
    """读取 n_longs 个 long (大端)"""
    longs = []
    for i in range(n_longs):
        val = struct.unpack('>q', raw[pos:pos+8])[0] & 0xFFFFFFFFFFFFFFFF
        pos += 8
        longs.append(val)
    return longs, pos

def decode_bitarray(longs, bits_per_entry, entries):
    """解码 ConsistentBitArray"""
    inside_a_long = 64 // bits_per_entry
    mask = (1 << bits_per_entry) - 1
    result = []
    for i in range(entries):
        idx = i // inside_a_long
        shift = (i % inside_a_long) * bits_per_entry
        val = (longs[idx] >> shift) & mask
        result.append(val)
    return result

raw = read_xwmc(3, 0, 0)
print(f"File size: {len(raw)} bytes")

# 解析到 biome index storage
pos = 0
version = struct.unpack('>I', raw[pos:pos+4])[0]; pos += 4
print(f"Version: 0x{version:08X}")

# metadata
textures_meta = []
while True:
    coord = raw[pos]; pos += 1
    if coord == 0xFF: break
    i = coord >> 4; j = coord & 0x0F
    tex_ver = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    textures_meta.append((i, j, tex_ver))
print(f"Metadata: {len(textures_meta)} textures")

# biome palette
pal_size = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
biome_palette = []
for _ in range(pal_size):
    marker = raw[pos]; pos += 1
    if marker == 0xFF:
        biome_palette.append(None)
    else:
        slen = struct.unpack('>H', raw[pos:pos+2])[0]; pos += 2
        name = raw[pos:pos+slen].decode('utf-8', errors='replace'); pos += slen
        biome_palette.append(name)
print(f"Biome palette: {len(biome_palette)} entries")

# 第一个纹理
coord = raw[pos]; pos += 1
ti = coord & 0x0F  # X axis (low nibble = i per spec section 6)
tj = coord >> 4    # Z axis (high nibble = j per spec section 6)
print(f"\nTexture coord: 0x{coord:02X} -> i={ti}, j={tj}")

compressed = raw[pos]; pos += 1
color_format = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
buf_length = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
pixel_data = raw[pos:pos+buf_length]; pos += buf_length
has_light = raw[pos]; pos += 1

print(f"compressed={compressed}, colorFormat={color_format}, bufLen={buf_length}, hasLight={has_light}")
print(f"pixel_data: {len(pixel_data)} bytes")

# heightValues: 13 bits x 4096 entries = 1024 longs
hv_longs, pos = read_bitarray_longs(raw, pos, 1024)
print(f"heightValues: 1024 longs read, pos={pos}")

# topHeightValues: 13 bits x 4096 entries = 1024 longs
thv_longs, pos = read_bitarray_longs(raw, pos, 1024)
print(f"topHeightValues: 1024 longs read, pos={pos}")

# saveBiomeIndexStorage
per_tex_pal_size = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
print(f"\nperTexturePaletteSize: {per_tex_pal_size}")

per_tex_palette = []
for _ in range(per_tex_pal_size):
    elem = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    if elem != -1:
        count = struct.unpack('>h', raw[pos:pos+2])[0]; pos += 2
        per_tex_palette.append((elem, count))
    else:
        per_tex_palette.append((-1, None))

marker = raw[pos]; pos += 1
print(f"marker byte: 0x{marker:02X}")
print(f"biome indices start at pos: {pos}")

# 测试 bpe=4
print("\n=== Testing bpe=4 ===")
inside_4 = 64 // 4  # 16
data_len_4 = (4096 + inside_4 - 1) // inside_4  # 256
biome_bytes_4 = data_len_4 * 8  # 2048
print(f"  data_len={data_len_4} longs, {biome_bytes_4} bytes")

longs_4, pos_after_4 = read_bitarray_longs(raw, pos, data_len_4)
indices_4 = decode_bitarray(longs_4, 4, 4096)
valid_4 = sum(1 for v in indices_4 if 0 <= v <= per_tex_pal_size)
print(f"  Valid indices (0-{per_tex_pal_size}): {valid_4}/{len(indices_4)}")
print(f"  Unique values: {sorted(set(indices_4))}")
print(f"  pos after: {pos_after_4}, remaining: {len(raw) - pos_after_4}")

# 测试 bpe=13
print("\n=== Testing bpe=13 ===")
inside_13 = 64 // 13  # 4
data_len_13 = (4096 + inside_13 - 1) // inside_13  # 1024
biome_bytes_13 = data_len_13 * 8  # 8192
print(f"  data_len={data_len_13} longs, {biome_bytes_13} bytes")

longs_13, pos_after_13 = read_bitarray_longs(raw, pos, data_len_13)
indices_13 = decode_bitarray(longs_13, 13, 4096)
valid_13 = sum(1 for v in indices_13 if 0 <= v <= per_tex_pal_size)
print(f"  Valid indices (0-{per_tex_pal_size}): {valid_13}/{len(indices_13)}")
print(f"  Unique values: {sorted(set(indices_13))[:20]}")
print(f"  pos after: {pos_after_13}, remaining: {len(raw) - pos_after_13}")

# 渲染像素数据为 PNG (64x64 RGBA)
print("\n=== Rendering pixel data ===")
# color_format = 32856 = GL_RGBA8, bytes are R, G, B, A
img = Image.frombytes('RGBA', (64, 64), pixel_data)
out_path = OUT / "texture_0_0_rgba.png"
img.save(out_path)
print(f"  Saved RGBA: {out_path}")

# 也试 ARGB (Java 可能用 ARGB 顺序)
img_argb = Image.new('RGBA', (64, 64))
for y in range(64):
    for x in range(64):
        idx = (y * 64 + x) * 4
        a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
        img_argb.putpixel((x, y), (r, g, b, a))
out_path2 = OUT / "texture_0_0_argb.png"
img_argb.save(out_path2)
print(f"  Saved ARGB: {out_path2}")

# 渲染 heightValues 为灰度图
hv = decode_bitarray(hv_longs, 13, 4096)
hv_img = Image.new('L', (64, 64))
min_hv = min(hv)
max_hv = max(hv)
print(f"  heightValues range: {min_hv} - {max_hv}")
for y in range(64):
    for x in range(64):
        idx = y * 64 + x
        val = hv[idx]
        normalized = int((val - min_hv) / max(1, max_hv - min_hv) * 255) if max_hv > min_hv else 0
        hv_img.putpixel((x, y), normalized)
out_path3 = OUT / "texture_0_0_heights.png"
hv_img.save(out_path3)
print(f"  Saved heights: {out_path3}")

# 检查 bpe=13 后的剩余数据
remaining_13 = raw[pos_after_13:]
print(f"\n=== Remaining data after bpe=13 indices: {len(remaining_13)} bytes ===")
if len(remaining_13) <= 20:
    print(f"  hex: {remaining_13.hex()}")
    print(f"  Last byte: 0x{remaining_13[-1]:02x}")
