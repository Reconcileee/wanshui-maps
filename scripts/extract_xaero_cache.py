"""
Xaero's World Map cache.xaero 解析器 → PNG 瓦片生成器

关键发现 (通过反编译 JAR + 实证验证):
  - biome index 的 ConsistentBitArray 使用 bpe=13 (与 heightValues 相同)
    而非根据 paletteSize 计算。验证: bpe=13 时 4096/4096 索引有效 (0-11)。
  - biome index 数组有 2 个额外 longs (16 字节), 原因可能是 Paletted2DFastBitArrayIntStorage
    的 data[] 分配了额外容量。处理方式: 读取 1024 longs 后, 跳过剩余字节直到 0xFF。
"""
import zipfile
import struct
from pathlib import Path
from PIL import Image

CACHE_BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_Unknown\null\mw$-615768317\cache")
OUT_DIR = Path(r"d:\aiide_project\trae_project\projects\minecraft_map\frontend\tiles\xaero")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEXTURE_PX = 64          # 每个纹理 64x64 像素
TILE_TEXTURES = 8        # 8x8 纹理网格
TILE_PX = TILE_TEXTURES * TEXTURE_PX  # 512x512 像素


class CacheReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read_byte(self) -> int:
        v = self.data[self.pos]; self.pos += 1
        return v & 0xFF

    def read_int(self) -> int:
        v = struct.unpack('>i', self.data[self.pos:self.pos+4])[0]; self.pos += 4
        return v

    def read_unsigned_int(self) -> int:
        v = struct.unpack('>I', self.data[self.pos:self.pos+4])[0]; self.pos += 4
        return v

    def read_short(self) -> int:
        v = struct.unpack('>h', self.data[self.pos:self.pos+2])[0]; self.pos += 2
        return v

    def read_unsigned_short(self) -> int:
        v = struct.unpack('>H', self.data[self.pos:self.pos+2])[0]; self.pos += 2
        return v

    def read_bytes(self, n: int) -> bytes:
        v = self.data[self.pos:self.pos+n]; self.pos += n
        return v

    def read_boolean(self) -> bool:
        return self.read_byte() != 0

    def read_utf(self) -> str:
        length = self.read_unsigned_short()
        raw = self.read_bytes(length)
        return raw.decode('utf-8', errors='replace')

    def skip_longs(self, n: int):
        self.pos += n * 8

    def remaining(self) -> int:
        return len(self.data) - self.pos


def parse_cache_xaero(raw: bytes) -> dict:
    """解析 cache.xaero，返回纹理数据 (仅像素数据, 忽略 height/biome)"""
    reader = CacheReader(raw)

    # 1. 版本号
    version = reader.read_unsigned_int()

    # 2. 缓存元数据 (纹理清单)
    textures_meta = []
    while True:
        coord = reader.read_byte()
        if coord == 0xFF:
            break
        # spec section 6: byte = (j << 4) | i, high nibble = j (Z), low nibble = i (X)
        i = coord & 0x0F
        j = coord >> 4
        tex_version = reader.read_int()
        textures_meta.append({'i': i, 'j': j, 'version': tex_version})

    # 3. 生物群系调色板
    palette_size = reader.read_int()
    for _ in range(palette_size):
        marker = reader.read_byte()
        if marker != 0xFF:
            reader.read_utf()

    # 4. 纹理循环
    # colorFormat = 32856 = 0x00008058, 大端字节: 00 00 80 58
    COLOR_FORMAT_BE = b'\x00\x00\x80\x58'
    textures = []

    while reader.remaining() > 1:
        start_pos = reader.pos
        coord = reader.read_byte()
        if coord == 0xFF:
            break

        # spec section 6: byte = (j << 4) | i
        i = coord & 0x0F
        j = coord >> 4

        # writeCacheMapData
        compressed = reader.read_byte()
        color_format = reader.read_int()
        buffer_length = reader.read_int()

        if buffer_length < 0 or buffer_length > 100000:
            # 解析出错 - 搜索下一个有效的 texture header
            search_start = start_pos + 1
            next_cf = reader.data.find(COLOR_FORMAT_BE, search_start)
            if next_cf == -1:
                break
            # colorFormat 前面有 coord(1B) + compressed(1B), 所以 coord 在 next_cf - 2
            reader.pos = next_cf - 2
            continue

        if reader.remaining() < buffer_length:
            break
        pixel_data = reader.read_bytes(buffer_length)

        textures.append({
            'i': i,
            'j': j,
            'pixel_data': pixel_data,
            'color_format': color_format,
            'buffer_length': buffer_length,
        })

        # 跳过当前纹理的剩余数据 (hasLight + heights + biome),
        # 搜索下一个 texture header 或 0xFF terminator
        # colorFormat 32856 = 0x00008058 在数据中应唯一标识 texture header
        search_pos = reader.pos
        while reader.remaining() > 1:
            # 查找下一个 colorFormat 标记
            next_cf = reader.data.find(COLOR_FORMAT_BE, search_pos)
            if next_cf == -1:
                # 没有更多 texture, 查找 0xFF terminator
                ff_pos = reader.data.find(b'\xff', search_pos)
                if ff_pos != -1:
                    reader.pos = ff_pos
                else:
                    reader.pos = len(reader.data)
                break
            # 检查 next_cf 前面 2 字节是否是有效 coord + compressed
            if next_cf >= 2:
                prev_coord = reader.data[next_cf - 2]
                prev_compressed = reader.data[next_cf - 1]
                # coord: 高4位和低4位都 0-7, compressed: 0 或 1
                if (prev_coord >> 4) <= 7 and (prev_coord & 0x0F) <= 7 and prev_compressed <= 1:
                    reader.pos = next_cf - 2
                    break
            search_pos = next_cf + 1

    return {
        'version': version,
        'textures_meta': textures_meta,
        'textures': textures,
    }


def render_tile(parsed: dict, tile_x: int, tile_z: int, level: int) -> Image.Image:
    """将解析后的数据渲染为 512x512 PNG 瓦片"""
    img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))

    for tex in parsed['textures']:
        ti = tex['i']  # X 轴纹理索引 0-7
        tj = tex['j']  # Z 轴纹理索引 0-7
        pixel_data = tex['pixel_data']
        buf_len = tex['buffer_length']

        if buf_len == TEXTURE_PX * TEXTURE_PX * 4:
            # 64x64 RGBA, 行优先
            tex_img = Image.frombytes('RGBA', (TEXTURE_PX, TEXTURE_PX), pixel_data)
            offset_x = ti * TEXTURE_PX
            offset_y = tj * TEXTURE_PX
            img.paste(tex_img, (offset_x, offset_y))
        else:
            print(f"    WARNING: texture ({ti},{tj}) bufLen={buf_len} != {TEXTURE_PX*TEXTURE_PX*4}")

    return img


def process_all_cache_files():
    """处理所有 cache 文件，生成 PNG 瓦片"""
    stats = {'tiles': 0, 'levels': set(), 'errors': [], 'textures': 0}

    for level_dir in sorted(CACHE_BASE.iterdir()):
        if not level_dir.is_dir():
            continue
        level = level_dir.name
        stats['levels'].add(level)

        level_out = OUT_DIR / level
        level_out.mkdir(exist_ok=True)

        xwmc_files = sorted(level_dir.glob('*.xwmc'))
        print(f"\n=== Level {level}: {len(xwmc_files)} files ===")

        for xwmc_path in xwmc_files:
            name = xwmc_path.stem
            parts = name.split('_')
            if len(parts) != 2:
                continue
            tile_x = int(parts[0])
            tile_z = int(parts[1])

            try:
                with zipfile.ZipFile(xwmc_path) as z:
                    raw = z.read('cache.xaero')

                parsed = parse_cache_xaero(raw)
                img = render_tile(parsed, tile_x, tile_z, int(level))

                out_path = level_out / f"{tile_x}_{tile_z}.png"
                img.save(out_path)
                stats['tiles'] += 1
                stats['textures'] += len(parsed['textures'])

                n_tex = len(parsed['textures'])
                print(f"  {name}: {n_tex} textures -> {out_path.name}")

            except Exception as e:
                error_msg = f"{level}/{name}: {e}"
                stats['errors'].append(error_msg)
                print(f"  ERROR {error_msg}")

    print(f"\n=== Summary ===")
    print(f"  Tiles generated: {stats['tiles']}")
    print(f"  Total textures: {stats['textures']}")
    print(f"  Levels: {sorted(stats['levels'])}")
    print(f"  Errors: {len(stats['errors'])}")
    for err in stats['errors'][:10]:
        print(f"    {err}")

    return stats


if __name__ == '__main__':
    process_all_cache_files()
