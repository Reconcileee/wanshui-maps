import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

def read_region(tx, tz):
    path = BASE / f"{tx}_{tz}.zip"
    with zipfile.ZipFile(path) as z:
        return z.read("region.xaero")

raw = read_region(0, 0)
print(f"Total size: {len(raw)}")

# 找所有 minecraft: 字符串的位置
print("\n=== All 'minecraft:' positions ===")
pos = 0
positions = []
while True:
    idx = raw.find(b'minecraft:', pos)
    if idx == -1:
        break
    positions.append(idx)
    pos = idx + 1

print(f"Found {len(positions)} occurrences")

# 看看前 20 个的位置和前后内容
for i, idx in enumerate(positions[:20]):
    # 长度前缀在前一个字节
    if idx > 0:
        slen = raw[idx-1]
        name = raw[idx:idx+slen].decode('utf-8', errors='replace')
        # 后面的字节
        after = raw[idx+slen:idx+slen+8]
        print(f"  [{i:2d}] off={idx-1}, len={slen}, name={name[:40]}, after={after.hex()}")
    else:
        print(f"  [{i:2d}] off={idx}")

# 看看 biome 字符串之间的间隔
print(f"\n=== Spacing between biomes ===")
for i in range(min(20, len(positions)-1)):
    if positions[i] > 0:
        slen = raw[positions[i]-1]
        end = positions[i] + slen
    else:
        end = positions[i] + 10
    gap = positions[i+1] - end
    print(f"  biome {i} ends at {end}, next starts at {positions[i+1]}, gap={gap}")

# 看看 biome 字符串之后的数据是什么
print(f"\n=== After first biome string ===")
first_idx = positions[0]
slen = raw[first_idx - 1]
after_start = first_idx + slen
print(f"Biome ends at {after_start}")
print(f"Next 64 bytes:")
for i in range(0, 64, 16):
    chunk = raw[after_start + i:after_start + i + 16]
    print(f"  off {after_start + i:4d}: {chunk.hex()}")
    # 尝试解码为文本
    text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print(f"            '{text}'")
