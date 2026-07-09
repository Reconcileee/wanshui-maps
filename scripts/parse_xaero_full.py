"""深入分析 region.xaero 的完整结构"""
import zipfile, io
from pathlib import Path
from nbtlib import Compound, String, Byte, Int, Short, Long, ByteArray, IntArray

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

zp = BASE / "0_0.zip"
with zipfile.ZipFile(zp) as z:
    raw = z.read("region.xaero")

header = raw[:10]
nbt_start = 10
print(f"header: {header.hex()}")

# 解析第一个 NBT, 记录消耗字节数
stream = io.BytesIO(raw[nbt_start:])
first = Compound.parse(stream)
consumed = stream.tell()
print(f"first NBT consumed {consumed} bytes")
print(f"first NBT: {dict(first)}")

# 看后续字节
after = raw[nbt_start + consumed:]
print(f"\nafter first NBT: {len(after)} bytes remain")
print(f"next 32 hex: {after[:32].hex()}")
print(f"next 64 ascii: {after[:64]!r}")

# 尝试继续解析
stream2 = io.BytesIO(after)
try:
    second = Compound.parse(stream2)
    consumed2 = stream2.tell()
    print(f"\nsecond NBT consumed {consumed2} bytes")
    print(f"second NBT: {dict(second)}")
except Exception as e:
    print(f"second Compound.parse fail: {e}")
    # 尝试其他类型
    print(f"next byte type: {hex(after[0])}")
    # 0x0a=Compound, 0x08=String, 0x0b=IntArray, 0x0c=LongArray
    # 如果不是 NBT, 可能是 chunk 块数据
