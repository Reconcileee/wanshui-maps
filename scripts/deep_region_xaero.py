"""深入分析 region.xaero 格式

结构:
1. 10 bytes header
2. NBT block states (若干个 Compound)
3. Biome 字符串列表 (长度前缀字符串)
4. Block data (512x512 = 262144 blocks)
   - 每 block: 可能是 block state index + height + biome index?

我们知道:
- 第一个 NBT 从 offset 10 开始, 到 offset 104 结束 (94 bytes)
- offset 104 开始是 biome 字符串: 0x14 + "minecraft:deep_ocean" (20 bytes)

让我们找出:
1. 有多少个 NBT block states
2. 有多少个 biome 字符串
3. block data 从哪里开始
4. block data 的格式
"""
import zipfile
import io
from pathlib import Path
from nbtlib import Compound

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

f = BASE / "0_0.zip"
with zipfile.ZipFile(f) as z:
    raw = z.read("region.xaero")

print(f"Total size: {len(raw)} bytes")

# 找到所有 NBT block states
offset = 10
nbt_count = 0
nbt_list = []
while offset < len(raw):
    # 尝试解析 NBT
    try:
        stream = io.BytesIO(raw[offset:])
        c = Compound.parse(stream)
        nbt_list.append(c)
        # stream.tell() 是读了多少字节
        nbt_size = stream.tell()
        offset += nbt_size
        nbt_count += 1
        if nbt_count <= 3 or nbt_count % 20 == 0:
            name = c.get('', {}).get('Name', 'unknown')
            print(f"  NBT {nbt_count}: size={nbt_size}, name={name}")
    except Exception as e:
        # 解析失败, 说明 NBT 结束了
        print(f"\nNBT parse failed at offset {offset}: {e}")
        break

print(f"\nTotal NBT block states: {nbt_count}")
print(f"Offset after last NBT: {offset}")

# 检查 offset 处是不是 biome 字符串
print(f"\nBytes at offset {offset}: {raw[offset:offset+32].hex()}")

# 解析 biome 列表
biome_offset = offset
biomes = []
for i in range(200):  # 最多 200 个 biome
    if biome_offset >= len(raw):
        break
    slen = raw[biome_offset]
    if slen < 10 or slen > 64:  # biome 名长度范围
        # 可能不是 biome 了
        break
    if biome_offset + 1 + slen > len(raw):
        break
    name = raw[biome_offset+1:biome_offset+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes.append(name)
    biome_offset += 1 + slen

print(f"\nBiomes found: {len(biomes)}")
for i, b in enumerate(biomes[:15]):
    print(f"  {i}: {b}")
if len(biomes) > 15:
    print(f"  ... and {len(biomes)-15} more")

print(f"\nOffset after biome list: {biome_offset}")
print(f"Bytes at biome_offset: {raw[biome_offset:biome_offset+32].hex()}")

# block data 开始了
block_data_start = biome_offset
block_data_size = len(raw) - block_data_start
print(f"\nBlock data start: {block_data_start}")
print(f"Block data size: {block_data_size} bytes")
print(f"512*512 = {512*512} blocks")
print(f"bytes per block: {block_data_size / (512*512):.3f}")

# 每 block 多少字节?
# 如果 2 bytes: 262144 * 2 = 524288, 但实际是 ~2M
# 如果 8 bytes: 262144 * 8 = 2097152 = 2MB, 接近!
# region.xaero = 2111535 bytes
# 10 (header) + NBTs (94 * ?) + biomes + block_data = total
# block_data ≈ 2111535 - 10 - 94*nbt_count - biome_bytes
# 如果 nbt_count = 100, biomes = 20, 那 block_data ≈ 2.1M - 10K = ~2.1M
# 2.1M / 262144 = 8 bytes per block ✓

# 8 bytes per block! 可能是:
# - 2 bytes block state index
# - 2 bytes height
# - 2 bytes biome index  
# - 2 bytes ???
# 或
# - 4 bytes height
# - 2 bytes biome
# - 2 bytes light
# 等等

# 让我看前几个 block 的数据
print(f"\nFirst 20 blocks (8 bytes each):")
for i in range(20):
    off = block_data_start + i * 8
    b = raw[off:off+8]
    vals = list(b)
    # 试试不同解释
    u16_1 = (b[0] << 8) | b[1]
    u16_2 = (b[2] << 8) | b[3]
    u16_3 = (b[4] << 8) | b[5]
    u16_4 = (b[6] << 8) | b[7]
    print(f"  block {i:3d}: {vals} = u16({u16_1}, {u16_2}, {u16_3}, {u16_4})")

# 验证: 如果第一个数是 block state index, 应该 < nbt_count
# 如果第二个是 height, 应该在 0-256 之间
# 如果第三个是 biome index, 应该 < len(biomes)
