"""在 region.xaero 中搜索 biome 数据

假设:
- biome 数据是连续的一段
- 每 byte 是 biome index (0-10，因为只有 11 种 biome)
- 512x512 = 262144 bytes

让我们找一段连续的、大多数值都在 0-10 范围内的数据
"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

f = BASE / "0_0.zip"
with zipfile.ZipFile(f) as z:
    raw = z.read("region.xaero")

print(f"Total size: {len(raw)} bytes")

# 滑动窗口: 找 65536 字节的窗口，其中 >80% 的值在 0-10 范围内
window_size = 65536  # 先试试 256x256
threshold = 0.8

print(f"\nSearching for biome-like data (window={window_size}, threshold={threshold*100}%)...")

best_pos = -1
best_ratio = 0

for pos in range(0, len(raw) - window_size, 1024):
    window = raw[pos:pos+window_size]
    # 统计 0-10 的比例
    count = sum(1 for b in window if b <= 10)
    ratio = count / window_size
    if ratio > best_ratio:
        best_ratio = ratio
        best_pos = pos
    if ratio > threshold:
        print(f"  Found at offset {pos}: {ratio*100:.1f}%")

print(f"\nBest match: offset {best_pos}, ratio {best_ratio*100:.1f}%")

# 也试试 262144 字节的窗口 (512x512)
print(f"\nSearching with window=262144...")
window_size = 262144
best_pos2 = -1
best_ratio2 = 0
for pos in range(0, len(raw) - window_size, 4096):
    window = raw[pos:pos+window_size]
    count = sum(1 for b in window if b <= 10)
    ratio = count / window_size
    if ratio > best_ratio2:
        best_ratio2 = ratio
        best_pos2 = pos

print(f"Best match: offset {best_pos2}, ratio {best_ratio2*100:.1f}%")

# 也许 biome 是 4-bit (每 byte 两个 biome)
# 65536 字节 = 131072 个 biome，还是不够
# 或者 biome 数据更短，因为是按 chunk 存储的，每 chunk 只有 1 个 biome (平均值)

# 或者 height 数据？height 应该在 0-256 范围内
# 让我们找 height-like 数据 (值在 40-120 之间，典型地表高度)
print(f"\nSearching for height-like data (window=262144, values 40-120)...")
window_size = 262144
best_pos_h = -1
best_ratio_h = 0
for pos in range(0, len(raw) - window_size, 4096):
    window = raw[pos:pos+window_size]
    count = sum(1 for b in window if 40 <= b <= 120)
    ratio = count / window_size
    if ratio > best_ratio_h:
        best_ratio_h = ratio
        best_pos_h = pos

print(f"Best match: offset {best_pos_h}, ratio {best_ratio_h*100:.1f}%")
