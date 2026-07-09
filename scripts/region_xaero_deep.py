"""深入分析 region.xaero 格式 - 找出 biome 和 height 数据的布局

header 10 bytes: ff 00 06 00 08 00 02 70 00 01

之前的发现:
- offset 10 开始: 第一个 NBT block state (94 bytes, 到 offset 104)
- offset 104: 0x14 + "minecraft:deep_ocean" (biome 字符串)
- 但后面还有更多 NBT 和 biome 字符串交织

让我重新理解格式:
可能格式是:
1. 10 bytes header
2. 若干 segments, 每个 segment 是:
   - NBT block state (Compound)
   - biome 字符串 (length-prefixed)
   - chunk 数据?

不对，一个 region 有 32x32 = 1024 chunks。
让我看看有多少个 NBT + biome 对。

或者格式是:
1. 10 bytes header
2. chunk count? (1024?)
3. 每个 chunk 的数据...

让我找一个模式: NBT 后面跟着 biome 字符串
然后 biome 字符串后面跟着... 什么?
"""
import zipfile
import io
from pathlib import Path
from nbtlib import Compound

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

f = BASE / "0_0.zip"
with zipfile.ZipFile(f) as z:
    raw = z.read("region.xaero")

print(f"Total size: {len(raw)} bytes")

# 让我们尝试找所有的 "minecraft:" 字符串位置
# 每个 biome 字符串以长度前缀开头，后面是 minecraft:xxx
print("\n=== Finding all biome strings ===")
biome_positions = []
pos = 0
while True:
    idx = raw.find(b'minecraft:', pos)
    if idx == -1:
        break
    # 前一个字节应该是长度
    if idx > 0:
        slen = raw[idx-1]
        name = raw[idx:idx+slen].decode('utf-8', errors='replace')
        biome_positions.append((idx-1, slen, name))
    pos = idx + 1

print(f"Found {len(biome_positions)} biome strings")
for i, (pos, slen, name) in enumerate(biome_positions[:20]):
    print(f"  {i}: offset={pos}, len={slen}, name={name}")
if len(biome_positions) > 20:
    print(f"  ... and {len(biome_positions)-20} more")

# 如果有 11 个 biome，那 biome 种类是 11 种
# 每 chunk 引用 biome index

# 让我们看看前几个 biome 后面的数据是什么
print("\n\n=== Data after each biome string ===")
for i, (pos, slen, name) in enumerate(biome_positions[:5]):
    end = pos + 1 + slen
    after = raw[end:end+32]
    print(f"Biome {i} ({name}) ends at {end}:")
    print(f"  next 32 bytes: {after.hex()}")
    print(f"  next 32 dec: {list(after)}")

# 关键问题: region.xaero 总大小 2111535
# 512x512 = 262144 blocks
# 如果每 block 8 bytes = 2097152 bytes
# 2111535 - 2097152 = 14383 bytes header/metadata
# 14383 字节的 header + NBT + biome 列表，合理

# 让我们找 block data 的起始位置
# block data 应该是 262144 * N bytes, 从某个 offset 开始
# 2111535 - 262144*8 = 2111535 - 2097152 = 14383
# 所以 block data 可能从 offset 14383 开始?
# 或者 262144*7 = 1835008, 2111535 - 1835008 = 276527

# 让我们用不同方法: 找第一个 biome 字符串之前的所有 NBT
# 看看有多少个 block state 定义
print("\n\n=== Counting NBT block states before first biome ===")
first_biome_offset = biome_positions[0][0]
print(f"First biome at offset {first_biome_offset}")
print(f"Data before first biome: {first_biome_offset - 10} bytes (from offset 10)")

# 数 NBT 数量
offset = 10
nbt_count = 0
while offset < first_biome_offset:
    try:
        stream = io.BytesIO(raw[offset:])
        c = Compound.parse(stream)
        nbt_size = stream.tell()
        offset += nbt_size
        nbt_count += 1
    except:
        break

print(f"NBT count before first biome: {nbt_count}")
print(f"Offset after NBTs: {offset}")

# 等等，第一个 biome 在 offset 104，而第一个 NBT 从 10 开始，大小 94，到 104
# 那 offset 104 就是 biome 字符串的开始
# 所以 NBT + biome 是成对出现的: NBT 然后 biome 字符串

# 如果有 11 个 biome，那也应该有 11 个 NBT block states？
# 不对，block state 应该比 biome 多

# 让我看看 biome_positions 是不是 11 个
print(f"\nTotal biome strings found: {len(biome_positions)}")

# 如果只有 11 个，那就是 biome palette
# biome 数据从最后一个 biome 字符串结束的位置开始

last_biome_end = biome_positions[-1][0] + 1 + biome_positions[-1][1]
print(f"\nLast biome ends at offset {last_biome_end}")
print(f"Remaining data: {len(raw) - last_biome_end} bytes")
print(f"512*512 = {512*512} blocks")
print(f"bytes per block: {(len(raw) - last_biome_end) / (512*512):.3f}")

# 等等，之前只找到 1 个 biome，但现在 find 所有 minecraft: 应该能找到更多
# 让我看看 biome_positions 的数量

# 如果有 11 个 biome (palette)
# 那每 block biome index = 1 byte (0-10)
# 512*512 = 262144 bytes for biome
# 但 2111535 - last_biome_end 应该远大于 262144
# 因为还有 height / light / block state 等数据
