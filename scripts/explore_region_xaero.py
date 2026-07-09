"""探索 region.xaero 格式 (从 Xaero region zip 中)

之前我们知道:
- region.xaero = 10 字节头 + raw NBT block states + biome 字符串
- 第一个 NBT 是 94 字节 (一个 block state)
- 然后是 0x14 + biome 字符串 (0x14 是长度?)

但 region.xaero 应该包含完整的 512x512 block 数据
让我重新深入分析
"""
import zipfile
import io
from pathlib import Path
from nbtlib import Compound, List, tag

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

# 选一个 region zip 文件
f = BASE / "0_0.zip"
with zipfile.ZipFile(f) as z:
    print("Files in zip:")
    for name in z.namelist():
        info = z.getinfo(name)
        print(f"  {name}: {info.file_size} bytes")

    raw = z.read("region.xaero")

print(f"\nregion.xaero: {len(raw)} bytes")
print(f"first 32 hex: {raw[:32].hex()}")
print(f"first 32 dec: {list(raw[:32])}")

# 10 字节头
header = raw[:10]
print(f"\nheader (10 bytes): {' '.join(f'{b:02x}' for b in header)}")
# ff 00 06 00 08 00 02 70 00 01
# byte 0: ff = 255 (version?)
# byte 1: 00
# byte 2-3: 06 00 = 6 (big-endian)? 或 00 06 = 6?
# byte 4-5: 08 00 = 8
# byte 6: 02
# byte 7: 70 = 112
# byte 8: 00
# byte 9: 01

# 尝试解析 NBT
nbt_data = raw[10:]
print(f"\nNBT data size: {len(nbt_data)}")

# 第一个 NBT
try:
    c = Compound.parse(io.BytesIO(nbt_data))
    print(f"First NBT: {c}")
    print(f"First NBT keys: {list(c.keys())}")
except Exception as e:
    print(f"Error parsing NBT at start: {e}")

# 第一个 NBT 用了多少字节?
# 让我们用不同方法找大小
# 第一个 NBT 结束位置: 之前说是 94 字节
# 让我看看 offset 90-110
print(f"\nbytes 90-110: {raw[10+90:10+110].hex()}")
print(f"bytes 90-110 dec: {list(raw[10+90:10+110])}")

# 0x14 = 20, 后面跟着 biome 字符串 (长度 20 = "minecraft:deep_ocean"?)
# 让我检查 offset 94 后的字节
print(f"\nAfter first NBT (offset 10+94=104):")
print(f"  bytes 104-130: {raw[104:130].hex()}")
slen = raw[104]
print(f"  length byte: {slen} = 0x{slen:02x}")
if 105 + slen <= len(raw):
    name = raw[105:105+slen].decode('utf-8', errors='replace')
    print(f"  string: {name}")

# 如果第一个字节 0x14=20 是字符串长度, 那 "minecraft:deep_ocean"=20 字符?
# 让我数: m-i-n-e-c-r-a-f-t-:-d-e-e-p-_-o-c-e-a-n = 20
# 对! 正好 20

# 那后面呢? biome 数据是怎么组织的?
# 512x512 blocks per region = 262144 blocks
# 如果每块 1 字节 biome index, 就是 262144 bytes
# 但 region.xaero 有多大? 让我看
print(f"\nTotal size: {len(raw)} bytes")
print(f"512*512 = {512*512}")

# 不对, 262144 字节的 biome 数据, 但 region.xaero 多大?
# 让我看几个文件
print("\n=== Multiple region zip sizes ===")
count = 0
for f in sorted(BASE.glob("*.zip")):
    with zipfile.ZipFile(f) as z:
        if "region.xaero" in z.namelist():
            info = z.getinfo("region.xaero")
            print(f"  {f.name}: {info.file_size} bytes")
            count += 1
            if count >= 10:
                break
