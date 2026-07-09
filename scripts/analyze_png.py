"""分析生成的 PNG 颜色分布, 判断是否像地图"""
from pathlib import Path
from PIL import Image
from collections import Counter

OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")

for png_file in sorted(OUT.glob("arrange_*.png")):
    img = Image.open(png_file)
    print(f"\n=== {png_file.name} ({img.size}) ===")
    colors = Counter()
    for px in img.getdata():
        colors[px] += 1
    print(f"unique colors: {len(colors)}")
    print(f"top 10 colors (RGBA):")
    for c, n in colors.most_common(10):
        print(f"  {c}: {n}")

# 也看 single_chunk
for png_file in sorted(OUT.glob("single_chunk*.png")):
    img = Image.open(png_file)
    print(f"\n=== {png_file.name} ({img.size}) ===")
    colors = Counter()
    for px in img.getdata():
        colors[px] += 1
    print(f"unique colors: {len(colors)}")
    print(f"top 5 colors (RGBA):")
    for c, n in colors.most_common(5):
        print(f"  {c}: {n}")
