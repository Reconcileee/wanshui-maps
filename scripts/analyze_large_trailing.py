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

# 用 cache/1/0_0.xwmc 来分析
raw = read_xwmc(1, 0, 0)
px_start = find_pixel_start(raw)
print(f"px_start = {px_start}")
print(f"total = {len(raw)}")
data_after = len(raw) - px_start
print(f"data after px_start: {data_after} bytes")

# 假设 560 个 chunks
n_chunks = 560
pixel_bytes = n_chunks * 1024
trail_size = data_after - pixel_bytes
print(f"\nAssuming {n_chunks} chunks:")
print(f"  pixel_bytes = {pixel_bytes}")
print(f"  trail_size = {trail_size}")

trailing = raw[px_start + pixel_bytes:]

# 看看 trailing 的内容
print(f"\n=== Trailing first 128 bytes ===")
for i in range(0, min(128, len(trailing)), 16):
    chunk = trailing[i:i+16]
    print(f"  off {i:4d}: {chunk.hex()}")

print(f"\n=== Trailing last 128 bytes ===")
start = max(0, len(trailing) - 128)
for i in range(start, len(trailing), 16):
    chunk = trailing[i:i+16]
    print(f"  off {i:4d}: {chunk.hex()}")

# 试试在 trailing 中找坐标对
# 假设坐标是 2 字节 (cx, cz)，值在 0-23 之间
print(f"\n=== Searching for coord pairs (0-23) ===")
best_count = 0
best_start = 0
for start in range(min(200, trail_size - n_chunks*2 + 1)):
    count = 0
    for i in range(n_chunks):
        off = start + i * 2
        if off + 1 >= trail_size:
            break
        cx = trailing[off]
        cz = trailing[off + 1]
        if 0 <= cx < 24 and 0 <= cz < 24:
            count += 1
    if count > best_count:
        best_count = count
        best_start = start
        if count == n_chunks:
            print(f"  PERFECT at start={start}: all {n_chunks} valid!")
            break

if best_count < n_chunks:
    print(f"  Best: start={best_start}, count={best_count}/{n_chunks}")

# 也试试 4 字节坐标 (cx, cz 各 2 字节)
print(f"\n=== Searching for 4-byte coord pairs (0-23) ===")
best_count4 = 0
best_start4 = 0
coord_size4 = n_chunks * 4
for start in range(min(200, trail_size - coord_size4 + 1)):
    count = 0
    for i in range(n_chunks):
        off = start + i * 4
        if off + 3 >= trail_size:
            break
        # 小端序 u16
        cx = trailing[off] | (trailing[off+1] << 8)
        cz = trailing[off+2] | (trailing[off+3] << 8)
        if 0 <= cx < 24 and 0 <= cz < 24:
            count += 1
    if count > best_count4:
        best_count4 = count
        best_start4 = start
        if count == n_chunks:
            print(f"  PERFECT at start={start}: all {n_chunks} valid!")
            break

if best_count4 < n_chunks:
    print(f"  Best: start={best_start4}, count={best_count4}/{n_chunks}")

# 试试坐标在 trailing 末尾
print(f"\n=== Testing coords at END of trailing ===")
# 2 bytes per coord
if trail_size >= n_chunks * 2:
    coord_data = trailing[-n_chunks*2:]
    valid = 0
    coords = []
    for i in range(n_chunks):
        cx = coord_data[i*2]
        cz = coord_data[i*2 + 1]
        if 0 <= cx < 24 and 0 <= cz < 24:
            valid += 1
            coords.append((cx, cz))
    print(f"  2B from end: {valid}/{n_chunks} valid")
    if valid == n_chunks:
        unique = len(set(coords))
        print(f"    unique: {unique}")
        if unique == n_chunks:
            print(f"    *** ALL UNIQUE! ***")
