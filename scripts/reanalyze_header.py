import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def count_biomes(raw):
    """数 biome 数量"""
    pos = 16
    count = 0
    last_end = 16
    while True:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1:
            break
        if idx > 0:
            slen = raw[idx-1]
            if 10 <= slen <= 64:
                name = raw[idx:idx+slen].decode('utf-8', errors='replace')
                if name.startswith('minecraft:'):
                    count += 1
                    last_end = idx + slen
                    pos = last_end
                    continue
        pos = idx + 1
    return count, last_end

# 比较不同 level 的 0_0.xwmc
for level in ['1', '2', '3']:
    try:
        raw = read_xwmc(level, 0, 0)
        h = raw[:16]
        biome_count, last_end = count_biomes(raw)
        print(f"\n=== Level {level} ===")
        print(f"  Header hex: {h.hex()}")
        print(f"  Biome count (from strings): {biome_count}")
        print(f"  Last biome ends at: {last_end}")
        print(f"  Byte 10-11 (BE): {(h[10] << 8) | h[11]}")
        print(f"  Byte 12-13 (BE): {(h[12] << 8) | h[13]}")
        print(f"  Byte 14-15 (BE): {(h[14] << 8) | h[15]}")
        print(f"  Total size: {len(raw)}")
        print(f"  Data after biome palette: {len(raw) - last_end} bytes")
    except Exception as e:
        print(f"Level {level}: {e}")
