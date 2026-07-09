"""重新分析 region.xaero 格式

关键: 区分 NBT 内部的 minecraft: (block names) 和 biome 列表中的 minecraft: (biome names)

方法:
1. 顺序解析所有 NBT Compounds (block states)
2. NBT 结束后才是 biome 列表
3. biome 列表之后才是 block data
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

# 10 bytes header
print(f"Header (10 bytes): {raw[:10].hex()} = {list(raw[:10])}")

# 顺序解析 NBT，直到解析失败
offset = 10
nbt_list = []
print(f"\n=== Parsing NBT block states ===")
while offset < len(raw):
    start = offset
    try:
        stream = io.BytesIO(raw[offset:])
        c = Compound.parse(stream)
        nbt_size = stream.tell()
        offset += nbt_size
        name = c.get('', {}).get('Name', 'unknown')
        nbt_list.append((start, nbt_size, name))
        if len(nbt_list) <= 5 or len(nbt_list) % 50 == 0:
            print(f"  NBT {len(nbt_list)-1}: off={start}, size={nbt_size}, name={name}")
    except Exception as e:
        print(f"\nNBT parse failed at offset {offset}: {e}")
        break

print(f"\nTotal NBTs: {len(nbt_list)}")
print(f"Offset after last NBT: {offset}")

# 看看 offset 处的数据
print(f"\nBytes at offset {offset} (first 64):")
print(f"  hex: {raw[offset:offset+64].hex()}")
print(f"  dec: {list(raw[offset:offset+64])}")

# 看看这里是不是 biome 列表
# biome 列表格式: [1 byte len][name] [separator?]
print(f"\n=== Trying to parse biome list from offset {offset} ===")
biome_off = offset
biomes = []
for i in range(100):
    if biome_off >= len(raw):
        break
    slen = raw[biome_off]
    if slen == 0:
        biome_off += 1
        continue
    if slen < 10 or slen > 64:
        # 看看是不是 00 00 分隔
        if biome_off + 1 < len(raw) and raw[biome_off] == 0 and raw[biome_off+1] == 0:
            biome_off += 2
            continue
        break
    if biome_off + 1 + slen > len(raw):
        break
    name = raw[biome_off+1:biome_off+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes.append(name)
    biome_off += 1 + slen

print(f"Found {len(biomes)} biomes:")
for i, b in enumerate(biomes):
    print(f"  {i}: {b}")

# block data 起始
if biomes:
    block_start = biome_off
    # 跳过末尾的 0
    while block_start < len(raw) and raw[block_start] == 0:
        block_start += 1
    
    block_data_size = len(raw) - block_start
    print(f"\nBlock data starts at: {block_start}")
    print(f"Block data size: {block_data_size} bytes")
    print(f"512x512 = {512*512} blocks")
    print(f"Bytes per block: {block_data_size / (512*512):.3f}")
    
    # 看看前几个 block 的数据
    print(f"\nFirst 10 blocks:")
    bpb = block_data_size // (512*512)  # bytes per block (approx)
    for i in range(10):
        off = block_start + i * bpb
        print(f"  block {i}: {list(raw[off:off+bpb])}")
