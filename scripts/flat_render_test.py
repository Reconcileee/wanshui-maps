"""
关键洞察：让我用单人游戏的 Xaero 数据 + .mca 参考来验证

但首先，让我试试一个更简单的假设：
cache.xaero 的像素数据是按 tile 内的 chunk 坐标排列的，
但坐标信息存在文件开头，而不是结尾！

让我重新检查 header 后的结构。

另外，让我试试每 chunk 不是 1024 字节，而是其他大小。
比如每 chunk 256 字节（16x16, 1 byte per pixel = biome index）。
40 chunks * 256 = 10240 bytes。
41055 / 256 = 160.37... 不对。

或者每 chunk 512 字节（height + biome）。
40 * 512 = 20480。
41055 / 512 = 80.2... 也不对。

等等，之前我验证过 ARGB 渲染是有意义的（有颜色）。
但那些"颜色"会不会是 height map？

让我想想：Xaero 的地图显示的是俯视图，有高度阴影。
所以像素数据可能是：
- 每像素 1 字节 biome index
- 每像素 1 字节 height
- 每像素 1 字节 light
等等，组合成彩色

或者：像素已经是预渲染的 RGBA 颜色了！
这就是为什么我之前渲染出来有颜色——因为那就是最终的地图颜色！

如果是这样，那像素数据就是预渲染的地图图片。
问题只是：图片的尺寸是多少？

让我试试不同的图片宽度，看哪个最合理。
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def get_pixel_start(raw):
    pos = 16
    last_end = 16
    while True:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1:
            break
        if idx > 0:
            slen = raw[idx-1]
            if 10 <= slen <= 64:
                name = raw[idx:idx+slen].decode('utf-8', errors='replace')
                if name.startswith('minecraft:'):
                    last_end = idx + slen
                    pos = last_end
                    continue
        pos = idx + 1
    while last_end < len(raw) and raw[last_end] == 0:
        last_end += 1
    return last_end

# 用 cache/3/0_0.xwmc 测试 (最小的)
raw = read_xwmc(BASE / "3" / "0_0.xwmc")
pixel_start = get_pixel_start(raw)
pixel_data = raw[pixel_start:]

print(f"pixel_data size: {len(pixel_data)}")

# 假设像素是 ARGB (4 bytes per pixel)
# 试试不同的宽度
print("\n=== Trying different image widths (ARGB) ===")
for w in [64, 80, 96, 100, 120, 128, 160, 200, 256, 320]:
    n_pixels = len(pixel_data) // 4
    h = n_pixels // w
    if h < 1:
        continue
    actual_pixels = w * h
    actual_bytes = actual_pixels * 4
    rem = len(pixel_data) - actual_bytes
    
    # 只渲染合理的比例 (不是太细长)
    if w > h * 4 or h > w * 4:
        continue
    
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            idx = (y * w + x) * 4
            if idx + 3 < len(pixel_data):
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                img.putpixel((x, y), (r, g, b, a))
    
    out_file = OUT / f"l3_flat_{w}x{h}.png"
    img.save(out_file)
    print(f"  {w}x{h} = {actual_pixels} px, rem={rem} bytes, saved {out_file.name}")

# 也试试 RGBA 顺序 (不是 ARGB)
print("\n=== Trying RGBA order ===")
for w in [64, 80, 128, 160, 256]:
    n_pixels = len(pixel_data) // 4
    h = n_pixels // w
    if h < 1:
        continue
    actual_pixels = w * h
    
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            idx = (y * w + x) * 4
            if idx + 3 < len(pixel_data):
                r, g, b, a = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                img.putpixel((x, y), (r, g, b, a))
    
    out_file = OUT / f"l3_flat_rgba_{w}x{h}.png"
    img.save(out_file)
    print(f"  {w}x{h} = saved {out_file.name}")
