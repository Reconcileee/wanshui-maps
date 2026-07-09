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
print(f"Total size: {len(raw)} bytes")

# 10 字节 header
print(f"\n=== Header ===")
print(f"  hex: {raw[:10].hex()}")
# 尝试解析 header 字段
# byte 0: 0xff = magic?
# byte 1: 0x00 = ?
# byte 2-3: size?
# byte 4-5: ?
# byte 6-7: ?
# byte 8-9: ?

# 第一个 NBT
print(f"\n=== First NBT (offset 10) ===")
stream = io.BytesIO(raw[10:])
c = Compound.parse(stream)
nbt_size = stream.tell()
print(f"  size: {nbt_size}")
print(f"  name: {c.get('', {}).get('Name', 'unknown')}")

# NBT 之后的位置
pos = 10 + nbt_size
print(f"\nAfter first NBT: offset {pos}")

# 看看接下来的 256 字节
print(f"\n=== Next 256 bytes ===")
for i in range(0, min(256, len(raw) - pos), 16):
    chunk = raw[pos + i : pos + i + 16]
    hex_str = ' '.join(f'{b:02x}' for b in chunk)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print(f"  {pos+i:6d}: {hex_str}  '{ascii_str}'")

# 尝试解析第二个 NBT
print(f"\n=== Trying second NBT ===")
try:
    stream2 = io.BytesIO(raw[pos:])
    c2 = Compound.parse(stream2)
    nbt_size2 = stream2.tell()
    print(f"  Success! size={nbt_size2}")
    print(f"  Keys: {list(c2.keys())}")
except Exception as e:
    print(f"  Failed: {e}")

# 找所有长度前缀的 minecraft: 字符串
print(f"\n=== All length-prefixed minecraft: strings ===")
pos2 = pos
biome_list = []
while pos2 < len(raw):
    if raw[pos2] == 0:
        pos2 += 1
        continue
    slen = raw[pos2]
    if 10 <= slen <= 64:
        if pos2 + 1 + slen <= len(raw):
            name = raw[pos2+1:pos2+1+slen].decode('utf-8', errors='replace')
            if name.startswith('minecraft:'):
                biome_list.append((pos2, slen, name))
                pos2 += 1 + slen
                continue
    pos2 += 1

print(f"Found {len(biome_list)} biome strings after first NBT")
for i, (off, slen, name) in enumerate(biome_list[:20]):
    # 看看字符串后面的字节
    after = raw[off+1+slen:off+1+slen+8]
    print(f"  [{i:2d}] off={off}, {name[:40]}, after={after.hex()}")

# 分析 biome list 之后的内容
if biome_list:
    last_off = biome_list[-1][0] + 1 + biome_list[-1][1]
    print(f"\nLast biome ends at offset {last_off}")
    print(f"Remaining data: {len(raw) - last_off} bytes")
    
    # 看看接下来的 128 字节
    print(f"\nNext 128 bytes after last biome:")
    for i in range(0, min(128, len(raw) - last_off), 16):
        chunk = raw[last_off + i : last_off + i + 16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        print(f"  {last_off+i:6d}: {hex_str}")
