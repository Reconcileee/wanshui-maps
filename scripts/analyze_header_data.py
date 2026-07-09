"""分析 cache/1/8_7.xwmc offset 16-210 之间的数据

看看这些 4 字节整数是什么
"""
import zipfile
from pathlib import Path
import struct

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

raw = read_xwmc(BASE / "1" / "8_7.xwmc")

# 分析 offset 16 到 212 的数据 (196 bytes = 49 u32)
data = raw[16:212]
print(f"Data size: {len(data)} bytes = {len(data)//4} u32 values")

# 小端序 u32
vals_le = []
for i in range(0, len(data) - 3, 4):
    v = struct.unpack_from('<I', data, i)[0]
    vals_le.append(v)

print("\n=== u32 LE values ===")
for i, v in enumerate(vals_le):
    print(f"  [{i:2d}] {v:10d} (0x{v:08x})")

# 看看这些值是不是偏移量
# 如果是 chunk 偏移量，那它们应该指向 pixel data 中的位置
# pixel data 大约从 228 开始，大小约 1.4MB
print(f"\nTotal pixel data size: {len(raw) - 228} bytes")

# 看看有多少个值在合理范围内
valid = [v for v in vals_le if 0 < v < len(raw)]
print(f"Values in range (0, {len(raw)}): {len(valid)}/{len(vals_le)}")

# 排序看看
sorted_vals = sorted(vals_le)
print(f"\nSorted first 10: {sorted_vals[:10]}")
print(f"Sorted last 10: {sorted_vals[-10:]}")

# 也试试 u16 LE
print(f"\n=== u16 LE values (first 40) ===")
for i in range(0, min(80, len(data)), 4):
    v1 = struct.unpack_from('<H', data, i)[0]
    v2 = struct.unpack_from('<H', data, i+2)[0]
    print(f"  [{i//4:2d}] {v1:5d} {v2:5d}  (0x{v1:04x} 0x{v2:04x})")
