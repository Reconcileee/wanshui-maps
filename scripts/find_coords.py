"""根据新发现分析 trailing metadata

已知:
- tile 大小: 24x24 chunks (byte 2-3 = 24)
- 每 chunk 16x16 像素 = 1024 字节 ARGB
- cache/3/0_0.xwmc: 40 个 chunks
- trailing size: 95 bytes

chunk 坐标范围: 0-23 (1 字节足够)
40 chunks * 2 bytes (cx, cz) = 80 bytes
95 - 80 = 15 bytes header

让我们找坐标数据的位置
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
    """找到 pixel data 的起始位置 (最后一个 biome 字符串之后)"""
    # 找所有 minecraft: 的位置
    pos = 16
    last_end = 16
    while True:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1:
            break
        # 检查前一个字节是不是长度
        if idx > 0:
            slen = raw[idx-1]
            if slen >= 10 and slen <= 64:
                name = raw[idx:idx+slen].decode('utf-8', errors='replace')
                if name.startswith('minecraft:'):
                    last_end = idx + slen
                    pos = last_end
                    continue
        pos = idx + 1
    # 跳过末尾的 0 字节？
    # 不，直接返回最后一个 biome 结束的位置
    # 但需要跳过可能的 00 00 分隔符
    # 让我们检查后面几个字节
    while last_end < len(raw) and raw[last_end] == 0:
        last_end += 1
    return last_end

# 分析 cache/3/0_0.xwmc
raw = read_xwmc(BASE / "3" / "0_0.xwmc")
print(f"Total size: {len(raw)}")

pixel_start = get_pixel_start(raw)
print(f"Pixel start: {pixel_start}")

# 计算 chunk 数量
# 我们不知道 trailing 有多大，但我们可以假设 tile = 24x24 = 576 chunks
# 不对，实际只有 40 个有数据的 chunks

# 让我们从文件末尾往回找坐标
# 坐标都是 0-23 的值
# 找连续的 0-23 字节序列

trailing_candidates = []
for trail_size in range(80, 200):
    if pixel_start + 40*1024 + trail_size != len(raw):
        continue
    trailing = raw[-trail_size:]
    
    # 检查最后 80 字节是不是都在 0-23 范围内
    coords_bytes = trailing[-80:]
    all_valid = all(b <= 23 for b in coords_bytes)
    if all_valid:
        trailing_candidates.append((trail_size, trailing))
        print(f"  Found! trail_size={trail_size}, all 80 bytes <= 23")

if not trailing_candidates:
    # 试试不同 chunk 数量
    for n_chunks in range(30, 60):
        for trail_size in range(n_chunks*2, n_chunks*2 + 30):
            px_start = len(raw) - n_chunks*1024 - trail_size
            if px_start < 16:
                continue
            trailing = raw[px_start + n_chunks*1024:]
            coords_bytes = trailing[-n_chunks*2:]
            if len(coords_bytes) >= n_chunks*2:
                all_valid = all(b <= 23 for b in coords_bytes)
                if all_valid:
                    print(f"  n_chunks={n_chunks}, trail_size={trail_size}, px_start={px_start}")

# 直接试试: 假设 trailing 最后是坐标, 40 * 2 = 80 字节
# 从文件末尾取 80 字节
print("\n=== Trying last 80 bytes as coordinates ===")
coords_80 = raw[-80:]
all_0_23 = all(b <= 23 for b in coords_80)
print(f"All <= 23: {all_0_23}")
print(f"Values: {list(coords_80)}")

# 不对，让我直接从 pixel_start 开始算
# pixel_start = 256 (之前的结果)
# 40 chunks * 1024 = 40960
# 256 + 40960 = 41216
# trailing = 41311 - 41216 = 95 bytes
# trailing = raw[41216:41311] = 95 bytes

pixel_start = 256
n_chunks = 40
trailing_start = pixel_start + n_chunks * 1024
trailing = raw[trailing_start:]
print(f"\npixel_start={pixel_start}, n_chunks={n_chunks}, trailing_size={len(trailing)}")

# 让我们看看 trailing 里有多少个 0-23 的值
valid_bytes = sum(1 for b in trailing if b <= 23)
print(f"Valid bytes (0-23): {valid_bytes}/{len(trailing)}")

# 试试不同的坐标起始位置 (在 trailing 内部)
print("\n=== Trying different coordinate offsets within trailing ===")
for coord_offset in range(0, len(trailing) - 79):
    coords_bytes = trailing[coord_offset:coord_offset+80]
    valid = sum(1 for b in coords_bytes if b <= 23)
    if valid >= 75:  # 至少 75/80 有效
        print(f"  offset={coord_offset}: valid={valid}/80")
        # 解析坐标
        coords = []
        for i in range(0, 80, 2):
            cx = coords_bytes[i]
            cz = coords_bytes[i+1]
            coords.append((cx, cz))
        print(f"    First 10 coords: {coords[:10]}")
        print(f"    cx range: {min(c[0] for c in coords)} - {max(c[0] for c in coords)}")
        print(f"    cz range: {min(c[1] for c in coords)} - {max(c[1] for c in coords)}")
        
        # 渲染看看
        pixel_data = raw[pixel_start:trailing_start]
        min_cx = min(c[0] for c in coords)
        max_cx = max(c[0] for c in coords)
        min_cz = min(c[1] for c in coords)
        max_cz = max(c[1] for c in coords)
        w = (max_cx - min_cx + 1) * 16
        h = (max_cz - min_cz + 1) * 16
        if w <= 384 and h <= 384:
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            for ci, (cx, cz) in enumerate(coords):
                chunk_off = ci * 1024
                if chunk_off + 1024 > len(pixel_data):
                    break
                for py in range(16):
                    for px in range(16):
                        idx = chunk_off + (py * 16 + px) * 4
                        if idx + 3 < len(pixel_data):
                            a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                            abs_x = (cx - min_cx) * 16 + px
                            abs_y = (cz - min_cz) * 16 + py
                            if abs_x < w and abs_y < h:
                                img.putpixel((abs_x, abs_y), (r, g, b, a))
            out_file = OUT / f"level3_coffset_{coord_offset}.png"
            img.save(out_file)
            print(f"    Saved: {out_file.name} ({w}x{h})")
