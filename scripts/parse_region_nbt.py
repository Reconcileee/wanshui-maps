import zipfile
from pathlib import Path
from nbtlib import Compound
import io

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

def read_region(tx, tz):
    path = BASE / f"{tx}_{tz}.zip"
    with zipfile.ZipFile(path) as z:
        return z.read("region.xaero")

# 读 0_0.zip
raw = read_region(0, 0)
print(f"region.xaero size: {len(raw)} bytes")

# 前 10 字节是 header
print(f"\n=== First 10 bytes (header) ===")
for i in range(10):
    print(f"  byte {i}: 0x{raw[i]:02x} ({raw[i]:3d})")

# 试试解析 NBT
print(f"\n=== Trying to parse NBT from byte 10 ===")
try:
    nbt_data = raw[10:]
    stream = io.BytesIO(nbt_data)
    c = Compound.parse(stream)
    print(f"Parsed successfully!")
    print(f"Root keys: {list(c.keys())}")
    
    # 打印根节点的结构
    def print_nbt(tag, indent=0, max_depth=3):
        if indent > max_depth:
            return
        prefix = "  " * indent
        if isinstance(tag, dict):
            for key, value in tag.items():
                print(f"{prefix}{key}: {type(value).__name__}")
                print_nbt(value, indent + 1, max_depth)
        elif isinstance(tag, list):
            print(f"{prefix}List[{len(tag)}] of {type(tag[0]).__name__ if tag else 'unknown'}")
            if len(tag) > 0:
                print_nbt(tag[0], indent + 1, max_depth)
        else:
            print(f"{prefix}= {repr(tag)[:80]}")
    
    print_nbt(c)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
