"""分析各 level 图像的 alpha/颜色分布, 判断哪种排列最像地图

还需要找出 trailing metadata 的格式 (chunk 坐标)
"""
import zipfile
from pathlib import Path
from PIL import Image
from collections import Counter

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")

def get_pixel_start(raw):
    first = raw.find(b'minecraft:')
    off = first - 1
    while off < len(raw):
        slen = raw[off]
        if slen < 10 or slen > 64:
            nxt = raw[off+1:].find(b'minecraft:')
            if nxt >= 0:
                off = off + 1 + nxt - 1
                continue
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        off += 1 + slen
    return off

# 分析每个 chunk 的颜色分布
def analyze_chunks(pixel_data, n_chunks):
    """返回每个 chunk 的 (非透明像素数, 颜色数, 主色)"""
    results = []
    for ci in range(n_chunks):
        chunk_off = ci * 1024
        if chunk_off + 1024 > len(pixel_data):
            break
        colors = Counter()
        opaque = 0
        for py in range(16):
            for px in range(16):
                idx = chunk_off + (py * 16 + px) * 4
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                if a > 0:
                    opaque += 1
                    colors[(r, g, b)] += 1
        n_colors = len(colors)
        top_color = colors.most_common(1)[0] if colors else ((0,0,0), 0)
        results.append((opaque, n_colors, top_color[0], top_color[1]))
    return results

# 分析 cache/1/0_0.xwmc
fn = BASE / "1" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")
px_start = get_pixel_start(raw)
pd = raw[px_start:]
n_chunks = len(pd) // 1024
print(f"cache/1/0_0.xwmc: {n_chunks} chunks")

chunk_info = analyze_chunks(pd, n_chunks)
empty_chunks = sum(1 for c in chunk_info if c[0] == 0)
print(f"empty chunks (0 opaque): {empty_chunks}")
print(f"non-empty chunks: {n_chunks - empty_chunks}")

# 非空 chunk 的分布 (前 30 个)
print(f"\nfirst 30 chunks opaque counts:")
for i in range(min(30, n_chunks)):
    print(f"  chunk {i:3d}: opaque={chunk_info[i][0]:4d}, colors={chunk_info[i][1]:3d}, top={chunk_info[i][2]} ({chunk_info[i][3]}px)")

# 如果是 24x24 = 576 chunks, 但只有 560 个, 那 16 个缺失的可能在末尾
# 或者 560 个全有数据, 但有些是空的

# 让我看看空 chunk 的位置
empty_positions = [i for i, c in enumerate(chunk_info) if c[0] == 0]
print(f"\nempty chunk positions ({len(empty_positions)}): {empty_positions[:20]}...")

# 如果是 24x24 布局, 空 chunks 应该在哪?
# 假设空 chunks 在末尾, 那数据是 row-major
# 560 / 24 = 23.33, 所以 23 整行 + 8 个
# 23 * 24 = 552, 560 - 552 = 8, 第 24 行有 8 个
# 空 chunks = 576 - 560 = 16, 在最后一行

# 让我验证: 如果按 24x24 排列, 只有 560 个 chunks (最后一行缺 16 个)
# 那图像应该有明显的右下角缺失
# 让我看最后一行的 chunks 分布

# 或者: 560 个 chunks 全有数据, 但排列不是 24x24
# 让我找最合理的排列: 有最多的空 chunks 在边缘

# 换个思路: trailing metadata 应该包含 chunk 坐标
# 560 chunks, trailing = 821 bytes
# 每个坐标 1 byte (cx, cz) = 2 bytes, 560 * 2 = 1120 > 821, 不对
# 每个坐标 1 byte (索引) = 1 byte, 560 bytes, 821 - 560 = 261 bytes header, 可能

# 或者: 坐标是 2 bytes each, 但只有非空 chunks 有坐标
# 非空 chunks 数 = n_chunks - empty_chunks
non_empty = n_chunks - empty_chunks
print(f"\nnon-empty chunks: {non_empty}")
print(f"trailing size: {len(pd) % 1024}")
print(f"non_empty * 2 = {non_empty * 2}")

# 如果 trailing = 821, non_empty * 2 = 2 * (560 - empty)
# 821 / 2 = 410.5, 不对
# 821 - 1 = 820, 820 / 2 = 410
# 可能有 410 个非空 chunks + 1 byte count + ...

# 让我直接数有多少个非空 chunk
print(f"\nNon-empty chunks count: {sum(1 for c in chunk_info if c[0] > 0)}")
