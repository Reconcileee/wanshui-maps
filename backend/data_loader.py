"""加载演示数据 (JSON)。启动时一次性读入内存，后续路由复用。"""
import json
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TILE_DIR = Path(__file__).resolve().parent.parent / "frontend" / "tiles" / "xaero"


def _load(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache()
def get_dimensions() -> list[dict]:
    """维度元数据: [{id, name, size, max_zoom}]"""
    return _load("dimensions.json")


@lru_cache()
def get_pois() -> list[dict]:
    return _load("pois.json")


@lru_cache()
def get_portals() -> list[dict]:
    return _load("portals.json")


@lru_cache()
def get_players() -> list[dict]:
    return _load("players.json")


@lru_cache()
def get_walkable(dim_id: int) -> dict:
    """返回 {dim, obstacles(set of (x,z))}。真实坐标, 无偏移。"""
    data = _load(f"walkable_{dim_id}.json")
    data["obstacles"] = set(tuple(o) for o in data.get("obstacles", []))
    return data


def get_dim_meta(dim_id: int) -> dict | None:
    for d in get_dimensions():
        if d["id"] == dim_id:
            return d
    return None


def save_pois(pois: list[dict]):
    with open(DATA_DIR / "pois.json", "w", encoding="utf-8") as f:
        json.dump(pois, f, ensure_ascii=False, indent=2)
    get_pois.cache_clear()
