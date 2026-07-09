"""POI 增删改查 + 搜索。"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .data_loader import get_pois, save_pois

router = APIRouter()


class POI(BaseModel):
    name: str
    dim: int
    x: int
    z: int
    category: str = "landmark"
    icon: str = "flag"
    desc: str = ""


@router.get("/pois")
def list_pois(dim: int | None = None, category: str | None = None):
    """列出 POI，可按维度/类别筛选。"""
    pois = get_pois()
    if dim is not None:
        pois = [p for p in pois if p["dim"] == dim]
    if category:
        pois = [p for p in pois if p["category"] == category]
    return pois


@router.get("/pois/{poi_id}")
def get_poi(poi_id: str):
    for p in get_pois():
        if p["id"] == poi_id:
            return p
    raise HTTPException(404, f"POI 不存在: {poi_id}")


@router.post("/pois")
def add_poi(poi: POI):
    pois = get_pois()
    new_id = f"poi_{len(pois) + 1}"
    new_poi = {"id": new_id, **poi.model_dump()}
    pois.append(new_poi)
    save_pois(pois)
    return new_poi


@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    """按名称/描述/坐标搜索 POI。

    支持文本匹配和 "x,z" 坐标跳转。
    """
    pois = get_pois()
    # 坐标解析: "512,512" 或 "x=512,z=512"
    q_stripped = q.strip()
    try:
        parts = q_stripped.replace("x=", "").replace("z=", "").split(",")
        if len(parts) == 2:
            x, z = int(parts[0].strip()), int(parts[1].strip())
            return {
                "type": "coordinate",
                "x": x,
                "z": z,
                "dim": 0,  # 默认主世界
                "pois_nearby": [
                    p for p in pois
                    if abs(p["x"] - x) < 100 and abs(p["z"] - z) < 100
                ][:5],
            }
    except (ValueError, IndexError):
        pass

    # 文本搜索
    q_lower = q.lower()
    matched = [
        p for p in pois
        if q_lower in p["name"].lower() or q_lower in p.get("desc", "").lower()
    ]
    return {"type": "poi", "results": matched}


@router.get("/categories")
def categories():
    """返回所有 POI 类别及计数。"""
    pois = get_pois()
    cats: dict[str, int] = {}
    for p in pois:
        cats[p["category"]] = cats.get(p["category"], 0) + 1
    return [{"category": k, "count": v} for k, v in cats.items()]
