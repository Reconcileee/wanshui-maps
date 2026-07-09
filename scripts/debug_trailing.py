"""详细分析 trailing data 的内容

手动检查 cache/3/0_0.xwmc 的 trailing 数据
"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def find_pixel_start(raw):
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

raw = read_xwmc(BASE / "3" / "0_0.xwmc")
px_start = find_pixel_start(raw)
print(f"px_start = {px_start}")
print(f"total = {len(raw)}")
print(f"data after px_start = {len(raw) - px_start}")

# 假设 40 chunks
n_chunks = 40
pixel_bytes = n_chunks * 1024
trail_start = px_start + pixel_bytes
trailing = raw[trail_start:]
print(f"\nAssuming {n_chunks} chunks:")
print(f"  pixel_bytes = {pixel_bytes}")
print(f"  trail_start = {trail_start}")
print(f"  trail_size = {len(trailing)}")

# 打印 trailing 数据的 hex
print(f"\nTrailing data ({len(trailing)} bytes):")
for i in range(0, len(trailing), 16):
    chunk = trailing[i:i+16]
    hex_str = chunk.hex()
    dec_str = str(list(chunk))
    print(f"  off {i:3d}: {hex_str}")
    print(f"           {dec_str}")

# 试试从末尾数 80 字节 (40 * 2)
print(f"\n\nLast 80 bytes (possible 40 coord pairs):")
last80 = trailing[-80:]
for i in range(0, 80, 10):
    chunk = last80[i:i+10]
    print(f"  off {i:3d}: {list(chunk)}")

# 试试把 trailing 当成 (cx, cz) 对，看看有多少在合理范围
print(f"\n\nTrying all positions for coord pairs (2 bytes each):")
valid_counts = []
for start in range(len(trailing) - 80 + 1):
    coord_data = trailing[start:start+80]
    valid = 0
    coords = []
    for j in range(40):
        cx = coord_data[j*2]
        cz = coord_data[j*2 + 1]
        if 0 <= cx < 24 and 0 <= cz < 24:
            valid += 1
            coords.append((cx, cz))
    valid_counts.append((start, valid, coords[:5]))

# 按 valid 排序
valid_counts.sort(key=lambda x: -x[1])
print("Top 10 positions by valid count:")
for start, valid, sample in valid_counts[:10]:
    print(f"  start={start}: valid={valid}/40, sample={sample}")
