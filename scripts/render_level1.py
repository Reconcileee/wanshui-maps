"""RLE 遇到 count=0 就停止了, 但 0 可能是合法的颜色值的一部分

重新看 pixel_data 前 64 字节:
80 58 00 00 40 00 00 3a 4a 6b 00 27 42 7a 00 27
42 7a 00 28 42 7a 00 2b 45 7d 00 2b 45 7d 00 2b
45 7d 00 2c 46 7e 00 2d 49 7d 00 28 44 79 00 2a
44 7c 00 28 46 78 00 2b 47 7c 00 29 47 79 00 2b

如果是 RGBA:
80 58 00 00 = RGBA(128,88,0,0) - 深棕色透明
40 00 00 3a = RGBA(64,0,0,58) - 深红色半透明
4a 6b 00 27 = RGBA(74,107,0,39) - 橄榄绿半透明
...

如果是 ARGB:
80 58 00 00 = ARGB(128,88,0,0) - 同上
40 00 00 3a = ARGB(64,0,0,58) - 同上

看起来都是半透明颜色, 合理

但 count=128 太大了? 不, 128 个连续同色像素是可能的
问题是: 第一个 byte 是 80 = 128, 那 count=128
然后 58 00 00 = RGB(88,0,0) = 深红

让我重新解码, 0 可能是 count=0 但也可能是颜色值的一部分
不, count=0 没有意义, 所以如果第一个 byte 是 0, 那可能是其他格式

等等, 第一个 byte 是 80 = 128, 不是 0
那为什么 RLE 只解码了 26 runs 就遇到了 count=0?
让我看看第 26 个 run 之后的字节

解码 26 runs 用了 104 bytes, 所以第 104 byte 是下一个 count
让我看看 offset 104 附近的字节
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

fn = BASE / "1" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

# 找 pixel_data 起始
first_mc = raw.find(b'minecraft:')
pal_start = first_mc - 1
off = pal_start
biomes = []
while off < len(raw):
    slen = raw[off]
    if slen < 10 or slen > 64:
        if raw[off+1:].find(b'minecraft:') >= 0:
            off += 1
            continue
        break
    name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes.append(name)
    off += 1 + slen
pixel_start = off
while pixel_start < len(raw) and raw[pixel_start] == 0:
    pixel_start += 1

pixel_data = raw[pixel_start:]
print(f"pixel_data size: {len(pixel_data)}")

# RLE 解码, 但 count=0 时检查后面是否还有数据
# 如果 count=0 但后面还有非 0 字节, 那可能是格式理解错了
# 实际上: count 不能为 0, 所以如果遇到 0, 那就是 padding 或其他数据

# 让我看看前 200 字节, 手动解析
print("\nfirst 200 bytes of pixel_data:")
for i in range(0, 200, 16):
    print(f"  {i:4d}: {' '.join(f'{b:02x}' for b in pixel_data[i:i+16])}")

# 手动解析前 30 个 RLE entries
print("\nManual RLE decode (first 30):")
off = 0
total = 0
for i in range(30):
    if off + 4 > len(pixel_data):
        break
    count = pixel_data[off]
    r, g, b = pixel_data[off+1], pixel_data[off+2], pixel_data[off+3]
    total += count
    print(f"  [{i:2d}] off={off:3d} count={count:3d} RGB=({r:3d},{g:3d},{b:3d}) total={total}")
    off += 4

# 第 26 个 run 后 count=0?
# 让我看看 offset 104 处 (26 * 4 = 104)
print(f"\noffset 104: {pixel_data[104]} (0x{pixel_data[104]:02x})")
print(f"bytes 104-107: {pixel_data[104]:02x} {pixel_data[105]:02x} {pixel_data[106]:02x} {pixel_data[107]:02x}")

# 如果 pixel_data 不是连续 RLE, 那是什么?
# 每 chunk 1024 字节 (16x16 ARGB)?
# 574257 / 1024 = 560.798... 不是整数
# 560 chunks * 1024 = 573440
# 574257 - 573440 = 817 bytes 剩余

# 560 chunks * 256 pixels = 143360 像素
# 384x384 = 147456 像素
# 147456 - 143360 = 4096 像素 = 16 chunks 缺失

# 如果 tile 是 24x24 = 576 chunks, 有 560 个有数据, 16 个缺失 (稀疏)
# 那 560 chunks, 每 chunk 1024 bytes ARGB = 573440 bytes
# 574257 - 573440 = 817 bytes 头部? 不对

# 等等, 让我重新想
# 如果格式是: chunk_count (2 bytes) + chunk list
# 每个 chunk: cx(1 byte) cz(1 byte) + 1024 bytes ARGB
# 560 chunks * 1026 = 574560 bytes > 574257, 不对
# 不对, 560 * 1026 = 574560, 比 pixel_data 大

# 或者: 每 chunk 是 1024 bytes, 按 24x24 顺序存储 (稀疏的用 0 填充)
# 576 chunks * 1024 = 589824 > 574257, 不对

# 让我看看 pixel_data 的大小和什么接近
# 574257 / 576 = 996.97 bytes per chunk (平均)
# 接近 1024, 但略小

# 可能是 RLE 压缩的 chunks, 每 chunk 大小不同
# 有一个 header 描述每个 chunk 的 offset

# 或者: 每 pixel 不是 4 bytes, 而是 2 bytes?
# 574257 / 2 = 287128.5 像素, 不太合理

# 让我回到 ARGB 假设, 直接渲染 cache/1/0_0.xwmc
# 如果是 384x373 = 143232 像素 (接近 143564), 那看看图像
print(f"\n--- Render as ARGB 384x373 ---")
n_pixels = len(pixel_data) // 4
img = Image.new('RGBA', (384, 374), (0, 0, 0, 0))
for i in range(384 * 374):
    if i * 4 + 3 >= len(pixel_data):
        break
    a, r, g, b = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
    img.putpixel((i % 384, i // 384), (r, g, b, a))
img.save(OUT / "level1_0_0_384x374_argb.png")
print("saved")

# 也试 RGBA 顺序
img2 = Image.new('RGBA', (384, 374), (0, 0, 0, 0))
for i in range(384 * 374):
    if i * 4 + 3 >= len(pixel_data):
        break
    r, g, b, a = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
    img2.putpixel((i % 384, i // 384), (r, g, b, a))
img2.save(OUT / "level1_0_0_384x374_rgba.png")
print("saved rgba")

# 试 1024x?
# 143564 / 1024 = 140.2
img3 = Image.new('RGBA', (1024, 140), (0, 0, 0, 0))
for i in range(1024 * 140):
    if i * 4 + 3 >= len(pixel_data):
        break
    a, r, g, b = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
    img3.putpixel((i % 1024, i // 1024), (r, g, b, a))
img3.save(OUT / "level1_0_0_1024x140_argb.png")
print("saved 1024x140")

# 试 512x280
img4 = Image.new('RGBA', (512, 280), (0, 0, 0, 0))
for i in range(512 * 280):
    if i * 4 + 3 >= len(pixel_data):
        break
    a, r, g, b = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
    img4.putpixel((i % 512, i // 512), (r, g, b, a))
img4.save(OUT / "level1_0_0_512x280_argb.png")
print("saved 512x280")
