"""解析 Xaero region.xaero: 10 字节头 + raw NBT"""
import zipfile, io
from pathlib import Path
from nbtlib import File, Compound, List, tag

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

zp = BASE / "0_0.zip"
with zipfile.ZipFile(zp) as z:
    raw = z.read("region.xaero")

print(f"raw size: {len(raw)}")
print(f"header 10 bytes: {raw[:10].hex()}")
# ff 00 06 00 08 00 02 70 00 01
# 偏移 10 开始 NBT (0a 00 00 = TAG_Compound empty name)

nbt_data = raw[10:]
print(f"nbt size: {len(nbt_data)}, first byte: {hex(nbt_data[0])}")

# 尝试 nbtlib File.parse (raw, 非 gzip)
try:
    f = File.parse(io.BytesIO(nbt_data), gzipped=False)
    root = f
    print(f"File.parse ok, root keys: {list(root.keys())}")
except Exception as e:
    print(f"File.parse raw fail: {e}")
    # 尝试直接 Compound
    try:
        c = Compound.parse(io.BytesIO(nbt_data))
        print(f"Compound.parse ok, keys: {list(c.keys())}")
        root = c
    except Exception as e2:
        print(f"Compound.parse fail: {e2}")
        root = None

if root:
    print(f"\n=== root 结构 ===")
    def show(tag, indent=0, max_depth=3):
        if indent > max_depth:
            return
        prefix = "  " * indent
        if isinstance(tag, Compound):
            for k, v in tag.items():
                t = type(v).__name__
                if isinstance(v, (Compound, List)):
                    print(f"{prefix}{k}: {t}({len(v)})")
                    show(v, indent+1, max_depth)
                else:
                    val = str(v)
                    if len(val) > 60:
                        val = val[:60] + "..."
                    print(f"{prefix}{k}: {t} = {val}")
        elif isinstance(tag, List):
            if len(tag) > 0:
                print(f"{prefix}[0]: {type(tag[0]).__name__}")
                show(tag[0], indent+1, max_depth)
            print(f"{prefix}... total {len(tag)} items")
    show(root)
