"""Hex dump 关键位置以理解 cache.xaero 的实际结构"""
import zipfile
import struct
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def hexdump(data, start, length, label=""):
    """打印 hex dump"""
    end = min(start + length, len(data))
    print(f"\n--- {label} (pos {start}-{end}) ---")
    for i in range(start, end, 16):
        chunk = data[i:min(i+16, end)]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {i:6d}: {hex_str:<48s}  {ascii_str}")

raw = read_xwmc(3, 0, 0)
print(f"Total size: {len(raw)} bytes")

# 1. 文件头部
hexdump(raw, 0, 32, "FILE HEADER")

# 2. 第一个纹理结束后的区域 (pos 35148-35200)
hexdump(raw, 35145, 64, "AFTER FIRST TEXTURE")

# 3. 文件末尾
hexdump(raw, len(raw)-32, 32, "FILE END")

# 4. 在剩余 6161 字节中搜索 0xFF 字节 (可能的分隔符)
print("\n--- 0xFF bytes in range 35150-41311 ---")
remaining = raw[35150:]
ff_positions = [i + 35150 for i, b in enumerate(remaining) if b == 0xFF]
print(f"  Count: {len(ff_positions)}")
if len(ff_positions) <= 30:
    for p in ff_positions:
        context = raw[max(0,p-2):p+3]
        print(f"  pos {p}: ...{context.hex()}...")
else:
    print(f"  First 20: {ff_positions[:20]}")
    print(f"  Last 5: {ff_positions[-5:]}")

# 5. 尝试不同的 biome index 大小
# 如果 biome indices 更大, 第一个纹理会消耗更多字节
print("\n--- Trying different biome index sizes ---")
# 第一个纹理的 biome palette 在 pos 33031
# perTexturePaletteSize = 11
# 如果 bitsPerEntry 不同:
for bpe in [4, 5, 6, 7, 8, 13]:
    inside = 64 // bpe
    data_len = (4096 + inside - 1) // inside
    biome_bytes = data_len * 8
    # 计算第一个纹理总大小
    tex_size = 1 + 1 + 4 + 4 + 16384 + 1 + 8192 + 8192 + 4 + 66 + 1 + biome_bytes
    total_with_header = 252 + tex_size
    remaining_after = len(raw) - total_with_header
    print(f"  bpe={bpe}: biome_bytes={biome_bytes}, tex_total={tex_size}, "
          f"file_pos={total_with_header}, remaining={remaining_after}")

# 6. 检查 6161 字节是否可能是另一个没有 height data 的纹理
print("\n--- If 6161 bytes is a 2nd texture without height data ---")
# 6161 = 1(coord) + 1(compressed) + 4(format) + 4(buflen) + N(pixels) + 1(hasLight) + biome
# 6161 - 11 = 6150 for pixels + biome
# If pixels = 4096 (32x32), biome = 6150 - 4096 = 2054
# If pixels = 1024 (16x16), biome = 6150 - 1024 = 5126
print(f"  6161 - 11(header) = 6150 for pixels+biome")
print(f"  If 32x32 pixels (4096B): biome = {6150-4096}")
print(f"  If 16x16 pixels (1024B): biome = {6150-1024}")

# 7. 最关键的检查: 在 pos 35150 处, 尝试作为新纹理解析
# 但先检查 pos 35150 的字节是否可能是 0xFF terminator 被跳过了
print(f"\n--- Critical byte check ---")
print(f"  raw[35149] = 0x{raw[35149]:02x}")
print(f"  raw[35150] = 0x{raw[35150]:02x}")
print(f"  raw[35151] = 0x{raw[35151]:02x}")

# 8. 也许 biome indices 后面还有更多数据?
# 检查 pos 33100 (biome indices start) 之后的数据
hexdump(raw, 33095, 32, "AROUND BIOME INDICES START")
