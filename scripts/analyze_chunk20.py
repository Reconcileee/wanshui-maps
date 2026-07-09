"""分析 chunk 20 的原始数据, 找出 (250, 7, 208, 64) 模式来源"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

pixel_data = raw[254:]

# chunk 20 从 offset 20480 开始, 1024 bytes
chunk20 = pixel_data[20480:21504]
print(f"chunk20 size: {len(chunk20)}")
print(f"first 64 hex: {chunk20[:64].hex()}")
print(f"first 64 dec: {list(chunk20[:64])}")

# 找 250, 7, 208, 64 模式 (fa 07 d0 40)
pattern = bytes([250, 7, 208, 64])
pos = chunk20.find(pattern)
print(f"\n'fa 07 d0 40' first found at offset {pos} in chunk20")

# 看这个模式周围
if pos >= 0:
    start = max(0, pos - 8)
    end = min(len(chunk20), pos + 16)
    print(f"context: {chunk20[start:end].hex()}")
    print(f"context dec: {list(chunk20[start:end])}")

# 检查是否是 2-byte 模式
# fa 07 = 64007, d0 40 = 53312
# 或者 fa = 250, 07 = 7, d0 = 208, 40 = 64
# 如果是 2-byte little-endian: 07fa = 2042, 40d0 = 16624
# 如果是 2-byte big-endian: fa07 = 64007, d040 = 53312

# 看是否整个 chunk20 都是重复模式
print(f"\n--- chunk20 pattern analysis ---")
# 检查 4-byte 重复
for period in [2, 3, 4, 5, 6, 8, 16]:
    matches = 0
    for i in range(0, len(chunk20) - period, period):
        if chunk20[i:i+period] == chunk20[i+period:i+2*period]:
            matches += 1
    print(f"  period {period}: {matches} repeats ({matches*period}/{len(chunk20)} bytes)")

# 直接看 chunk20 的字节频率
from collections import Counter
c = Counter(chunk20)
print(f"\nchunk20 byte frequency (top 5):")
for b, n in c.most_common(5):
    print(f"  0x{b:02x} ({b}): {n}")

# 看是否是 RLE 编码
# 如果是 RLE: count + value
# fa 07 d0 40 可能是 count=250, value=07, 然后 count=208, value=64?
# 或 count=fa=250, color=07d040?
print(f"\n--- RLE hypothesis ---")
# 试 1 byte count + 3 byte RGB
off = 0
rle_pixels = 0
while off + 4 <= len(chunk20) and rle_pixels < 300:
    count = chunk20[off]
    r, g, b = chunk20[off+1], chunk20[off+2], chunk20[off+3]
    if rle_pixels < 50 or count > 10:
        print(f"  off={off}: count={count}, RGB=({r},{g},{b})")
    rle_pixels += count
    off += 4
    if off >= len(chunk20):
        break
print(f"  total pixels from RLE: {rle_pixels}, off={off}")
