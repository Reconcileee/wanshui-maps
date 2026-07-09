"""调试失败的 cache 文件"""
import zipfile
import struct
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def hexdump(data, start, length, label=""):
    end = min(start + length, len(data))
    print(f"\n--- {label} (pos {start}-{end}) ---")
    for i in range(start, end, 16):
        chunk = data[i:min(i+16, end)]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {i:6d}: {hex_str:<48s}  {ascii_str}")

def debug_file(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    if not path.exists():
        print(f"Not found: {path}")
        return
    with zipfile.ZipFile(path) as z:
        raw = z.read("cache.xaero")
    print(f"\n{'='*60}")
    print(f"File: cache/{level}/{tx}_{tz}.xwmc ({len(raw)} bytes)")
    print(f"{'='*60}")

    hexdump(raw, 0, 48, "HEADER")

    pos = 0
    version = struct.unpack('>I', raw[pos:pos+4])[0]; pos += 4
    print(f"\nVersion: 0x{version:08X} ({version})")

    # metadata
    print(f"\nMetadata:")
    tex_count = 0
    while pos < len(raw):
        coord = raw[pos]; pos += 1
        if coord == 0xFF:
            print(f"  Terminator at pos {pos-1}")
            break
        i = coord & 0x0F; j = coord >> 4
        if pos + 4 > len(raw):
            print(f"  ERROR: not enough bytes for version at pos {pos}")
            return
        tex_ver = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
        print(f"  Texture (i={i}, j={j}): version={tex_ver}")
        tex_count += 1
    print(f"  Total: {tex_count} textures")

    # biome palette
    if pos + 4 > len(raw):
        print(f"\nERROR: not enough bytes for palette size at pos {pos}")
        return
    pal_size = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    print(f"\nBiome palette size: {pal_size}")

    for idx in range(pal_size):
        if pos >= len(raw):
            print(f"  ERROR: out of data at palette entry {idx}")
            return
        marker = raw[pos]; pos += 1
        if marker == 0xFF:
            print(f"  [{idx}] null")
        else:
            if pos + 2 > len(raw):
                print(f"  ERROR: out of data for string length at entry {idx}")
                return
            slen = struct.unpack('>H', raw[pos:pos+2])[0]; pos += 2
            if pos + slen > len(raw):
                print(f"  ERROR: out of data for string at entry {idx} (slen={slen})")
                return
            name = raw[pos:pos+slen].decode('utf-8', errors='replace'); pos += slen
            print(f"  [{idx}] {name}")

    print(f"\nTexture loop at pos {pos}:")

    # First texture
    if pos >= len(raw):
        print(f"  ERROR: no texture data")
        return
    coord = raw[pos]; pos += 1
    if coord == 0xFF:
        print(f"  Immediate terminator")
        return
    i = coord & 0x0F; j = coord >> 4
    print(f"  Texture (i={i}, j={j}) at pos {pos-1}")

    if pos + 1 > len(raw):
        print(f"    ERROR: out of data for compressed flag")
        return
    compressed = raw[pos]; pos += 1
    print(f"    compressed: {compressed}")

    if pos + 4 > len(raw):
        print(f"    ERROR: out of data for colorFormat (remaining={len(raw)-pos})")
        hexdump(raw, pos, min(16, len(raw)-pos), "REMAINING")
        return
    color_fmt = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    print(f"    colorFormat: {color_fmt} (0x{color_fmt:08X})")

    if pos + 4 > len(raw):
        print(f"    ERROR: out of data for bufferLength")
        return
    buf_len = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    print(f"    bufferLength: {buf_len}")

    if buf_len < 0 or buf_len > 100000:
        print(f"    WARNING: bufferLength seems invalid: {buf_len}")
        hexdump(raw, pos-8, min(32, len(raw)-pos+8), "AROUND BUFFER LENGTH")
        return

    if pos + buf_len > len(raw):
        print(f"    ERROR: not enough data for pixels (need {buf_len}, have {len(raw)-pos})")
        return
    pos += buf_len
    print(f"    pixel data: {buf_len} bytes, pos now {pos}")

    # hasLight
    if pos >= len(raw):
        print(f"    ERROR: out of data for hasLight")
        return
    has_light = raw[pos]; pos += 1
    print(f"    hasLight: {has_light}")

    # Check if we have enough for height arrays (8192 + 8192 = 16384)
    remaining = len(raw) - pos
    print(f"    Remaining after pixel+light: {remaining} bytes")

    if remaining < 16384:
        print(f"    NOTE: Not enough for 2x 8192-byte height arrays")
        print(f"    Maybe this level uses smaller arrays?")
        # Try to figure out what's here
        hexdump(raw, pos, min(64, remaining), "AFTER PIXEL DATA")

# Debug several failing files
for level, tx, tz in [(1, 0, 0), (1, -1, 5), (2, 0, 0), (3, 1, 0)]:
    debug_file(level, tx, tz)
