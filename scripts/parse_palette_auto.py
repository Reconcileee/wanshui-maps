"""修正 palette 解析算法 - 不假设 biome_count 位置

之前的问题: 低 zoom level 文件中 biome_count 字节位置可能不对
让我用更可靠的方法: 从 offset 16 开始搜索 'minecraft:' 字符串
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def parse_palette_auto(raw):
    """从 offset 16 开始自动解析 biome palette, 返回 (biomes, pixel_start)"""
    off = 16
    biomes = []
    while off < len(raw):
        # 跳过 0 字节
        while off < len(raw) and raw[off] == 0:
            off += 1
        if off >= len(raw):
            break
        slen = raw[off]
        # 检查是否是合理的字符串长度
        if slen < 10 or slen > 64:  # minecraft:xxx 至少 11 字符
            break
        if off + 1 + slen > len(raw):
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        biomes.append(name)
        off += 1 + slen
    # off 现在是最后一个 biome 后第一个非 0 字节 (或文件末尾)
    # pixel data 应该从 off 开始
    return biomes, off

# 测试所有文件
for level in ["3", "2", "1"]:
    d = BASE / level
    files = sorted(d.glob("*.xwmc"))
    print(f"\n=== cache/{level}/ ({len(files)} files) ===")
    for fn in files[:3]:
        with zipfile.ZipFile(fn) as z:
            raw = z.read("cache.xaero")
        biomes, pixel_start = parse_palette_auto(raw)
        pixel_data = raw[pixel_start:]
        n_pixels = len(pixel_data) // 4
        extra = len(pixel_data) % 4
        print(f"  {fn.name}: total={len(raw)}, biomes={len(biomes)}, pixel_start={pixel_start}, pixels={n_pixels}, extra={extra}")
        if biomes:
            print(f"    first: {biomes[0]}, last: {biomes[-1]}")

# 详细看 cache/2/0_0.xwmc
print("\n=== Detailed: cache/2/0_0.xwmc ===")
fn = BASE / "2" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

biomes, pixel_start = parse_palette_auto(raw)
print(f"biomes: {len(biomes)}")
for i, b in enumerate(biomes[:5]):
    print(f"  [{i}] {b}")
print(f"  ...")
for i, b in enumerate(biomes[-3:]):
    print(f"  [{len(biomes)-3+i}] {b}")

pixel_data = raw[pixel_start:]
print(f"pixel_data: {len(pixel_data)} bytes")
print(f"first 32 hex: {pixel_data[:32].hex()}")
print(f"first 32 dec: {list(pixel_data[:32])}")

# 如果 pixel_data 很大 (>100KB), 渲染看看
n_pixels = len(pixel_data) // 4
if n_pixels > 1000:
    # 尝试几个尺寸
    for w in [256, 512, 1024]:
        h = n_pixels // w
        if h > 0 and h < 2000:
            print(f"  try {w}x{h} = {w*h}px")
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            for i in range(w * h):
                a, r, g, b = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
                img.putpixel((i % w, i // w), (r, g, b, a))
            img.save(OUT / f"level2_0_0_{w}x{h}.png")
