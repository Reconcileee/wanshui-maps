"""验证 cache.xaero 格式: chunk 列表 (2字节头 + 1024字节ARGB)

假设:
- 16 bytes header
- biome palette (变长)
- N chunks: 每 chunk = 2 bytes (cx, cz signed) + 1024 bytes ARGB (16x16)
- 末尾 padding/元数据
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

# 严格解析 palette
def parse_palette(raw, start):
    off = start
    biomes = []
    while off < len(raw):
        while off < len(raw) and raw[off] == 0:
            off += 1
        if off >= len(raw):
            break
        slen = raw[off]
        if slen < 10 or slen > 64:
            break
        if off + 1 + slen > len(raw):
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        biomes.append(name)
        off += 1 + slen
    return biomes, off

biomes, palette_end = parse_palette(raw, 16)
# palette_end 后可能有 00 00 分隔, 包含在 pixel_data 中
# 之前分析: palette_end=256, 但 pixel_data 应从 254 开始 (含 00 00)
# 让我检查 palette_end 附近
print(f"palette_end = {palette_end}")
print(f"bytes at palette_end-2..palette_end+4: {raw[palette_end-2:palette_end+4].hex()}")
# 如果 palette_end=256, 前 2 字节是 00 00 (分隔), 那 pixel_data 应从 254 开始
# 让我两种都试

for pd_start in [palette_end - 2, palette_end, palette_end + 2]:
    print(f"\n=== trying pd_start={pd_start} ===")
    pixel_data = raw[pd_start:]
    print(f"pixel_data size: {len(pixel_data)}")
    print(f"first 16 hex: {pixel_data[:16].hex()}")

    # 假设: 每 chunk = 2 bytes header (cx, cz) + 1024 bytes ARGB
    chunk_total = 2 + 1024
    n_chunks = len(pixel_data) // chunk_total
    remainder = len(pixel_data) % chunk_total
    print(f"chunk_size={chunk_total}, n_chunks={n_chunks}, remainder={remainder}")

    # 检查前 5 个 chunk 的 header 是否合理 (cx, cz 在 -32~31 范围)
    print(f"first 5 chunk headers:")
    valid_count = 0
    for i in range(min(5, n_chunks)):
        off = i * chunk_total
        cx = pixel_data[off]
        cz = pixel_data[off + 1]
        # signed
        if cx >= 128:
            cx -= 256
        if cz >= 128:
            cz -= 256
        print(f"  chunk {i}: cx={cx}, cz={cz}")
        if -32 <= cx <= 31 and -32 <= cz <= 31:
            valid_count += 1

    # 如果前 5 个都合理, 尝试生成 PNG
    if valid_count >= 3:
        print(f"  -> headers look valid! generating PNG...")
        # 找出 chunk 坐标范围
        coords = []
        for i in range(n_chunks):
            off = i * chunk_total
            cx = pixel_data[off]
            cz = pixel_data[off + 1]
            if cx >= 128:
                cx -= 256
            if cz >= 128:
                cz -= 256
            coords.append((cx, cz))

        min_cx = min(c[0] for c in coords)
        max_cx = max(c[0] for c in coords)
        min_cz = min(c[1] for c in coords)
        max_cz = max(c[1] for c in coords)
        print(f"  cx range: {min_cx} to {max_cx}")
        print(f"  cz range: {min_cz} to {max_cz}")

        # 生成大图
        w = (max_cx - min_cx + 1) * 16
        h = (max_cz - min_cz + 1) * 16
        print(f"  image size: {w}x{h}")
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))

        for i, (cx, cz) in enumerate(coords):
            off = i * chunk_total + 2
            chunk_data = pixel_data[off:off + 1024]
            # 16x16 ARGB
            for py in range(16):
                for px in range(16):
                    idx = (py * 16 + px) * 4
                    if idx + 3 < len(chunk_data):
                        a, r, g, b = chunk_data[idx], chunk_data[idx+1], chunk_data[idx+2], chunk_data[idx+3]
                        # 放到大图上
                        abs_x = (cx - min_cx) * 16 + px
                        abs_y = (cz - min_cz) * 16 + py
                        if 0 <= abs_x < w and 0 <= abs_y < h:
                            img.putpixel((abs_x, abs_y), (r, g, b, a))

        out_file = OUT / f"pd{pd_start}_chunks{n_chunks}_{w}x{h}.png"
        img.save(out_file)
        print(f"  saved: {out_file}")

        # 也保存单个 chunk 看看
        if n_chunks > 0:
            chunk_img = Image.new('RGBA', (16, 16))
            off = 2
            chunk_data = pixel_data[off:off + 1024]
            for py in range(16):
                for px in range(16):
                    idx = (py * 16 + px) * 4
                    if idx + 3 < len(chunk_data):
                        a, r, g, b = chunk_data[idx], chunk_data[idx+1], chunk_data[idx+2], chunk_data[idx+3]
                        chunk_img.putpixel((px, py), (r, g, b, a))
            chunk_img.resize((128, 128)).save(OUT / f"pd{pd_start}_chunk0_16x16.png")
