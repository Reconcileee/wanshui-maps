import zipfile
from pathlib import Path
import struct

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

raw = read_xwmc(3, 0, 0)
print(f"Total size: {len(raw)} bytes")

# 打印 offset 195-300 的内容
print("\n=== Bytes 195-300 ===")
for i in range(195, min(300, len(raw))):
    b = raw[i]
    ascii_char = chr(b) if 32 <= b < 127 else '.'
    print(f"  offset {i:3d}: 0x{b:02x} ({b:3d})  '{ascii_char}'")

# 找所有 minecraft: 字符串
print("\n=== All biome strings ===")
pos = 0
biomes = []
while True:
    idx = raw.find(b'minecraft:', pos)
    if idx == -1:
        break
    if idx > 0:
        slen = raw[idx-1]
        if 10 <= slen <= 64:
            name = raw[idx:idx+slen].decode('utf-8', errors='replace')
            if name.startswith('minecraft:'):
                biomes.append((idx-1, slen, name))
                pos = idx + slen
                continue
    pos = idx + 1

for i, (off, slen, name) in enumerate(biomes):
    print(f"  biome {i}: off={off}, len={slen}, {name}")

print(f"\nTotal biomes: {len(biomes)}")
last_end = biomes[-1][0] + 1 + biomes[-1][1] if biomes else 16
print(f"Last biome ends at: {last_end}")

# 看看 last_end 之后的内容
print(f"\n=== After last biome ({last_end} - {last_end+50} ===")
for i in range(last_end, min(last_end+50, len(raw))):
    b = raw[i]
    ascii_char = chr(b) if 32 <= b < 127 else '.'
    print(f"  offset {i:3d}: 0x{b:02x} ({b:3d})  '{ascii_char}'")
