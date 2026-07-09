"""调试 cache.xaero 解析器 - 逐步分析"""
import zipfile
import struct
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

raw = read_xwmc(3, 0, 0)
print(f"Total size: {len(raw)} bytes")
pos = 0

# 1. 版本号
version = struct.unpack('>I', raw[pos:pos+4])[0]
pos += 4
print(f"\n[1] Version: 0x{version:08X} ({version})")

# 2. 缓存元数据
print(f"\n[2] Cache metadata (texture inventory):")
textures_meta = []
while pos < len(raw):
    coord = raw[pos]
    pos += 1
    if coord == 0xFF:
        print(f"  Terminator at pos {pos-1}")
        break
    i = coord >> 4
    j = coord & 0x0F
    tex_ver = struct.unpack('>i', raw[pos:pos+4])[0]
    pos += 4
    textures_meta.append((i, j, tex_ver))
    print(f"  Texture ({i},{j}): version={tex_ver}")

print(f"  Total textures in metadata: {len(textures_meta)}")

# 3. 生物群系调色板
print(f"\n[3] Biome palette at pos {pos}:")
palette_size = struct.unpack('>i', raw[pos:pos+4])[0]
pos += 4
print(f"  Palette size: {palette_size}")

biome_palette = []
for idx in range(palette_size):
    marker = raw[pos]
    pos += 1
    if marker == 0xFF:
        biome_palette.append(None)
        print(f"  [{idx}] null")
    else:
        str_len = struct.unpack('>H', raw[pos:pos+2])[0]
        pos += 2
        name = raw[pos:pos+str_len].decode('utf-8', errors='replace')
        pos += str_len
        biome_palette.append(name)
        print(f"  [{idx}] {name} (len={str_len})")

print(f"  Palette end at pos: {pos}")

# 4. 纹理循环
print(f"\n[4] Texture loop at pos {pos}:")
tex_count = 0
while pos < len(raw):
    coord = raw[pos]
    pos += 1
    if coord == 0xFF:
        print(f"  Terminator at pos {pos-1}")
        break

    i = coord >> 4
    j = coord & 0x0F
    print(f"\n  Texture ({i},{j}) at pos {pos-1}:")

    # writeCacheMapData
    compressed = raw[pos]
    pos += 1
    print(f"    compressed: {compressed}")

    color_format = struct.unpack('>i', raw[pos:pos+4])[0]
    pos += 4
    print(f"    colorBufferFormat: {color_format} (0x{color_format:08X})")

    buf_length = struct.unpack('>i', raw[pos:pos+4])[0]
    pos += 4
    print(f"    bufferLength: {buf_length}")

    pixel_data = raw[pos:pos+buf_length]
    pos += buf_length
    print(f"    pixel data: {len(pixel_data)} bytes (first 8: {pixel_data[:8].hex()})")

    has_light = raw[pos]
    pos += 1
    print(f"    hasLight: {has_light}")

    # heightValues: 1024 longs = 8192 bytes
    remaining = len(raw) - pos
    print(f"    Remaining data: {remaining} bytes")
    
    if remaining < 8192:
        print(f"    *** NOT ENOUGH DATA for heightValues (need 8192, have {remaining}) ***")
        # 打印剩余数据
        print(f"    Remaining hex: {raw[pos:pos+min(64, remaining)].hex()}")
        break

    # 读取 heightValues
    pos += 8192
    print(f"    heightValues: 8192 bytes read, pos now {pos}")

    # topHeightValues: 1024 longs = 8192 bytes
    remaining = len(raw) - pos
    if remaining < 8192:
        print(f"    *** NOT ENOUGH DATA for topHeightValues (need 8192, have {remaining}) ***")
        break
    pos += 8192
    print(f"    topHeightValues: 8192 bytes read, pos now {pos}")

    # saveBiomeIndexStorage
    remaining = len(raw) - pos
    print(f"    Remaining for biomeIndex: {remaining} bytes")

    if remaining < 4:
        print(f"    *** NOT ENOUGH for palette size ***")
        break

    per_tex_pal_size = struct.unpack('>i', raw[pos:pos+4])[0]
    pos += 4
    print(f"    perTexturePaletteSize: {per_tex_pal_size}")

    for pidx in range(per_tex_pal_size):
        if pos + 4 > len(raw):
            print(f"      *** OUT OF DATA at palette entry {pidx} ***")
            break
        elem = struct.unpack('>i', raw[pos:pos+4])[0]
        pos += 4
        if elem != -1:
            if pos + 2 > len(raw):
                print(f"      *** OUT OF DATA for count ***")
                break
            count = struct.unpack('>h', raw[pos:pos+2])[0]
            pos += 2
            print(f"      [{pidx}] elem={elem}, count={count}")
        else:
            print(f"      [{pidx}] elem=-1 (null)")

    if pos < len(raw):
        marker_byte = raw[pos]
        pos += 1
        print(f"    marker byte: 0x{marker_byte:02X}")

    # 计算 bitsPerEntry
    needed_bits = 1
    val = per_tex_pal_size
    while val > 1:
        needed_bits += 1
        val >>= 1
    bits_per_entry = max(needed_bits, 1)
    inside_a_long = 64 // bits_per_entry
    data_len = (4096 + inside_a_long - 1) // inside_a_long
    biome_data_bytes = data_len * 8

    print(f"    bitsPerEntry: {bits_per_entry}, longs: {data_len}, bytes: {biome_data_bytes}")

    remaining = len(raw) - pos
    if remaining < biome_data_bytes:
        print(f"    *** NOT ENOUGH for biome indices (need {biome_data_bytes}, have {remaining}) ***")
        print(f"    Remaining hex: {raw[pos:pos+min(64, remaining)].hex()}")
        break
    pos += biome_data_bytes
    print(f"    biome indices: {biome_data_bytes} bytes read, pos now {pos}")

    tex_count += 1

print(f"\n=== Summary ===")
print(f"  Textures processed: {tex_count}")
print(f"  Final pos: {pos} / {len(raw)}")
print(f"  Remaining: {len(raw) - pos} bytes")
