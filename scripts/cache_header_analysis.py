"""分析 cache.xaero 的 16 字节 header

比较多个文件的 header，找出每个字段的含义
"""
import zipfile
from pathlib import Path
import struct

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

# 收集几个不同文件的 header
files_to_check = [
    ("3", "0_0.xwmc"),
    ("3", "-1_1.xwmc"),
    ("2", "0_0.xwmc"),
    ("2", "-1_1.xwmc"),
    ("1", "0_0.xwmc"),
    ("1", "-1_1.xwmc"),
]

print("=== Cache.xaero header analysis (16 bytes) ===")
print(f"{'File':<20} {'hex':<35} {'u16(BE)':<30} {'u32(BE)':<25}")
print("-" * 110)

for level, fname in files_to_check:
    fp = BASE / level / fname
    if not fp.exists():
        continue
    raw = read_xwmc(fp)
    h = raw[:16]
    
    hex_str = ' '.join(f'{b:02x}' for b in h)
    
    # 解析为 u16 big-endian
    u16s = []
    for i in range(0, 16, 2):
        v = (h[i] << 8) | h[i+1]
        u16s.append(str(v))
    
    # 解析为 u32 big-endian
    u32s = []
    for i in range(0, 16, 4):
        v = (h[i] << 24) | (h[i+1] << 16) | (h[i+2] << 8) | h[i+3]
        u32s.append(str(v))
    
    label = f"cache/{level}/{fname}"
    print(f"{label:<20} {hex_str:<35} {' '.join(u16s):<30} {' '.join(u32s):<25}")
    print(f"{'':<20} size={len(raw)} bytes")

# 找规律:
# byte 0: 可能是版本/标志
# byte 2-3 / 4-5: 可能是 chunk 数量或 tile 大小
# byte 12-13: 之前认为是 biome count (cache/3 = 11)

# 让我验证 biome count
print("\n\n=== Biome count verification (byte 12-13 as u16 BE) ===")
for level in ["3", "2", "1"]:
    level_dir = BASE / level
    files = list(level_dir.glob("*.xwmc"))[:3]
    for f in files:
        raw = read_xwmc(f)
        biome_count_be = (raw[12] << 8) | raw[13]
        biome_count_le = (raw[13] << 8) | raw[12]
        # 数实际 biome 数量
        first_minecraft = raw.find(b'minecraft:')
        # 简单数: 找所有 minecraft: 的出现次数
        n = 0
        pos = 0
        while True:
            idx = raw.find(b'minecraft:', pos)
            if idx == -1 or idx > 500:  # 只看前 500 字节
                break
            n += 1
            pos = idx + 1
        print(f"  cache/{level}/{f.name}: byte12-13 BE={biome_count_be}, LE={biome_count_le}, minecraft_count={n}")

# 让我也看看 pixel_start 之前有多少字节的数据
# 找最后一个 biome 字符串的结束位置
print("\n\n=== Last biome string position ===")
for level, fname in files_to_check[:4]:
    fp = BASE / level / fname
    if not fp.exists():
        continue
    raw = read_xwmc(fp)
    
    # 找前 500 字节内的所有 biome
    biome_end = 16
    pos = 16
    while pos < 500 and pos < len(raw):
        # 找 minecraft:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1 or idx > 500:
            break
        # 前一个字节是长度
        if idx > 0:
            slen = raw[idx-1]
            biome_end = idx + slen
            pos = biome_end
        else:
            pos = idx + 1
    
    print(f"  cache/{level}/{fname}: last_biome_ends_at={biome_end}, total={len(raw)}")
