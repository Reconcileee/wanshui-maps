import zipfile
from pathlib import Path
from nbtlib import Compound
import io

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

def read_region(tx, tz):
    path = BASE / f"{tx}_{tz}.zip"
    with zipfile.ZipFile(path) as z:
        return z.read("region.xaero")

raw = read_region(0, 0)
print(f"region.xaero size: {len(raw)} bytes")

# 10 字节 header
print(f"\n=== Header (10 bytes) ===")
print(f"  hex: {raw[:10].hex()}")
print(f"  dec: {list(raw[:10])}")

# 顺序解析所有 NBT
print(f"\n=== Parsing all NBT compounds ===")
offset = 10
nbt_count = 0
nbt_list = []
while offset < len(raw):
    try:
        stream = io.BytesIO(raw[offset:])
        c = Compound.parse(stream)
        nbt_size = stream.tell()
        name = c.get('', {}).get('Name', 'unknown')
        nbt_list.append((offset, nbt_size, name))
        offset += nbt_size
        nbt_count += 1
        if nbt_count <= 10 or nbt_count % 100 == 0:
            print(f"  NBT {nbt_count}: off={offset-nbt_size}, size={nbt_size}, name={name}")
    except Exception as e:
        print(f"\nNBT parse failed at offset {offset}: {e}")
        break

print(f"\nTotal NBT compounds: {nbt_count}")
print(f"Data remaining after NBTs: {len(raw) - offset} bytes")

# 看看剩余数据的开头
if offset < len(raw):
    remaining = raw[offset:]
    print(f"\n=== Remaining data first 64 bytes ===")
    for i in range(0, min(64, len(remaining)), 16):
        chunk = remaining[i:i+16]
        print(f"  off {i:4d}: {chunk.hex()}")
    
    # 找所有 minecraft: 字符串在剩余数据中
    print(f"\n=== 'minecraft:' in remaining data ===")
    pos = 0
    found = 0
    while True:
        idx = remaining.find(b'minecraft:', pos)
        if idx == -1:
            break
        # 看看周围的内容
        start = max(0, idx - 5)
        end = min(len(remaining), idx + 50)
        context = remaining[start:end]
        print(f"  at offset {offset + idx}: {context.hex()}")
        try:
            print(f"    text: {context.decode('utf-8', errors='replace')}")
        except:
            pass
        found += 1
        if found >= 10:
            print(f"  ... and more")
            break
        pos = idx + 1
