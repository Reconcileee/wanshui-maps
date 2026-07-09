"""精确分析 cache.xaero 格式 - 找到 pixel_data 的确切起始位置

之前的 get_pixel_start 函数可能有 bug。
让我们逐字节分析 cache/3/0_0.xwmc 的 header + palette 部分
"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

fn = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

print(f"Total size: {len(raw)}")

# 16 bytes header
print(f"\nHeader (16 bytes):")
print(f"  hex: {raw[:16].hex()}")
print(f"  dec: {list(raw[:16])}")
# 解读:
# byte 0-1: 可能是 magic/version
# byte 2-3: 00 00?
# byte 4-5: biome count? (之前看到 byte 12-13 = 11)
# 让我看看 byte 12-13
b12_13 = (raw[12] << 8) | raw[13]
print(f"  byte 12-13 as u16 BE: {b12_13}")

# 之前发现 biome 从 offset 16 开始
# 让我们逐 biome 打印精确位置
print(f"\nBiome list starting at offset 16:")
off = 16
biome_idx = 0
while off < min(off + 300, len(raw)):
    # 打印当前位置的字节
    if off + 32 > len(raw):
        break
    chunk = raw[off:off+32]
    # 检查是不是 biome 字符串 (以 length 开头, 后面是 minecraft:)
    slen = chunk[0]
    if slen > 10 and slen < 64 and off + 1 + slen <= len(raw):
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if name.startswith('minecraft:'):
            end = off + 1 + slen
            print(f"  biome {biome_idx}: offset={off}, len={slen}, name={name}, end={end}")
            # 打印 end 之后的 4 字节
            after = raw[end:end+4]
            print(f"    after: {after.hex()} = {list(after)}")
            off = end
            biome_idx += 1
            continue
    # 否则打印原始字节
    print(f"  offset {off}: {chunk.hex()} = {list(chunk)}")
    off += 16
    if biome_idx >= 11 and off > 260:
        break

# 现在让我们找到 pixel data 的真正起始位置
# 关键: pixel data 应该是 ARGB, 每 chunk 1024 字节
# 我们可以通过检查数据模式来找

# 从 offset 250 开始, 尝试不同起始位置, 看哪个 1024 字节块看起来像像素
print("\n\n=== Finding pixel data start ===")
for start_off in range(250, 280):
    # 取第一个 1024 字节块
    if start_off + 1024 > len(raw):
        break
    chunk = raw[start_off:start_off+1024]
    # 检查: 有多少像素是完全透明的 (A=0 且 R=G=B=0)
    transparent = 0
    for i in range(0, 1024, 4):
        a, r, g, b = chunk[i], chunk[i+1], chunk[i+2], chunk[i+3]
        if a == 0 and r == 0 and g == 0 and b == 0:
            transparent += 1
    # 打印结果
    if transparent > 0 and transparent < 256:
        print(f"  start={start_off}: transparent_pixels={transparent}/256 = {transparent/256*100:.1f}%")
