"""新发现: cache.xaero 格式

cache/2/0_0.xwmc 的前 32 字节:
62 40 c1 11 00 88 98 b9 ff 00 00 00 0b 00 00 14
6d 69 6e 65 63 72 61 66 74 3a 64 65 65 70 5f 6f

offset 9: 00 00 00 0b = 11 = biome count!
offset 16: 14 6d 69 6e 65 63 72 61 66 74 3a 64 65 65 70 5f 6f
= "minecraft:deep_ocean" 等

所以头部不是 16 字节!
对于 cache/2/0_0.xwmc:
- bytes 0-3: 62 40 c1 11 = ?
- bytes 4-8: 00 88 98 b9 ff = ?
- bytes 9-12: 00 00 00 0b = 11 = biome count
- bytes 13-15: 00 00 14 = ?
- offset 16: palette

让我比较 cache/3 和 cache/2 的头部
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

# 收集所有文件的头部和基本信息
print("=== File headers ===")
for level in ["3", "2", "1"]:
    d = BASE / level
    files = sorted(d.glob("*.xwmc"))
    print(f"\ncache/{level}/ ({len(files)} files):")
    for fn in files[:3]:
        with zipfile.ZipFile(fn) as z:
            raw = z.read("cache.xaero")
        h = raw[:32]
        print(f"  {fn.name}: size={len(raw)}")
        print(f"    hex: {' '.join(f'{b:02x}' for b in h[:16])}")
        print(f"    hex: {' '.join(f'{b:02x}' for b in h[16:32])}")
        # 找 biome count (11 = 0x0b)
        # 0b 出现在 byte 12 (cache/3) 和 byte 11 (cache/2)?
        # 让我精确找
        for i in range(20):
            if raw[i] == 0x00 and raw[i+1] == 0x0b:
                print(f"    00 0b at offset {i} ({(raw[i]<<8)|raw[i+1]})")
            if raw[i] == 0x0b and raw[i+1] == 0x00:
                print(f"    0b 00 at offset {i} ({(raw[i]<<8)|raw[i+1]})")

# 重新解析: 对于 cache/2/0_0.xwmc
# offset 9-12 = 00 00 00 0b = 11 (big-endian 32-bit)
# offset 13-15 = 00 00 14 = ?
# offset 16 开始 palette

# 对于 cache/3/0_0.xwmc
# offset 0-15 = 00 01 00 18 00 01 2a 61 9d ff 00 00 00 0b 00 00
# offset 12-13 = 00 0b = 11 (big-endian 16-bit)
# offset 16 开始 palette

# 两者结构不同? 不太可能
# 让我重新看 cache/3/0_0.xwmc 的 offset 9-12 = ff 00 00 00 = 4278190080
# 不像 biome count

# 等等, 让我搜索所有文件中 'minecraft:' 的起始位置
print("\n=== 'minecraft:' position in each file ===")
for level in ["3", "2", "1"]:
    d = BASE / level
    files = sorted(d.glob("*.xwmc"))
    print(f"\ncache/{level}/:")
    for fn in files[:3]:
        with zipfile.ZipFile(fn) as z:
            raw = z.read("cache.xaero")
        # 找第一个 'minecraft:'
        idx = raw.find(b'minecraft:')
        print(f"  {fn.name}: 'minecraft:' at offset {idx}")
        # 那之前的字节是长度
        if idx > 0:
            print(f"    length byte at {idx-1}: {raw[idx-1]} = {idx-1 - (idx-1)}? no, {raw[idx-1]} is the length")
            # 检查是否 length 是 1 字节
            slen = raw[idx-1]
            print(f"    string length = {slen}")
            print(f"    string = {raw[idx:idx+slen].decode('utf-8', errors='replace')}")

# 结论:
# - palette 中每个 biome 是 1 byte length + string
# - biome 之间可能有 00 00 分隔 (或其他分隔)
# - biome count 可能在某个位置

# 让我找 biome count
# cache/3/0_0.xwmc: 11 biomes, 'minecraft:' first at 17 (offset 17)
#   前一个字节是 14 (offset 16), 所以 length=20, 但 "minecraft:deep_ocean" 是 22?
#   等一下, "minecraft:deep_ocean" = m-i-n-e-c-r-a-f-t-:-d-e-e-p-_-o-c-e-a-n = 22?
#   让我数: m(1)i(2)n(3)e(4)c(5)r(6)a(7)f(8)t(9):(10)d(11)e(12)e(13)p(14)_(15)o(16)c(17)e(18)a(19)n(20) = 20!
#   对! 20 字节. 所以 0x14 = 20 是对的

# cache/2/0_0.xwmc: 11 biomes, 'minecraft:' first at 16? 
# 让我检查
print("\n=== Verify cache/2/0_0.xwmc first biome ===")
fn = BASE / "2" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")
# 找第一个 minecraft:
idx = raw.find(b'minecraft:')
print(f"first 'minecraft:' at {idx}")
slen = raw[idx-1] if idx > 0 else 0
print(f"length byte at {idx-1}: {slen}")
if idx + slen <= len(raw):
    name = raw[idx:idx+slen].decode('utf-8', errors='replace')
    print(f"name: {name}")

# 如果 idx=16, 那 length byte 在 15
# 那 biome count 在哪?
# 让我在 idx-10 到 idx 之间找
print(f"\nbytes {max(0, idx-10)} to {idx}:")
for i in range(max(0, idx-10), idx):
    print(f"  [{i}] 0x{raw[i]:02x} ({raw[i]:3d})")

# 可能格式: 
# 4 bytes: ?
# 4 bytes: ?
# 4 bytes: biome_count (big-endian int32)
# 4 bytes: ?
# palette...

# 对于 cache/2/0_0.xwmc, idx=16, biome_count 可能在 offset 12-15
# 但 offset 12-15 = 0b 00 00 14 = 0x0b000014 = 184549412, 太大了

# 或者: biome count 在 offset 8-11
# 00 00 00 0b = 11! 对!
# offset 8-11 = 00 00 00 0b = 11 (big-endian int32)
print(f"\nbytes 8-11: {raw[8]:02x} {raw[9]:02x} {raw[10]:02x} {raw[11]:02x}")
print(f"as int32 big-endian: {(raw[8]<<24)|(raw[9]<<16)|(raw[10]<<8)|raw[11]}")

# 验证: cache/3/0_0.xwmc 的 bytes 8-11
fn3 = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(fn3) as z:
    raw3 = z.read("cache.xaero")
print(f"\ncache/3/0_0.xwmc bytes 8-11: {raw3[8]:02x} {raw3[9]:02x} {raw3[10]:02x} {raw3[11]:02x}")
print(f"as int32 big-endian: {(raw3[8]<<24)|(raw3[9]<<16)|(raw3[10]<<8)|raw3[11]}")
# 9d ff 00 00 = 0x9dff0000 = 2650767360, 不是 11

# 但 cache/3 有 11 个 biome, cache/2 也应该有 11 个
# 让我数 cache/2/0_0.xwmc 有多少个 biome
biomes = []
off = idx - 1  # start of length byte
# 不对, 从 palette 开始位置找
# 让我从 offset 16 开始数有多少个 minecraft:
print("\n=== Counting biomes in cache/2/0_0.xwmc ===")
count = 0
search_from = 0
while True:
    pos = raw.find(b'minecraft:', search_from)
    if pos == -1:
        break
    count += 1
    search_from = pos + 1
print(f"found {count} 'minecraft:' occurrences")

# 只有 11 个的话, biome_count 是 11
# 但 cache/3 的 bytes 8-11 不是 11
# 可能格式在不同 zoom level 不同? 不太可能

# 让我重新看 cache/3/0_0.xwmc 头部
# 00 01 00 18 00 01 2a 61 9d ff 00 00 00 0b 00 00
# bytes 12-13 = 00 0b = 11!
# bytes 10-11 = 00 00 = 0
# bytes 14-15 = 00 00 = 0
# 可能 biome count 是 bytes 12-13 (16-bit), 且 bytes 10-11 是 0

# cache/2/0_0.xwmc:
# 62 40 c1 11 00 88 98 b9 ff 00 00 00 0b 00 00 14
# bytes 10-13 = 00 00 00 0b = 11 (32-bit)?
# 不对, bytes 8-11 = ff 00 00 00 = 4278190080

# 让我精确对齐: 
# cache/3: biome count at offset 12 (2 bytes, big-endian)
# cache/2: 也看看 offset 12
print(f"\ncache/2 bytes 12-13: {raw[12]:02x} {raw[13]:02x} = {(raw[12]<<8)|raw[13]}")
# 0b 00 = 2816, 不是 11

# 等等, 可能是 little-endian?
print(f"cache/2 bytes 12-13 (LE): {raw[13]:02x} {raw[12]:02x} = {(raw[13]<<8)|raw[12]}")
# 00 0b = 11!

# 验证 cache/3
print(f"cache/3 bytes 12-13 (LE): {raw3[13]:02x} {raw3[12]:02x} = {(raw3[13]<<8)|raw3[12]}")
# 00 00 = 0, 不对

# 这不对, 让我换个思路
# 直接从 palette 解析, 不依赖 biome count
print("\n=== Parse palette from 'minecraft:' ===")
def parse_palette_from_string(raw):
    """从第一个 'minecraft:' 开始, 向前找 length byte, 然后解析所有 biome"""
    first = raw.find(b'minecraft:')
    if first == -1:
        return [], 0
    
    # 向前找 length byte (1 byte)
    # 假设 length 就在字符串前面
    slen = raw[first - 1]
    palette_start = first - 1
    print(f"  first 'minecraft:' at {first}, length={slen}, palette_start={palette_start}")
    
    # 解析所有 biome
    biomes = []
    off = palette_start
    while off < len(raw):
        if off >= len(raw):
            break
        slen = raw[off]
        if slen < 10 or slen > 64:
            # 可能是 00 分隔或其他
            # 看看后面是否还有 minecraft:
            if off + 1 < len(raw) and raw[off+1:].find(b'minecraft:') >= 0:
                off += 1
                continue
            else:
                break
        if off + 1 + slen > len(raw):
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        biomes.append(name)
        off += 1 + slen
    
    # pixel_start = end of last biome + trailing zeros until non-zero
    pixel_start = off
    # 跳过末尾的 0
    while pixel_start < len(raw) and raw[pixel_start] == 0:
        pixel_start += 1
    
    return biomes, pixel_start

for level, name in [("3", "0_0.xwmc"), ("2", "0_0.xwmc"), ("1", "0_0.xwmc")]:
    fn = BASE / level / name
    if not fn.exists():
        continue
    with zipfile.ZipFile(fn) as z:
        raw = z.read("cache.xaero")
    biomes, pixel_start = parse_palette_from_string(raw)
    pixel_data = raw[pixel_start:]
    n_pixels = len(pixel_data) // 4
    print(f"\ncache/{level}/{name}:")
    print(f"  biomes: {len(biomes)}")
    print(f"  pixel_start: {pixel_start}")
    print(f"  pixel_data: {len(pixel_data)} bytes = {n_pixels} pixels")
    print(f"  first biome: {biomes[0] if biomes else 'none'}")
    print(f"  last biome: {biomes[-1] if biomes else 'none'}")
    
    # 如果像素多, 渲染看看
    if n_pixels > 1000:
        # 试几个常见尺寸
        for w in [256, 384, 512, 1024]:
            h = n_pixels // w
            if h > 0 and h < 2000 and w * h > n_pixels * 0.9:
                print(f"  try render {w}x{h}")
                img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                for i in range(w * h):
                    if i * 4 + 3 >= len(pixel_data):
                        break
                    a, r, g, b = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
                    img.putpixel((i % w, i // w), (r, g, b, a))
                img.save(OUT / f"l{level}_{name.replace('.xwmc','')}_{w}x{h}.png")
