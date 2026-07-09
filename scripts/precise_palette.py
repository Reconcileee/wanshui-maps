"""验证 cache.xaero 格式: 16 bytes header + biome palette + N chunks (1024 bytes each)

新发现: pixel_start 应该包含最后一个 00 分隔符!
让我重新计算:

cache/3/0_0.xwmc:
- 11 biomes
- "minecraft:deep_ocean" = 20 bytes (length 20)
- 每个 biome = 1 + 20 = 21 bytes (带 length)
- 11 * 21 = 231 bytes
- 加上 10 个 2-byte 分隔符 (00 00) = 20 bytes
- 231 + 20 = 251 bytes
- 从 offset 16 开始, 16 + 251 = 267
- 不对, 实际是 254 或 256

让我重新精确计算每个 biome 的长度
"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

fn = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

print(f"total: {len(raw)}")

# 精确解析 palette
off = 16
biomes = []
for i in range(100):  # 最多 100 个
    if off >= len(raw):
        break
    # 跳过 0
    while off < len(raw) and raw[off] == 0:
        off += 1
    if off >= len(raw):
        break
    slen = raw[off]
    if slen < 10 or slen > 64:
        break
    if off + 1 + slen > len(raw):
        break
    name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes.append((slen, name, off))
    off += 1 + slen

print(f"\nParsed {len(biomes)} biomes:")
for slen, name, start_off in biomes:
    end_off = start_off + 1 + slen
    print(f"  offset {start_off}: len={slen}, name={name}, end={end_off}")

print(f"\nFinal offset after last biome: {off}")
print(f"Next 8 bytes: {raw[off:off+8].hex()} = {list(raw[off:off+8])}")

# pixel_data 应该从 off 开始 (跳过末尾的 0)
px_start = off
while px_start < len(raw) and raw[px_start] == 0:
    px_start += 1
print(f"pixel_start (skip zeros): {px_start}")
print(f"pixel_data size: {len(raw) - px_start}")

# 检查 pixel_data 是否能被 1024 整除
pd_size = len(raw) - px_start
print(f"\npixel_data / 1024 = {pd_size / 1024:.4f}")
print(f"pixel_data // 1024 = {pd_size // 1024} chunks")
print(f"remainder: {pd_size % 1024} bytes")

# 关键: 我之前跳过了末尾的 0, 但可能那些 0 就是第一个 chunk 的开始部分
# 让我不跳过 0, 直接从 off 开始
pd_size2 = len(raw) - off
print(f"\nno-skip pixel_data size: {pd_size2}")
print(f"no-skip / 1024 = {pd_size2 / 1024:.4f}")
print(f"no-skip // 1024 = {pd_size2 // 1024} chunks")
print(f"remainder: {pd_size2 % 1024} bytes")

# 验证: 如果 40 chunks * 1024 = 40960
# 那 pd_size 应该是 40960 + trailing
# cache/3/0_0.xwmc: total=41311
# 如果 pixel_start = 254, pd=41057, 41057-40960=97
# 如果 pixel_start = 256, pd=41055, 41055-40960=95

# 让我用另一个文件验证
print("\n=== cache/3/-1_1.xwmc ===")
fn2 = BASE / "3" / "-1_1.xwmc"
with zipfile.ZipFile(fn2) as z:
    raw2 = z.read("cache.xaero")

print(f"total: {len(raw2)}")
off2 = 16
biomes2 = []
for i in range(100):
    while off2 < len(raw2) and raw2[off2] == 0:
        off2 += 1
    if off2 >= len(raw2):
        break
    slen = raw2[off2]
    if slen < 10 or slen > 64:
        break
    if off2 + 1 + slen > len(raw2):
        break
    name = raw2[off2+1:off2+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes2.append((slen, name))
    off2 += 1 + slen

print(f"biomes: {len(biomes2)}")
print(f"offset after biomes: {off2}")
print(f"next 8 bytes: {raw2[off2:off2+8].hex()}")

px_start2 = off2
while px_start2 < len(raw2) and raw2[px_start2] == 0:
    px_start2 += 1
print(f"pixel_start (skip zeros): {px_start2}")
pd2 = len(raw2) - px_start2
print(f"pixel_data size: {pd2}")
print(f"/ 1024 = {pd2 / 1024:.4f}")
print(f"// 1024 = {pd2 // 1024} chunks, remainder = {pd2 % 1024}")

# 如果两个文件的 remainder 相同, 那 trailing 大小固定
# cache/3/0_0.xwmc: 95 or 97
# cache/3/-1_1.xwmc: ?

# 也看看 cache/2 和 cache/1
for level in ["2", "1"]:
    for fname in ["0_0.xwmc"]:
        fn = BASE / level / fname
        if not fn.exists():
            continue
        with zipfile.ZipFile(fn) as z:
            r = z.read("cache.xaero")
        # 找 pixel_start
        first = r.find(b'minecraft:')
        off3 = first - 1
        while off3 < len(r):
            slen = r[off3]
            if slen < 10 or slen > 64:
                if r[off3+1:].find(b'minecraft:') >= 0:
                    off3 += 1
                    continue
                break
            name = r[off3+1:off3+1+slen].decode('utf-8', errors='replace')
            if not name.startswith('minecraft:'):
                break
            off3 += 1 + slen
        # 不跳 0
        pd3 = len(r) - off3
        n_chunks = pd3 // 1024
        rem = pd3 % 1024
        print(f"\ncache/{level}/{fname}: total={len(r)}, pixel_start={off3}, pd={pd3}, chunks={n_chunks}, rem={rem}")
