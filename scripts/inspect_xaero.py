"""研究 Xaero region.xaero / cache.xaero 格式"""
import zipfile, zlib, os, struct
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")

# 1. 检查 .xwmc
xwmc = BASE / "cache" / "1" / "0_0.xwmc"
print(f"xwmc exists: {xwmc.exists()}, size: {xwmc.stat().st_size}")
with zipfile.ZipFile(xwmc) as z:
    names = z.namelist()
    print(f"xwmc zip entries: {names}")
    raw = z.read(names[0])
    print(f"{names[0]} size: {len(raw)}")
    print(f"first 32 hex: {raw[:32].hex()}")
    print(f"first 64 ascii: {raw[:64]!r}")
    # 尝试 zlib
    for off in [0,1,2,3,4,8,16]:
        try:
            d = zlib.decompress(raw[off:])
            print(f"zlib@{off} ok, decomp size: {len(d)}, first 32 hex: {d[:32].hex()}")
            break
        except:
            pass

# 2. 检查 cache 目录结构
cache = BASE / "cache"
print(f"\ncache subdirs:")
for sub in sorted(cache.iterdir()):
    if sub.is_dir():
        files = list(sub.iterdir())
        print(f"  {sub.name}/: {len(files)} files, sample: {[f.name for f in files[:3]]}")

# 3. region.xaero 深入分析
print("\n=== region.xaero 分析 ===")
zp = BASE / "0_0.zip"
with zipfile.ZipFile(zp) as z:
    raw = z.read("region.xaero")
print(f"raw size: {len(raw)}")
print(f"first 64 hex: {raw[:64].hex()}")
# 0xFF 开头，分析结构
# ff 00 06 00 08 00 02 70 00 01 0a 00 00 0a 00 0a
# 尝试解读为 chunk 块
off = 0
magic = raw[0]  # 0xFF
print(f"magic: {hex(magic)}")
# 读取后续
print(f"bytes 1-8: {raw[1:9].hex()}")
# 可能: version(2) + ?
# 扫描寻找 chunk 块标志
# 尝试解读为: 0xFF, then version, then chunk count
# ff 00 = magic+version?
# 06 00 = ?
# 08 00 = ?
# 02 70 = ?
# 尝试找重复模式
# 检查是否包含 PNG 签名
png_sig = b'\x89PNG\r\n\x1a\n'
idx = raw.find(png_sig)
print(f"PNG signature at: {idx}")
# 检查是否包含 JPEG
jpg_sig = b'\xff\xd8\xff'
idx = raw.find(jpg_sig)
print(f"JPEG signature at: {idx}")
