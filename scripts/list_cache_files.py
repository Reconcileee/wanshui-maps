"""列出所有 cache 目录下的文件，了解坐标范围和文件大小分布"""
import zipfile
from pathlib import Path
import re

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def parse_filename(name):
    """解析 x_y.xwmc 文件名返回 (x, y)"""
    m = re.match(r'(-?\d+)_(-?\d+)\.xwmc', name)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None

for level in ["1", "2", "3"]:
    level_dir = BASE / level
    if not level_dir.exists():
        continue
    files = list(level_dir.glob("*.xwmc"))
    print(f"\n=== cache/{level}: {len(files)} files ===")
    
    coords = []
    sizes = []
    for f in files:
        c = parse_filename(f.name)
        if c:
            coords.append(c)
            with zipfile.ZipFile(f) as z:
                raw = z.read("cache.xaero")
                sizes.append(len(raw))
    
    if coords:
        xs = [c[0] for c in coords]
        zs = [c[1] for c in coords]
        print(f"  X range: {min(xs)} to {max(xs)} ({max(xs)-min(xs)+1} tiles)")
        print(f"  Z range: {min(zs)} to {max(zs)} ({max(zs)-min(zs)+1} tiles)")
        print(f"  Total tiles in grid: {(max(xs)-min(xs)+1) * (max(zs)-min(zs)+1)}")
        print(f"  Actual files: {len(coords)}")
    
    if sizes:
        print(f"  Size range: {min(sizes)} - {max(sizes)} bytes")
        print(f"  Average size: {sum(sizes)//len(sizes)} bytes")
        
        # 按大小分桶
        sizes.sort()
        print(f"  Size distribution (first 10): {sizes[:10]}")
        print(f"  Size distribution (last 10): {sizes[-10:]}")
