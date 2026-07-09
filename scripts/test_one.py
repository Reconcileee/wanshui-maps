"""测试单个文件解析"""
import zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from extract_xaero_cache import parse_cache_xaero, render_tile, CACHE_BASE, OUT_DIR

path = CACHE_BASE / '3' / '0_0.xwmc'
with zipfile.ZipFile(path) as z:
    raw = z.read('cache.xaero')
parsed = parse_cache_xaero(raw)
print(f'Textures: {len(parsed["textures"])}')
for t in parsed['textures']:
    print(f'  ({t["i"]},{t["j"]}): bufLen={t["buffer_length"]}, colorFmt={t["color_format"]}')
img = render_tile(parsed, 0, 0, 3)
out = OUT_DIR / '3' / '0_0.png'
out.parent.mkdir(exist_ok=True)
img.save(out)
print(f'Saved: {out}')
