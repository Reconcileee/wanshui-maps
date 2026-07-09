"""修正 RLE 解析: 第一个字节可能不是 count

pixel_data 前 64 hex:
00008058 00004000 00284278 002b457d 0029457a 00284678 00284478 002a457b
00000000 00000000 ff000000 ff000000 ...

这看起来更像 ARGB 格式, 但 count 是 0 或 255
00 = alpha 0 (透明), ff = alpha 255 (不透明)
所以格式其实就是 ARGB, 每像素 4 字节!

但为什么 chunk 20 只有 12 种颜色, 且 (250, 7, 208, 64) 出现 576 次?
如果是 ARGB, 那 64 是 alpha, 250,7,208 是 RGB
这看起来是合理的颜色 (洋红色系)

等一下, 那为什么之前 4 个 chunk (0-3) 各只用了 48 bytes?
因为我之前假设 1024 字节 per chunk, 但其实是连续 ARGB

重新计算: 41057 bytes / 4 = 10264.25 像素
10264 像素 = 多少 chunks? 10264 / 256 = 40.09 chunks

但文件大小 41311, header+palette=254, pixel=41057
41057 / 4 = 10264.25, 不对, 有 1 字节多余

让我重新检查: palette_end 到底是多少?
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

print(f"total: {len(raw)}")
print(f"first 32: {raw[:32].hex()}")

# 重新解析 palette
# header: 00 01 00 18 00 01 2a 61 9d ff 00 00 00 0b 00 00
# byte 0-1: 00 01 = version?
# byte 2-3: 00 18 = 24 = tile size in chunks? (1 chunk = 16 pixels, 24*16=384)
# byte 4-7: 00 01 2a 61 = timestamp?
# byte 8-9: 9d ff = ?
# byte 10-11: 00 00 = ?
# byte 12-13: 00 0b = 11 = biome count
# byte 14-15: 00 00 = ?

# palette 从 offset 16 开始
# 14 6d 69 6e 65 63 72 61 66 74 3a 64 65 65 70 5f
# 14 = 20 = string length, "minecraft:deep_" 前面 20 字节?
# "minecraft:deep_ocean" = 22 bytes? 让我数
# m-i-n-e-c-r-a-f-t-:-d-e-e-p-_-o-c-e-a-n = 22 字节

# 等等, 第一个字节是 14 = 20, 但 "minecraft:deep_ocean" 是 22 字符
# 不对, 让我重新看
# raw[16] = 0x14 = 20
# raw[17:17+20] = "minecraft:deep_ocean" 不, "minecraft:" 是 10, "deep_ocean" 是 10, 共 20!

# 那 biome palette 的格式是: length(1 byte) + name(length bytes) + 00 00 分隔?
# 让我精确解析
biome_count = (raw[12] << 8) | raw[13]
print(f"\nbiome_count = {biome_count}")

off = 16
biomes = []
for i in range(biome_count):
    if off >= len(raw):
        break
    slen = raw[off]
    off += 1
    if off + slen > len(raw):
        break
    name = raw[off:off+slen].decode('utf-8', errors='replace')
    biomes.append(name)
    off += slen
    # 分隔符: 可能是 00 00
    if off + 1 < len(raw) and raw[off] == 0 and raw[off+1] == 0:
        off += 2

print(f"biomes ({len(biomes)}):")
for i, b in enumerate(biomes):
    print(f"  [{i}] {b}")
print(f"palette end at offset {off}")
print(f"next 8 bytes: {raw[off:off+8].hex()} = {list(raw[off:off+8])}")

pixel_start = off
pixel_data = raw[pixel_start:]
pixel_count = len(pixel_data) // 4
print(f"\npixel_data: {len(pixel_data)} bytes = {pixel_count} full pixels + {len(pixel_data)%4} extra")
print(f"extra bytes: {pixel_data[pixel_count*4:].hex()}")

# 如果是 ARGB, 10264 像素 = 什么尺寸?
# 尝试不同的宽高
for w in [16, 32, 64, 128, 256, 384, 512]:
    h = pixel_count // w
    if h > 0:
        print(f"  {w} x {h} = {w*h} pixels (剩 {pixel_count - w*h})")

# 关键: 如果 tile size = 24 chunks (byte 2-3 = 24), 每 chunk 16 像素
# 那 tile 尺寸 = 24 * 16 = 384 像素
# 384 * 384 = 147456 像素, 但只有 10264 像素, 不对

# 或者: 24 是 chunk 数量, 但只是部分 chunks (稀疏)
# 10264 / 256 = 40.09, 约 40 个 chunks
# 但 byte 2-3 = 24, 不是 40

# 让我看看其他 zoom level 的文件大小
print("\n=== Checking cache/2/ and cache/1/ ===")
for level in ["2", "1"]:
    d = BASE / level
    files = sorted(d.glob("*.xwmc"))
    print(f"\ncache/{level}/ ({len(files)} files):")
    for fn in files[:5]:
        with zipfile.ZipFile(fn) as z:
            raw2 = z.read("cache.xaero")
        bc = (raw2[12] << 8) | raw2[13]
        ts = (raw2[2] << 8) | raw2[3]  # tile size?
        print(f"  {fn.name}: total={len(raw2)}, biome_count={bc}, byte2-3={ts}")
