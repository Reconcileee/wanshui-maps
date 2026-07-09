"""A* 路径规划 + 传送门联动。

支持:
- 同维度内 A* 寻路 (4 方向, 避开障碍)
- 跨维度 (主世界↔下界) 经传送门联动, 坐标 1:8 映射
- 多段路径组合, 返回总距离 + 分段信息
"""
import heapq
import math
from fastapi import APIRouter, HTTPException, Query

from .data_loader import get_walkable, get_portals, get_dim_meta

router = APIRouter()

PORTAL_COST = 10  # 传送门固定开销
MAX_EXPLORE = 200_000  # A* 最大探索节点, 防止服务器卡死


def heuristic(x1: int, z1: int, x2: int, z2: int) -> float:
    return math.hypot(x2 - x1, z2 - z1)


def astar(dim_id: int, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]] | None:
    """单维度内 A* 寻路。start/end = (x, z) 真实坐标。返回路径点列表或 None。

    无障碍时直接返回直线插值路径 (避免在 4096+ 规模网格上探索过多节点)。
    """
    data = get_walkable(dim_id)
    obstacles = data["obstacles"]
    sx, sz = start
    ex, ez = end

    if (ex, ez) in obstacles:
        ex, ez = _nearest_walkable(dim_id, ex, ez)
        if ex is None:
            return None

    # 无障碍: 直线插值 (步长 1 block)
    if not obstacles:
        path = []
        dx, dz = ex - sx, ez - sz
        steps = max(abs(dx), abs(dz))
        if steps == 0:
            return [(sx, sz)]
        for i in range(steps + 1):
            t = i / steps
            path.append((round(sx + dx * t), round(sz + dz * t)))
        return path

    # 有障碍: 标准 A*
    open_heap = [(heuristic(sx, sz, ex, ez), 0.0, sx, sz)]
    came_from: dict[tuple, tuple] = {}
    g_score: dict[tuple, float] = {(sx, sz): 0.0}
    closed: set[tuple] = set()
    explored = 0

    while open_heap:
        _, g, x, z = heapq.heappop(open_heap)
        if (x, z) in closed:
            continue
        closed.add((x, z))
        explored += 1
        if explored > MAX_EXPLORE:
            return None
        if (x, z) == (ex, ez):
            path = [(x, z)]
            cur = (x, z)
            while cur in came_from:
                cur = came_from[cur]
                path.append(cur)
            path.reverse()
            return path

        for dx, dz in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, nz = x + dx, z + dz
            if (nx, nz) in closed:
                continue
            if (nx, nz) in obstacles:
                continue
            ng = g + 1.0
            if ng < g_score.get((nx, nz), float("inf")):
                g_score[(nx, nz)] = ng
                came_from[(nx, nz)] = (x, z)
                heapq.heappush(open_heap, (ng + heuristic(nx, nz, ex, ez), ng, nx, nz))
    return None


def _nearest_walkable(dim_id: int, x: int, z: int) -> tuple[int, int] | tuple[None, None]:
    """找最近的可行走点 (螺旋搜索, 半径上限 20)。"""
    data = get_walkable(dim_id)
    obstacles = data["obstacles"]
    for r in range(1, 21):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if max(abs(dx), abs(dz)) != r:
                    continue
                nx, nz = x + dx, z + dz
                if (nx, nz) not in obstacles:
                    return nx, nz
    return None, None


def _path_length(path: list[tuple[int, int]]) -> float:
    """折线总长度 (曼哈顿近似欧氏)。"""
    if len(path) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(path)):
        x1, z1 = path[i - 1]
        x2, z2 = path[i]
        total += math.hypot(x2 - x1, z2 - z1)
    return total


@router.get("/route")
def plan_route(
    from_dim: int = Query(...),
    from_x: int = Query(...),
    from_z: int = Query(...),
    to_dim: int = Query(...),
    to_x: int = Query(...),
    to_z: int = Query(...),
):
    """A* + 传送门联动路径规划。

    返回:
      segments: [{dim, path:[[x,z],...], distance, type:"walk"|"portal"}]
      total_distance: float
      portals_used: [{overworld:{x,z}, nether:{x,z}}]
    """
    start = (from_x, from_z)
    end = (to_x, to_z)

    # 同维度: 直接 A*
    if from_dim == to_dim:
        path = astar(from_dim, start, end)
        if path is None:
            raise HTTPException(404, "无法找到路径 (障碍阻挡或超出范围)")
        return {
            "segments": [{
                "dim": from_dim,
                "path": [[x, z] for x, z in path],
                "distance": _path_length(path),
                "type": "walk",
            }],
            "total_distance": _path_length(path),
            "portals_used": [],
        }

    # 跨维度: 仅支持主世界(0) ↔ 下界(-1)
    pair = {from_dim, to_dim}
    if pair != {0, -1}:
        raise HTTPException(400, "跨维度路径仅支持主世界↔下界 (末地需通过末地传送门, 暂不支持)")

    portals = get_portals()
    best = None  # (total_cost, segments, portals_used)

    for portal in portals:
        # 确定 from 侧和 to 侧的传送门坐标
        if from_dim == 0:
            p_from = (portal["overworld"]["x"], portal["overworld"]["z"])
            p_to = (portal["nether"]["x"], portal["nether"]["z"])
        else:
            p_from = (portal["nether"]["x"], portal["nether"]["z"])
            p_to = (portal["overworld"]["x"], portal["overworld"]["z"])

        # 段1: start → p_from (在 from_dim)
        seg1 = astar(from_dim, start, p_from)
        if seg1 is None:
            continue
        # 段2: p_to → end (在 to_dim)
        seg2 = astar(to_dim, p_to, end)
        if seg2 is None:
            continue

        total = _path_length(seg1) + PORTAL_COST + _path_length(seg2)
        if best is None or total < best[0]:
            best = (
                total,
                [
                    {"dim": from_dim, "path": [[x, z] for x, z in seg1],
                     "distance": _path_length(seg1), "type": "walk"},
                    {"dim": from_dim, "path": [list(p_from), list(p_from)],
                     "distance": 0, "type": "portal_exit"},
                    {"dim": to_dim, "path": [list(p_to), list(p_to)],
                     "distance": 0, "type": "portal_enter"},
                    {"dim": to_dim, "path": [[x, z] for x, z in seg2],
                     "distance": _path_length(seg2), "type": "walk"},
                ],
                [portal],
            )

    if best is None:
        raise HTTPException(404, "无法找到跨维度路径 (传送门不可达或障碍阻挡)")

    return {
        "segments": best[1],
        "total_distance": best[0],
        "portals_used": best[2],
    }


@router.get("/portals")
def list_portals():
    return get_portals()


@router.get("/walkable/{dim}")
def walkable_info(dim: int):
    """返回可行走性元数据 (obstacles 数量)。"""
    data = get_walkable(dim)
    meta = get_dim_meta(dim)
    return {"dim": dim, "obstacle_count": len(data["obstacles"]), "max_zoom": meta["max_zoom"] if meta else None}
