"""从真实 Minecraft 存档生成地图瓦片 + 解析 Xaero Waypoints 作为 POI。

数据源:
  - region/*.mca → 生物群系 → 颜色 → 瓦片金字塔
  - XaeroWaypoints/*/dim%0/*.txt → POI 地点

运行: python scripts/gen_real_data.py
输出到 data/ 目录。
"""
import io
import json
import zlib
import struct
from pathlib import Path

from PIL import Image
from nbtlib import File

# ---------- 配置 ----------
PROJECT = Path(__file__).resolve().parent.parent
SAVE_DIR = PROJECT / "1.19.2TOBU0405"
WORLD_DIR = SAVE_DIR / "saves" / "新的世界"
WAYPOINTS_DIR = SAVE_DIR / "XaeroWaypoints"
DATA_DIR = PROJECT / "data"
TILE_DIR = DATA_DIR / "xaeroworldmap" / "DemoWorld"
TILE_SIZE = 256

# Minecraft 1.19.2 biome ID → 颜色 (RGB)
# 参考: https://minecraft.fandom.com/wiki/Biome/ID
BIOME_COLORS = {
    # 海洋类
    0: (0, 0, 130),      # 海洋
    1: (0, 0, 170),      # 平原
    2: (0, 0, 200),      # 沙漠
    3: (60, 100, 180),   # 山脉
    4: (40, 80, 160),    # 森林
    5: (0, 120, 100),    # 深海
    6: (120, 200, 100),  # 沼泽
    7: (140, 180, 100),  # 河流
    8: (200, 180, 80),   # 下界荒地 → 沙漠色
    9: (100, 40, 40),    # 末地
    # 1.13+ 海洋变种
    10: (0, 0, 140),     # 冻洋
    11: (100, 160, 200), # 冻河
    12: (255, 255, 255), # 冰原
    13: (200, 220, 255), # 冰刺平原
    14: (50, 70, 180),   # 冷海
    15: (40, 60, 160),   # 深冷海
    16: (60, 150, 220),  # 温海
    17: (40, 110, 200),  # 深温海
    18: (80, 160, 120),  # 温海 (变种)
    19: (50, 130, 180),  # 深温海 (变种)
    # 1.14+
    21: (80, 140, 180),  # 海洋丛林
    22: (100, 160, 100), # 丛林边缘
    23: (60, 130, 90),   # 丛林
    24: (150, 180, 100), # 竹林
    25: (100, 140, 80),  # 竹林丘陵
    26: (50, 120, 200),  # 河流变种
    27: (200, 200, 150), # 沙漠变种
    28: (50, 100, 70),   # 森林变种
    29: (40, 90, 60),    # 深林
    30: (60, 120, 80),   # 深林变种
    31: (130, 170, 100), # 草原
    32: (120, 160, 90),  # 草原变种
    33: (90, 140, 70),   # 草原丘陵
    34: (180, 160, 80),  # 沙漠丘陵
    35: (180, 160, 100), # 沙漠湖泊
    36: (40, 80, 50),    # 森林丘陵
    37: (30, 70, 40),    # 深林丘陵
    38: (60, 100, 70),   # 沼泽丘陵
    39: (0, 0, 120),     # 海洋变种
    40: (50, 90, 140),   # 深海变种
    41: (100, 140, 180), # 河流变种
    42: (50, 80, 120),   # 深海暖
    43: (40, 70, 100),   # 深冷海变种
    44: (60, 100, 140),  # 深温海变种
    45: (40, 80, 100),   # 深暖海
    46: (255, 200, 200), # 积雪山
    47: (200, 180, 180), # 积雪山变种
    48: (200, 160, 160), # 积雪丘陵
    49: (180, 140, 140), # 积雪林
    50: (150, 120, 120), # 积雪河
    # 1.15+
    51: (100, 180, 180), # 末地荒地
    52: (80, 160, 160),  # 末地高地
    53: (120, 200, 200), # 末地空岛
    54: (0, 0, 0),       # 虚空
    # 1.16+ 下界
    55: (100, 50, 50),   # 灵魂沙谷
    56: (120, 60, 60),   # 绯红森林
    57: (80, 40, 40),    # 诡异森林
    58: (90, 50, 50),    # 下界荒地 (变种)
    59: (110, 55, 55),   # 玄武岩三角洲
    # 1.17+
    60: (200, 220, 220), # 洞穴
    61: (180, 200, 200), # 繁茂洞穴
    62: (90, 140, 60),   # 苔藓洞穴
    63: (70, 120, 50),   # 深板岩
    64: (160, 180, 180), # 滴水石
    # 1.18+
    65: (100, 150, 80),  # 草甸
    66: (80, 130, 70),   # 树林
    67: (60, 110, 60),   # 雪林
    68: (70, 120, 80),   # 尖峰
    69: (50, 100, 50),   # 冰冻峰
    70: (80, 100, 60),   # 石峰
    71: (120, 140, 80),  # 河流
    72: (100, 120, 70),  # 冻河
    # 默认
    127: (128, 128, 128),
}

DEFAULT_COLOR = (128, 128, 128)


def get_biome_color(biome_id):
    """生物群系 ID → 颜色, 带高度阴影。"""
    return BIOME_COLORS.get(biome_id, DEFAULT_COLOR)


def read_region_chunk(mca_path, cx, cz):
    """从 .mca 文件读取指定 chunk (cx, cz 为 region 内坐标 0-31) 的 NBT 数据。"""
    with open(mca_path, "rb") as f:
        # location table: 1024 字节, 每 4 字节一个 chunk
        offset = (cx + cz * 32) * 4
        f.seek(offset)
        loc = f.read(4)
        if len(loc) < 4:
            return None
        chunk_offset = (loc[0] << 16 | loc[1] << 8 | loc[2]) * 4096
        chunk_sectors = loc[3]
        if chunk_offset == 0 or chunk_sectors == 0:
            return None  # chunk 不存在

        f.seek(chunk_offset)
        length_bytes = f.read(4)
        if len(length_bytes) < 4:
            return None
        length = struct.unpack(">I", length_bytes)[0]
        comp_byte = f.read(1)
        if len(comp_byte) < 1:
            return None
        compression = comp_byte[0]
        raw = f.read(length - 1)
        if len(raw) < length - 1:
            return None

        try:
            if compression == 2:  # zlib
                data = zlib.decompress(raw)
            elif compression == 1:  # gzip
                import gzip
                data = gzip.decompress(raw)
            else:
                return None
            return File.parse(io.BytesIO(data))
        except Exception:
            return None


def extract_chunk_biomes(nbt_data):
    """从 chunk NBT 提取顶层生物群系 (16x16 网格)。

    1.18+: chunk 有 sections 数组, biomes 存在每个 section 的 palette 中。
    返回: 16x16 的 biome_id 网格 (顶层)
    """
    if nbt_data is None:
        return None

    try:
        root = nbt_data
        sections = root["sections"]
        # 找到最高的非空 section
        top_section = None
        for sec in sorted(sections, key=lambda s: int(s["Y"]), reverse=True):
            if "biomes" in sec:
                top_section = sec
                break

        if top_section is None:
            return None

        biomes = top_section["biomes"]
        palette = list(biomes["palette"])
        # biomes["data"] 是 int array, 每 4 个 bit 代表一个 biome index (1.18+)
        # 但如果是单 biome, data 可能不存在
        if "data" not in biomes:
            # 单一 biome, 整个 section 都是 palette[0]
            biome_id = parse_biome_id(palette[0])
            return [[biome_id] * 16 for _ in range(16)]

        data = list(biomes["data"])
        # 1.18+: biomes 用 4x4x4 的 sub-chunk, 每个 section 有 4*4*4=64 个 biome
        # 但渲染时我们只需要顶层 4x4=16 个 biome (每个 4x4 blocks)
        # 实际上 1.18+ biomes 是 4x4x4, 顶层是 y=48~63 (在 section 内)
        # 对于俯视图, 我们取 section 内最上面的 4x4 biome 层
        bits = max(4, (len(palette) - 1).bit_length())
        grid = [[0] * 16 for _ in range(16)]

        # biome data 顺序: x, z, y (每个 4x4x4)
        # 对于顶层 (y=3 within section), 取 index = x*16 + z*4 + 3
        for bx in range(4):
            for bz in range(4):
                idx = bx * 16 + bz * 4 + 3  # 顶层
                if idx < len(data) * (64 // bits):
                    # 提取 biome index
                    long_idx = idx * bits // 64
                    bit_offset = idx * bits % 64
                    if long_idx < len(data):
                        val = data[long_idx]
                        # 处理 long 的符号位
                        if val < 0:
                            val += (1 << 64)
                        mask = (1 << bits) - 1
                        biome_idx = (val >> bit_offset) & mask
                        if biome_idx < len(palette):
                            biome_id = parse_biome_id(palette[biome_idx])
                            # 填充 4x4 block 区域
                            for dx in range(4):
                                for dz in range(4):
                                    grid[bx * 4 + dx][bz * 4 + dz] = biome_id
        return grid
    except Exception as e:
        return None


def parse_biome_id(biome_str):
    """从 biome 字符串 (如 'minecraft:plains') 解析 ID。
    由于 1.18+ 使用字符串 ID, 我们需要映射表。"""
    # 简化: 用字符串 hash 映射到颜色 (后续可优化)
    BIOME_STR_COLORS = {
        "minecraft:plains": (120, 180, 100),
        "minecraft:desert": (220, 200, 140),
        "minecraft:forest": (76, 124, 76),
        "minecraft:birch_forest": (90, 140, 80),
        "minecraft:dark_forest": (50, 90, 50),
        "minecraft:swamp": (100, 140, 90),
        "minecraft:jungle": (60, 130, 90),
        "minecraft:savanna": (180, 170, 90),
        "minecraft:taiga": (70, 110, 90),
        "minecraft:snowy_plains": (220, 230, 240),
        "minecraft:snowy_taiga": (180, 200, 220),
        "minecraft:ice_spikes": (200, 220, 255),
        "minecraft:beach": (220, 210, 160),
        "minecraft:snowy_beach": (230, 230, 240),
        "minecraft:river": (80, 140, 180),
        "minecraft:frozen_river": (120, 160, 200),
        "minecraft:ocean": (40, 80, 160),
        "minecraft:cold_ocean": (50, 90, 170),
        "minecraft:deep_ocean": (30, 60, 140),
        "minecraft:deep_cold_ocean": (40, 70, 150),
        "minecraft:deep_frozen_ocean": (50, 80, 160),
        "minecraft:warm_ocean": (60, 130, 200),
        "minecraft:deep_warm_ocean": (50, 110, 180),
        "minecraft:lukewarm_ocean": (60, 120, 190),
        "minecraft:deep_lukewarm_ocean": (50, 100, 170),
        "minecraft:mountains": (130, 130, 130),
        "minecraft:wooded_mountains": (100, 110, 100),
        "minecraft:gravelly_mountains": (120, 115, 110),
        "minecraft:mountain_edge": (140, 140, 130),
        "minecraft:stone_shore": (120, 120, 120),
        "minecraft:mushroom_fields": (180, 140, 140),
        "minecraft:flower_forest": (100, 150, 90),
        "minecraft:sunflower_plains": (130, 190, 110),
        "minecraft:lake": (60, 120, 180),
        # 1.14+
        "minecraft:bamboo_jungle": (100, 150, 80),
        "minecraft:dark_forest_hills": (60, 100, 60),
        "minecraft:desert_hills": (200, 180, 120),
        "minecraft:desert_lakes": (210, 190, 130),
        "minecraft:birch_forest_hills": (100, 150, 90),
        "minecraft:tall_birch_forest": (95, 145, 85),
        "minecraft:tall_birch_hills": (105, 155, 95),
        "minecraft:forest_hills": (60, 110, 70),
        "minecraft:jungle_hills": (70, 140, 100),
        "minecraft:modified_jungle": (65, 135, 95),
        "minecraft:jungle_edge": (90, 160, 110),
        "minecraft:modified_jungle_edge": (95, 165, 115),
        "minecraft:savanna_plateau": (190, 180, 100),
        "minecraft:shattered_savanna": (170, 160, 90),
        "minecraft:shattered_savanna_plateau": (180, 170, 95),
        "minecraft:swamp_hills": (110, 150, 100),
        "minecraft:taiga_hills": (80, 120, 100),
        "minecraft:taiga_mountains": (90, 130, 110),
        "minecraft:snowy_taiga_hills": (190, 210, 230),
        "minecraft:snowy_taiga_mountains": (200, 220, 240),
        "minecraft:giant_tree_taiga": (80, 120, 80),
        "minecraft:giant_tree_taiga_hills": (90, 130, 90),
        "minecraft:modified_gravelly_mountains": (125, 120, 115),
        "minecraft:wooded_badlands_plateau": (150, 120, 70),
        "minecraft:badlands_plateau": (160, 130, 80),
        "minecraft:badlands": (170, 140, 90),
        "minecraft:eroded_badlands": (180, 150, 100),
        "minecraft:modified_badlands_plateau": (165, 135, 85),
        "minecraft:modified_wooded_badlands_plateau": (155, 125, 75),
        # 1.18+
        "minecraft:meadow": (130, 170, 90),
        "minecraft:grove": (90, 130, 80),
        "minecraft:snowy_slopes": (200, 210, 220),
        "minecraft:jagged_peaks": (180, 180, 190),
        "minecraft:frozen_peaks": (210, 220, 230),
        "minecraft:stony_peaks": (160, 160, 160),
        "minecraft:stony_shore": (130, 130, 130),
        "minecraft:windswept_hills": (140, 140, 130),
        "minecraft:windswept_forest": (100, 120, 90),
        "minecraft:windswept_gravelly_hills": (130, 125, 120),
        "minecraft:windswept_savanna": (170, 160, 90),
        "minecraft:old_growth_pine_taiga": (80, 120, 80),
        "minecraft:old_growth_spruce_taiga": (85, 125, 85),
        "minecraft:snowy_beach": (230, 230, 240),
        # 1.19+
        "minecraft:mangrove_swamp": (90, 130, 80),
        # 洞穴
        "minecraft:lush_caves": (90, 140, 60),
        "minecraft:dripstone_caves": (160, 140, 120),
        "minecraft:deep_dark": (30, 30, 40),
        # 下界
        "minecraft:nether_wastes": (110, 40, 40),
        "minecraft:soul_sand_valley": (90, 70, 50),
        "minecraft:crimson_forest": (120, 60, 60),
        "minecraft:warped_forest": (60, 80, 90),
        "minecraft:basalt_deltas": (80, 50, 50),
        # 末地
        "minecraft:the_end": (220, 215, 180),
        "minecraft:end_barrens": (200, 195, 160),
        "minecraft:end_highlands": (230, 225, 190),
        "minecraft:end_midlands": (210, 205, 170),
        "minecraft:small_end_islands": (190, 185, 150),
        "minecraft:void": (20, 20, 20),
    }
    return None  # 返回 None, 使用字符串映射


def get_biome_color_str(biome_str):
    """从 biome 字符串获取颜色。"""
    BIOME_STR_COLORS = {
        "minecraft:plains": (120, 180, 100),
        "minecraft:desert": (220, 200, 140),
        "minecraft:forest": (76, 124, 76),
        "minecraft:birch_forest": (90, 140, 80),
        "minecraft:dark_forest": (50, 90, 50),
        "minecraft:swamp": (100, 140, 90),
        "minecraft:jungle": (60, 130, 90),
        "minecraft:savanna": (180, 170, 90),
        "minecraft:taiga": (70, 110, 90),
        "minecraft:snowy_plains": (220, 230, 240),
        "minecraft:snowy_taiga": (180, 200, 220),
        "minecraft:ice_spikes": (200, 220, 255),
        "minecraft:beach": (220, 210, 160),
        "minecraft:snowy_beach": (230, 230, 240),
        "minecraft:river": (80, 140, 180),
        "minecraft:frozen_river": (120, 160, 200),
        "minecraft:ocean": (40, 80, 160),
        "minecraft:cold_ocean": (50, 90, 170),
        "minecraft:deep_ocean": (30, 60, 140),
        "minecraft:deep_cold_ocean": (40, 70, 150),
        "minecraft:deep_frozen_ocean": (50, 80, 160),
        "minecraft:warm_ocean": (60, 130, 200),
        "minecraft:deep_warm_ocean": (50, 110, 180),
        "minecraft:lukewarm_ocean": (60, 120, 190),
        "minecraft:deep_lukewarm_ocean": (50, 100, 170),
        "minecraft:mountains": (130, 130, 130),
        "minecraft:wooded_mountains": (100, 110, 100),
        "minecraft:gravelly_mountains": (120, 115, 110),
        "minecraft:mountain_edge": (140, 140, 130),
        "minecraft:stone_shore": (120, 120, 120),
        "minecraft:mushroom_fields": (180, 140, 140),
        "minecraft:flower_forest": (100, 150, 90),
        "minecraft:sunflower_plains": (130, 190, 110),
        "minecraft:lake": (60, 120, 180),
        "minecraft:bamboo_jungle": (100, 150, 80),
        "minecraft:dark_forest_hills": (60, 100, 60),
        "minecraft:desert_hills": (200, 180, 120),
        "minecraft:desert_lakes": (210, 190, 130),
        "minecraft:birch_forest_hills": (100, 150, 90),
        "minecraft:tall_birch_forest": (95, 145, 85),
        "minecraft:tall_birch_hills": (105, 155, 95),
        "minecraft:forest_hills": (60, 110, 70),
        "minecraft:jungle_hills": (70, 140, 100),
        "minecraft:modified_jungle": (65, 135, 95),
        "minecraft:jungle_edge": (90, 160, 110),
        "minecraft:modified_jungle_edge": (95, 165, 115),
        "minecraft:savanna_plateau": (190, 180, 100),
        "minecraft:shattered_savanna": (170, 160, 90),
        "minecraft:shattered_savanna_plateau": (180, 170, 95),
        "minecraft:swamp_hills": (110, 150, 100),
        "minecraft:taiga_hills": (80, 120, 100),
        "minecraft:taiga_mountains": (90, 130, 110),
        "minecraft:snowy_taiga_hills": (190, 210, 230),
        "minecraft:snowy_taiga_mountains": (200, 220, 240),
        "minecraft:giant_tree_taiga": (80, 120, 80),
        "minecraft:giant_tree_taiga_hills": (90, 130, 90),
        "minecraft:modified_gravelly_mountains": (125, 120, 115),
        "minecraft:wooded_badlands_plateau": (150, 120, 70),
        "minecraft:badlands_plateau": (160, 130, 80),
        "minecraft:badlands": (170, 140, 90),
        "minecraft:eroded_badlands": (180, 150, 100),
        "minecraft:modified_badlands_plateau": (165, 135, 85),
        "minecraft:modified_wooded_badlands_plateau": (155, 125, 75),
        "minecraft:meadow": (130, 170, 90),
        "minecraft:grove": (90, 130, 80),
        "minecraft:snowy_slopes": (200, 210, 220),
        "minecraft:jagged_peaks": (180, 180, 190),
        "minecraft:frozen_peaks": (210, 220, 230),
        "minecraft:stony_peaks": (160, 160, 160),
        "minecraft:stony_shore": (130, 130, 130),
        "minecraft:windswept_hills": (140, 140, 130),
        "minecraft:windswept_forest": (100, 120, 90),
        "minecraft:windswept_gravelly_hills": (130, 125, 120),
        "minecraft:windswept_savanna": (170, 160, 90),
        "minecraft:old_growth_pine_taiga": (80, 120, 80),
        "minecraft:old_growth_spruce_taiga": (85, 125, 85),
        "minecraft:snowy_beach": (230, 230, 240),
        "minecraft:mangrove_swamp": (90, 130, 80),
        "minecraft:lush_caves": (90, 140, 60),
        "minecraft:dripstone_caves": (160, 140, 120),
        "minecraft:deep_dark": (30, 30, 40),
        "minecraft:nether_wastes": (110, 40, 40),
        "minecraft:soul_sand_valley": (90, 70, 50),
        "minecraft:crimson_forest": (120, 60, 60),
        "minecraft:warped_forest": (60, 80, 90),
        "minecraft:basalt_deltas": (80, 50, 50),
        "minecraft:the_end": (220, 215, 180),
        "minecraft:end_barrens": (200, 195, 160),
        "minecraft:end_highlands": (230, 225, 190),
        "minecraft:end_midlands": (210, 205, 170),
        "minecraft:small_end_islands": (190, 185, 150),
        "minecraft:void": (20, 20, 20),
    }
    return BIOME_STR_COLORS.get(biome_str, DEFAULT_COLOR)


def extract_chunk_top_biomes(nbt_data):
    """从 chunk NBT 提取顶层生物群系 (16x16), 使用字符串 ID。"""
    if nbt_data is None:
        return None

    try:
        root = nbt_data
        sections = root["sections"]
        # 找到最高的非空 section
        top_section = None
        for sec in sorted(sections, key=lambda s: int(s["Y"]), reverse=True):
            if "biomes" in sec:
                top_section = sec
                break

        if top_section is None:
            return None

        biomes = top_section["biomes"]
        palette = [str(p) for p in biomes["palette"]]

        if "data" not in biomes:
            # 单一 biome
            color = get_biome_color_str(palette[0])
            return [[color] * 16 for _ in range(16)]

        data = list(biomes["data"])
        bits = max(4, (len(palette) - 1).bit_length())
        grid = [[DEFAULT_COLOR] * 16 for _ in range(16)]

        for bx in range(4):
            for bz in range(4):
                idx = bx * 16 + bz * 4 + 3  # 顶层
                long_idx = idx * bits // 64
                bit_offset = idx * bits % 64
                if long_idx < len(data):
                    val = int(data[long_idx])
                    if val < 0:
                        val += (1 << 64)
                    mask = (1 << bits) - 1
                    biome_idx = (val >> bit_offset) & mask
                    if biome_idx < len(palette):
                        color = get_biome_color_str(palette[biome_idx])
                        for dx in range(4):
                            for dz in range(4):
                                grid[bx * 4 + dx][bz * 4 + dz] = color
        return grid
    except Exception:
        return None


def extract_heightmap(nbt_data):
    """从 chunk NBT 提取 MOTION_BLOCKING 高度图 (16x16)。"""
    if nbt_data is None:
        return None
    try:
        root = nbt_data
        heightmaps = root["Heightmaps"]
        if "MOTION_BLOCKING" in heightmaps:
            data = list(heightmaps["MOTION_BLOCKING"])
            # 高度图是 16x16, 每个 9 bit
            heights = [[0] * 16 for _ in range(16)]
            for i in range(256):
                long_idx = i * 9 // 64
                bit_offset = i * 9 % 64
                if long_idx < len(data):
                    val = int(data[long_idx])
                    if val < 0:
                        val += (1 << 64)
                    h = (val >> bit_offset) & 0x1FF
                    # x = i % 16, z = i // 16
                    heights[i % 16][i // 16] = h
            return heights
    except Exception:
        pass
    return None


def render_region(mca_path, rx, rz):
    """渲染一个 region (512x512) 为 PIL Image。"""
    img = Image.new("RGB", (512, 512), (30, 30, 40))
    px = img.load()

    has_data = False
    for cx in range(32):
        for cz in range(32):
            nbt = read_region_chunk(mca_path, cx, cz)
            if nbt is None:
                continue
            has_data = True
            biomes = extract_chunk_top_biomes(nbt)
            heights = extract_heightmap(nbt)
            if biomes is None:
                continue

            for bx in range(16):
                for bz in range(16):
                    color = biomes[bx][bz]
                    # 高度阴影
                    if heights and bx < 15 and bz < 15:
                        h = heights[bx][bz]
                        h_e = heights[bx + 1][bz] if heights else h
                        shade = 1.0 + (h - h_e) * 0.015
                        shade = max(0.5, min(1.5, shade))
                        color = tuple(int(c * shade) for c in color)

                    # 像素位置: region 内 (rx*512 + cx*16 + bx, rz*512 + cz*16 + bz)
                    px_x = cx * 16 + bx
                    px_z = cz * 16 + bz
                    if 0 <= px_x < 512 and 0 <= px_z < 512:
                        px[px_x, px_z] = color

    return img if has_data else None


def slice_tiles(img, dim_id, origin_x, origin_z, world_size, max_zoom, tile_dir):
    """将 region 图像贴到世界大图上, 并切片瓦片。"""
    # 这里我们采用: 先把所有 region 拼成大图, 再切片
    # 但大图可能很大 (4608x3584), 需要分块处理
    # 简化: 直接在大图上对应区域贴入
    pass


def render_world(dim_id, dim_name, region_dir, world_origin_x, world_origin_z, world_size, max_zoom):
    """渲染整个维度的地形图并切片瓦片。"""
    print(f"渲染 {dim_name} (world_size={world_size}, max_zoom={max_zoom})...")

    # 创建世界大图
    world_img = Image.new("RGB", (world_size, world_size), (30, 30, 40))
    px = world_img.load()

    # 遍历所有 region 文件
    region_files = sorted(region_dir.glob("r.*.mca"))
    print(f"  找到 {len(region_files)} 个 region 文件")

    for i, mca in enumerate(region_files):
        parts = mca.stem.split(".")
        rx, rz = int(parts[1]), int(parts[2])
        # 世界坐标: rx*512 到 (rx+1)*512
        # 转换到大图坐标: 减去 world_origin
        img_x = rx * 512 - world_origin_x
        img_z = rz * 512 - world_origin_z

        # 跳过超出范围的 region
        if img_x + 512 <= 0 or img_x >= world_size or img_z + 512 <= 0 or img_z >= world_size:
            continue

        print(f"  [{i+1}/{len(region_files)}] region ({rx},{rz}) → 图坐标 ({img_x},{img_z})")
        region_img = render_region(mca, rx, rz)
        if region_img is None:
            print(f"    跳过 (无数据)")
            continue

        # 批量贴到世界大图 (处理边界裁剪)
        if img_x < 0 or img_z < 0 or img_x + 512 > world_size or img_z + 512 > world_size:
            # 部分超出, 裁剪后贴入
            src_box = (max(0, -img_x), max(0, -img_z),
                       min(512, world_size - img_x), min(512, world_size - img_z))
            dst_x = max(0, img_x)
            dst_z = max(0, img_z)
            crop = region_img.crop(src_box)
            world_img.paste(crop, (dst_x, dst_z))
        else:
            world_img.paste(region_img, (img_x, img_z))

    # 切片瓦片金字塔 (TMS y-flipped)
    out = TILE_DIR / f"tile_{dim_id}"
    out.mkdir(parents=True, exist_ok=True)

    for z in range(max_zoom + 1):
        tiles_per_side = 2 ** z
        full_px = tiles_per_side * TILE_SIZE
        scaled = world_img.resize((full_px, full_px), Image.NEAREST)
        zdir = out / str(z)
        zdir.mkdir(exist_ok=True)
        for tx in range(tiles_per_side):
            xdir = zdir / str(tx)
            xdir.mkdir(exist_ok=True)
            for ty in range(tiles_per_side):
                tms_y = tiles_per_side - 1 - ty
                box = (tx * TILE_SIZE, tms_y * TILE_SIZE,
                       (tx + 1) * TILE_SIZE, (tms_y + 1) * TILE_SIZE)
                tile = scaled.crop(box)
                tile.save(xdir / f"{ty}.png")

    # 保存完整图 (调试)
    world_img.save(DATA_DIR / f"terrain_{dim_id}.png")
    print(f"  {dim_name} 完成")


def parse_waypoints():
    """解析 Xaero Waypoints 文件, 返回 POI 列表。"""
    pois = []
    poi_id = 0

    # 遍历所有多人游戏服务器目录
    for server_dir in sorted(WAYPOINTS_DIR.iterdir()):
        if not server_dir.is_dir() or not server_dir.name.startswith("Multiplayer_"):
            continue
        server_name = server_dir.name.replace("Multiplayer_", "")

        # 遍历维度目录 (dim%0 = 主世界, dim%-1 = 下界, dim%1 = 末地)
        for dim_dir in sorted(server_dir.iterdir()):
            if not dim_dir.is_dir() or not dim_dir.name.startswith("dim%"):
                continue
            dim_id = int(dim_dir.name.replace("dim%", ""))

            # 遍历 waypoint 文件
            for wp_file in sorted(dim_dir.glob("*.txt")):
                with open(wp_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line.startswith("waypoint:"):
                            continue
                        parts = line.split(":")
                        if len(parts) < 7:
                            continue
                        name = parts[1]
                        x = int(parts[3])
                        y = int(parts[4])
                        z = int(parts[5])
                        wp_type = int(parts[8]) if len(parts) > 8 else 0

                        # 跳过死亡点 (type=2)
                        if wp_type == 2:
                            continue
                        # 跳过 xaero 内部 waypoint
                        if name.startswith("gui.xaero"):
                            continue

                        # 分类: 根据名称关键词
                        category = "landmark"
                        name_lower = name.lower()
                        if any(k in name for k in ["矿", "资源", "宝箱", "钻石", "铁", "金"]):
                            category = "resource"
                        elif any(k in name for k in ["传送门", "portal", "门"]):
                            category = "portal"

                        pois.append({
                            "id": f"poi_{poi_id}",
                            "name": name,
                            "dim": dim_id,
                            "x": x,
                            "z": z,
                            "y": y,
                            "category": category,
                            "icon": "flag",
                            "desc": f"{server_name}",
                        })
                        poi_id += 1

    # 去重 (同名同坐标)
    seen = set()
    unique_pois = []
    for p in pois:
        key = (p["name"], p["x"], p["z"])
        if key not in seen:
            seen.add(key)
            unique_pois.append(p)

    print(f"解析到 {len(unique_pois)} 个唯一 waypoints (从 {len(pois)} 个中)")
    return unique_pois


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {DATA_DIR}")

    # 1. 渲染主世界地形 (从 .mca)
    overworld_region = WORLD_DIR / "region"
    if overworld_region.exists():
        # 计算世界范围: region x: -5~3, z: -3~3
        # 世界坐标: x: -2560 ~ 2048, z: -1536 ~ 2048
        # 为了正坐标, 偏移使最小值为 0
        world_origin_x = -2560
        world_origin_z = -1536
        world_size_x = (3 + 1) * 512 + abs(world_origin_x)  # = 2048 + 2560 = 4608
        world_size_z = (3 + 1) * 512 + abs(world_origin_z)  # = 2048 + 1536 = 3584
        # 取正方形 (较大值), 2 的幂
        world_size = 4096  # 2^12, 足够大
        max_zoom = 4  # 2^4 = 16 tiles per side at max zoom

        render_world(0, "主世界", overworld_region, world_origin_x, world_origin_z, world_size, max_zoom)
    else:
        print("警告: 找不到主世界 region 目录")

    # 2. 下界 (DIM-1)
    nether_region = WORLD_DIR / "DIM-1" / "region"
    if nether_region.exists() and any(nether_region.glob("*.mca")):
        # 下界坐标是主世界的 1/8
        world_size = 1024
        max_zoom = 2
        render_world(-1, "下界", nether_region, 0, 0, world_size, max_zoom)
    else:
        print("下界无 region 数据, 使用空地图")
        # 生成空地图
        img = Image.new("RGB", (1024, 1024), (60, 20, 20))
        img.save(DATA_DIR / "terrain_-1.png")
        out = TILE_DIR / "tile_-1"
        out.mkdir(parents=True, exist_ok=True)
        for z in range(3):
            zdir = out / str(z)
            zdir.mkdir(exist_ok=True)
            tiles_per_side = 2 ** z
            full_px = tiles_per_side * TILE_SIZE
            scaled = img.resize((full_px, full_px), Image.NEAREST)
            for tx in range(tiles_per_side):
                xdir = zdir / str(tx)
                xdir.mkdir(exist_ok=True)
                for ty in range(tiles_per_side):
                    tms_y = tiles_per_side - 1 - ty
                    tile = scaled.crop((tx * TILE_SIZE, tms_y * TILE_SIZE,
                                        (tx + 1) * TILE_SIZE, (tms_y + 1) * TILE_SIZE))
                    tile.save(xdir / f"{ty}.png")

    # 3. 末地 (DIM1)
    end_region = WORLD_DIR / "DIM1" / "region"
    if end_region.exists() and any(end_region.glob("*.mca")):
        world_size = 1024
        max_zoom = 2
        render_world(1, "末地", end_region, 0, 0, world_size, max_zoom)
    else:
        print("末地无 region 数据, 使用空地图")
        img = Image.new("RGB", (1024, 1024), (20, 20, 20))
        img.save(DATA_DIR / "terrain_1.png")
        out = TILE_DIR / "tile_1"
        out.mkdir(parents=True, exist_ok=True)
        for z in range(3):
            zdir = out / str(z)
            zdir.mkdir(exist_ok=True)
            tiles_per_side = 2 ** z
            full_px = tiles_per_side * TILE_SIZE
            scaled = img.resize((full_px, full_px), Image.NEAREST)
            for tx in range(tiles_per_side):
                xdir = zdir / str(tx)
                xdir.mkdir(exist_ok=True)
                for ty in range(tiles_per_side):
                    tms_y = tiles_per_side - 1 - ty
                    tile = scaled.crop((tx * TILE_SIZE, tms_y * TILE_SIZE,
                                        (tx + 1) * TILE_SIZE, (tms_y + 1) * TILE_SIZE))
                    tile.save(xdir / f"{ty}.png")

    # 4. 解析 waypoints
    print("\n解析 waypoints...")
    pois = parse_waypoints()
    (DATA_DIR / "pois.json").write_text(json.dumps(pois, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5. 生成维度元数据 (含 origin: 瓦片图坐标原点对应的真实 MC 坐标)
    dimensions = [
        {"id": 0, "name": "主世界", "size": 4096, "max_zoom": 4, "origin_x": -2560, "origin_z": -1536},
        {"id": -1, "name": "下界", "size": 1024, "max_zoom": 2, "origin_x": 0, "origin_z": 0},
        {"id": 1, "name": "末地", "size": 1024, "max_zoom": 2, "origin_x": 0, "origin_z": 0},
    ]
    (DATA_DIR / "dimensions.json").write_text(json.dumps(dimensions, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6. 生成占位玩家和传送门数据
    players = [
        {"id": "p1", "name": "Steve", "dim": 0, "x": 0, "z": 0, "yaw": 0, "world": "新的世界"},
    ]
    (DATA_DIR / "players.json").write_text(json.dumps(players, ensure_ascii=False, indent=2), encoding="utf-8")

    portals = []
    (DATA_DIR / "portals.json").write_text(json.dumps(portals, ensure_ascii=False, indent=2), encoding="utf-8")

    # 7. 生成 walkable 数据 (稀疏 obstacles 表示; 真实坐标, 无偏移)
    for dim in dimensions:
        w = {"dim": dim["id"], "obstacles": []}
        (DATA_DIR / f"walkable_{dim['id']}.json").write_text(json.dumps(w), encoding="utf-8")

    print("\n完成!")


if __name__ == "__main__":
    main()
