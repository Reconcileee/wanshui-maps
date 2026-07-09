"""分析 cache.xaero 的 trailing metadata (文件末尾)

并且验证 chunk 排列方式
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

# 分析 cache/3/0_0.xwmc 的末尾
fn = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

print(f"Total size: {len(raw)}")

# 已知: pixel_start = 256, 40 chunks = 40960 bytes
# trailing 从 256 + 40960 = 41216 开始
pixel_start = 256
n_chunks = 40
trailing_start = pixel_start + n_chunks * 1024
trailing = raw[trailing_start:]
print(f"\nTrailing start: {trailing_start}")
print(f"Trailing size: {len(trailing)} bytes")
print(f"Trailing hex: {trailing.hex()}")
print(f"Trailing dec: {list(trailing)}")

# 让我们看看 trailing 里有什么
# 95 字节可能是什么?
# 40 个 chunk, 每个 chunk 2 bytes 坐标 (cx, cz) = 80 bytes
# 95 - 80 = 15 bytes header
# 或者: 40 chunks * 2 bytes + 一些额外数据

# 让我们试试 2-byte 坐标 (cx, cz) 从 trailing 末尾往前数
print("\n\n=== Trying trailing as chunk coordinates (from end) ===")
# 假设 trailing 最后是 40 * 4 = 160 bytes 的坐标? 不对, 95 < 160
# 40 * 2 = 80 bytes
coord_bytes = n_chunks * 2
if len(trailing) >= coord_bytes:
    coords_data = trailing[-coord_bytes:]
    coords = []
    for i in range(n_chunks):
        cx = coords_data[i*2]
        cz = coords_data[i*2+1]
        coords.append((cx, cz))
    print(f"Last 80 bytes as (cx, cz) pairs (unsigned byte):")
    for i in range(0, n_chunks, 5):
        print(f"  {coords[i:i+5]}")
    
    # 检查坐标范围
    all_cx = [c[0] for c in coords]
    all_cz = [c[1] for c in coords]
    print(f"\ncx range: {min(all_cx)} - {max(all_cx)}")
    print(f"cz range: {min(all_cz)} - {max(all_cz)}")

# 试试有符号字节
print("\n\n=== Signed byte coordinates ===")
if len(trailing) >= coord_bytes:
    coords_data = trailing[-coord_bytes:]
    coords = []
    for i in range(n_chunks):
        cx = coords_data[i*2] - 256 if coords_data[i*2] > 127 else coords_data[i*2]
        cz = coords_data[i*2+1] - 256 if coords_data[i*2+1] > 127 else coords_data[i*2+1]
        coords.append((cx, cz))
    print(f"Last 80 bytes as (cx, cz) pairs (signed byte):")
    for i in range(0, n_chunks, 5):
        print(f"  {coords[i:i+5]}")
    all_cx = [c[0] for c in coords]
    all_cz = [c[1] for c in coords]
    print(f"\ncx range: {min(all_cx)} - {max(all_cx)}")
    print(f"cz range: {min(all_cz)} - {max(all_cz)}")

# 用坐标来渲染!
# 如果这些坐标是 chunk 在 tile 内的偏移 (比如 0-23 或 0-?)
# 那我们可以按坐标排列 chunks
print("\n\n=== Rendering with coordinates ===")
pixel_data = raw[pixel_start:trailing_start]

# 先用无符号坐标试试
for signed in [False, True]:
    coords_data = trailing[-coord_bytes:] if len(trailing) >= coord_bytes else None
    if not coords_data:
        continue
    
    coords = []
    for i in range(n_chunks):
        cx = coords_data[i*2]
        cz = coords_data[i*2+1]
        if signed:
            cx = cx - 256 if cx > 127 else cx
            cz = cz - 256 if cz > 127 else cz
        coords.append((cx, cz))
    
    # 计算边界
    min_cx = min(c[0] for c in coords)
    max_cx = max(c[0] for c in coords)
    min_cz = min(c[1] for c in coords)
    max_cz = max(c[1] for c in coords)
    
    w = (max_cx - min_cx + 1) * 16
    h = (max_cz - min_cz + 1) * 16
    
    if w > 0 and h > 0 and w < 2000 and h < 2000:
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
        
        suffix = "signed" if signed else "unsigned"
        out_file = OUT / f"level3_0_0_coords_{suffix}.png"
        img.save(out_file)
        print(f"  Rendered with {suffix} coords: {w}x{h} px, cx=[{min_cx},{max_cx}], cz=[{min_cz},{max_cz}]")
        print(f"    Saved to: {out_file.name}")
