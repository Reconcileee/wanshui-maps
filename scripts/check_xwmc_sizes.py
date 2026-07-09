"""检查多个 .xwmc 文件大小, 判断是否稀疏存储"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

for sub in ["1", "2", "3"]:
    d = BASE / sub
    files = sorted(d.glob("*.xwmc"))
    print(f"\n=== cache/{sub}/ ({len(files)} files) ===")
    for f in files[:10]:
        with zipfile.ZipFile(f) as z:
            raw = z.read("cache.xaero")
        if len(raw) < 16:
            print(f"  {f.name}: too small ({len(raw)} bytes)")
            continue
        # 解析头部 + palette
        biome_count = (raw[12] << 8) | raw[13]
        off = 16
        try:
            for i in range(biome_count):
                if off >= len(raw):
                    break
                slen = raw[off]
                off += 1
                off += slen
                while off + 1 < len(raw) and raw[off] == 0 and raw[off+1] == 0:
                    off += 2
                    break
        except IndexError:
            print(f"  {f.name}: parse error at off={off}, total={len(raw)}")
            continue
        pixel_size = len(raw) - off
        print(f"  {f.name}: total={len(raw)}, palette_end={off}, pixel_data={pixel_size}, pixel%4={pixel_size%4}, pixel%1024={pixel_size%1024}")
