import zipfile
from pathlib import Path
import struct

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

# 比较不同 level 的 0_0.xwmc header
print("=== Comparing headers ===")
for level in ['1', '2', '3']:
    try:
        raw = read_xwmc(level, 0, 0)
        h = raw[:16]
        print(f"\nLevel {level}:")
        print(f"  hex: {h.hex()}")
        print(f"  total size: {len(raw)}")
        # 解析一些字段
        print(f"  byte 0: {h[0]}")
        print(f"  byte 1: {h[1]}")
        print(f"  byte 2-3 (BE u16): {(h[2] << 8) | h[3]}")
        print(f"  byte 4-5 (BE u16): {(h[4] << 8) | h[5]}")
        print(f"  byte 6-9 (BE u32): {struct.unpack('>I', h[6:10])[0]}")
        print(f"  byte 6-9 (LE u32): {struct.unpack('<I', h[6:10])[0]}")
        print(f"  byte 10-11 (BE u16): {(h[10] << 8) | h[11]}")
        print(f"  byte 12-13 (BE u16): {(h[12] << 8) | h[13]}")
        print(f"  byte 14-15 (BE u16): {(h[14] << 8) | h[15]}")
    except Exception as e:
        print(f"Level {level}: {e}")

# 比较同一 level 不同坐标的 header
print("\n\n=== Comparing level 3 headers ===")
files_to_check = [
    (3, 0, 0),
    (3, -1, 1),
    (3, 0, 1),
    (3, 1, 0),
    (3, 1, 1),
]
for level, tx, tz in files_to_check:
    try:
        raw = read_xwmc(level, tx, tz)
        h = raw[:16]
        print(f"\n  ({tx}, {tz}):")
        print(f"    hex: {h.hex()}")
        print(f"    size: {len(raw)}")
        print(f"    byte 6-9 (LE): {struct.unpack('<I', h[6:10])[0]}")
        print(f"    byte 6-9 (BE): {struct.unpack('>I', h[6:10])[0]}")
    except Exception as e:
        print(f"  ({tx}, {tz}): {e}")
