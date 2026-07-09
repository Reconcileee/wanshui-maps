"""检查 .xwmc 文件格式头部。"""
from pathlib import Path

f = Path("1.19.2TOBU0405/XaeroWorldMap/新的世界/null/cache/1/0_0.xwmc")
data = f.read_bytes()
print(f"文件大小: {len(data)} bytes")
print(f"前 64 字节 (hex): {data[:64].hex()}")

if data[:4] == b"\x89PNG":
    print("格式: PNG")
elif data[:2] == b"\xff\xd8":
    print("格式: JPEG")
elif data[:4] == b"RIFF":
    print("格式: WebP")
else:
    print("格式: 自定义二进制")
    for i in range(0, min(32, len(data))):
        c = chr(data[i]) if 32 <= data[i] < 127 else "?"
        print(f"  offset {i}: {data[i]:3d} (0x{data[i]:02x}) char={c}")

# 检查所有 cache 目录的文件
cache_dir = Path("1.19.2TOBU0405/XaeroWorldMap/新的世界/null/cache")
for z in sorted(cache_dir.iterdir()):
    if z.is_dir():
        files = list(z.glob("*.xwmc"))
        print(f"\nzoom {z.name}: {len(files)} 文件")
        for f in sorted(files)[:5]:
            print(f"  {f.name}: {f.stat().st_size} bytes")
