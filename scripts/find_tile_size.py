"""把 cache/1/8_7.xwmc 的 pixel data 渲染成不同尺寸，找到正确的布局

假设 pixel_start 在 biome 结束后不久
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

raw = read_xwmc(BASE / "1" / "8_7.xwmc")

# 找到 biome 结束的位置
# 已知 biome 在 offset 211 (len=16, "minecraft:plains")
biome_end = 211 + 1 + 16  # 228
print(f"Biome ends at offset {biome_end}")

# 看看 biome_end 之后的数据
print(f"Bytes 228-260: {raw[228:260].hex()}")

# 尝试不同的 pixel_start
for px_start in [228, 232, 236, 240, 244, 248, 252, 256]:
    pixel_data = raw[px_start:]
    n_pixels = len(pixel_data) // 4
    
    print(f"\npx_start={px_start}: {len(pixel_data)} bytes = {n_pixels} pixels")
    
    # 尝试不同的宽度
    # 24 chunks * 16 px = 384 px? 不对，n_pixels 太大了
    # 试试更大的尺寸
    for w in [256, 384, 512, 640, 768, 896, 1024, 1280, 1536]:
        h = n_pixels // w
        if h < 10:
            continue
        actual = w * h
        rem = len(pixel_data) - actual * 4
        if abs(rem) > 1024:
            continue
        
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for y in range(h):
            for x in range(w):
                idx = (y * w + x) * 4
                if idx + 3 >= len(pixel_data):
                    break
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                img.putpixel((x, y), (r, g, b, a))
        
        # 统计不透明像素
        opaque = sum(1 for y in range(h) for x in range(w) if img.getpixel((x, y))[3] > 0)
        if opaque > 100:  # 至少有一些不透明像素
            out_path = OUT / f"l1_8_7_px{px_start}_{w}x{h}.png"
            img.save(out_path)
            print(f"  {w}x{h}: opaque={opaque}, saved")
