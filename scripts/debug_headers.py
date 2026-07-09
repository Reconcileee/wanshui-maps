"""详细分析 tile (8,7) 的 header 和 biome palette

只有 1 个 biome，但 byte 6 = 11？让我看看中间的数据
"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

raw = read_xwmc(BASE / "1" / "8_7.xwmc")
print(f"Total size: {len(raw)} bytes")

# 打印 offset 16 到 260 的详细信息
print(f"\n=== Bytes 16 to 260 ===")
for i in range(16, min(260, len(raw)), 16):
    end = min(i + 16, len(raw))
    chunk = raw[i:end]
    hex_str = chunk.hex()
    # 每 4 字节加空格
    hex_spaced = ' '.join(hex_str[j:j+8] for j in range(0, len(hex_str), 8))
    print(f"  off {i:4d}: {hex_spaced}")
    # 打印 4 字节整数 (LE and BE)
    print(f"            u32LE: ", end="")
    vals_le = []
    for j in range(0, len(chunk) - 3, 4):
        v = int.from_bytes(chunk[j:j+4], 'little')
        vals_le.append(str(v))
    print(' '.join(vals_le))
    print(f"            u32BE: ", end="")
    vals_be = []
    for j in range(0, len(chunk) - 3, 4):
        v = int.from_bytes(chunk[j:j+4], 'big')
        vals_be.append(str(v))
    print(' '.join(vals_be))

# 也看看 cache/3/0_0.xwmc 的 header 对比
print(f"\n\n=== cache/3/0_0.xwmc header ===")
raw3 = read_xwmc(BASE / "3" / "0_0.xwmc")
for i in range(0, min(64, len(raw3)), 16):
    end = min(i + 16, len(raw3))
    chunk = raw3[i:end]
    hex_str = chunk.hex()
    hex_spaced = ' '.join(hex_str[j:j+8] for j in range(0, len(hex_str), 8))
    print(f"  off {i:4d}: {hex_spaced}")
    print(f"            u32LE: ", end="")
    vals_le = []
    for j in range(0, len(chunk) - 3, 4):
        v = int.from_bytes(chunk[j:j+4], 'little')
        vals_le.append(str(v))
    print(' '.join(vals_le))

# 再看看 biome 字符串位置
print(f"\n\n=== Finding all 'minecraft:' in cache/3/0_0.xwmc ===")
count = 0
pos = 0
while True:
    idx = raw3.find(b'minecraft:', pos)
    if idx == -1:
        break
    slen = raw3[idx-1] if idx > 0 else -1
    name = raw3[idx:idx+min(slen, 40)].decode('utf-8', errors='replace') if slen > 0 else '?'
    print(f"  {count}: offset={idx}, slen={slen}, name={name[:30]}")
    count += 1
    pos = idx + 1
print(f"Total: {count}")
