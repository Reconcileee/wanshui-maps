"""分析 cache.xaero 文件大小和结构, 寻找图像数据"""
import zipfile, io, struct
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

for level in ["1", "2", "3"]:
    d = BASE / level
    if not d.exists():
        continue
    files = sorted(d.glob("*.xwmc"))
    print(f"\n=== cache/{level}/ ({len(files)} files) ===")
    for f in files:
        size = f.stat().st_size
        with zipfile.ZipFile(f) as z:
            names = z.namelist()
            raw = z.read(names[0])
            print(f"  {f.name}: file={size}, {names[0]}={len(raw)}, first16={raw[:16].hex()}")

# 深入 cache/3/0_0.xwmc (最小缩放, 应该是单瓦片)
print("\n=== cache/3/0_0.xwmc 深入 ===")
f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")
print(f"size: {len(raw)}")
print(f"first 128 hex: {raw[:128].hex()}")
# 如果是 256x256 RGBA = 262144, 看是否匹配
print(f"256x256x4 = {256*256*4}")
# 检查是否像像素数据 (字节分布)
from collections import Counter
c = Counter(raw[:4096])
print(f"byte distribution (first 4096): unique={len(c)}, top5={c.most_common(5)}")
