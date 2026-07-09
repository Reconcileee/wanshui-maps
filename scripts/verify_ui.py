"""端到端 UI 验证: 截图 + 检查关键元素。"""
from playwright.sync_api import sync_playwright
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:8000/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})

    # 收集 console 错误
    errors = []
    page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)

    print("1. 打开页面...")
    page.goto(URL, wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(1500)  # 等瓦片渲染

    # 检查关键元素
    print("2. 检查关键 DOM 元素...")
    checks = {
        "map 容器": "#map",
        "搜索框": "#search-input",
        "维度下拉": "#dim-select",
        "维度列表": "#dim-list",
        "POI 列表": "#poi-list",
        "坐标显示": "#coord-text",
        "路径起点输入": "#route-from",
    }
    for name, sel in checks.items():
        el = page.locator(sel)
        visible = el.is_visible() if el.count() > 0 else False
        print(f"   {'✓' if visible else '✗'} {name} ({sel}): {'可见' if visible else '缺失/不可见'}")

    # 截图: 初始状态 (主世界)
    page.screenshot(path=str(OUT / "01_overworld.png"))
    print(f"3. 截图: 主世界初始状态 → {OUT / '01_overworld.png'}")

    # 检查 POI 标记数量
    poi_markers = page.locator(".mc-poi-marker").count()
    player_markers = page.locator(".mc-player-marker").count()
    portal_markers = page.locator(".mc-portal-marker").count()
    print(f"4. 标记数量: POI={poi_markers}, 玩家={player_markers}, 传送门={portal_markers}")

    # 测试坐标显示 (鼠标移动到地图中心)
    print("5. 测试坐标显示...")
    map_box = page.locator("#map").bounding_box()
    page.mouse.move(map_box["x"] + map_box["width"] / 2, map_box["y"] + map_box["height"] / 2)
    page.wait_for_timeout(300)
    coord_text = page.locator("#coord-text").text_content()
    print(f"   坐标显示: {coord_text}")

    # 测试维度切换: 下界
    print("6. 切换到下界...")
    page.locator("#dim-select").select_option("-1")
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "02_nether.png"))
    print(f"   截图: 下界 → {OUT / '02_nether.png'}")

    # 测试维度切换: 末地
    print("7. 切换到末地...")
    page.locator("#dim-select").select_option("1")
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "03_end.png"))
    print(f"   截图: 末地 → {OUT / '03_end.png'}")

    # 回到主世界, 测试搜索
    print("8. 测试搜索...")
    page.locator("#dim-select").select_option("0")
    page.wait_for_timeout(500)
    page.locator("#search-input").fill("出生")
    page.wait_for_timeout(500)  # 等联想
    page.screenshot(path=str(OUT / "04_search_suggest.png"))
    print(f"   截图: 搜索联想 → {OUT / '04_search_suggest.png'}")
    suggest_count = page.locator(".suggest-item").count()
    print(f"   联想结果数: {suggest_count}")

    # 回车搜索
    page.locator("#search-input").press("Enter")
    page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / "05_search_result.png"))
    print(f"   截图: 搜索结果 → {OUT / '05_search_result.png'}")

    # 检查瓦片 404 错误
    print("\n9. 检查浏览器 console 错误:")
    if errors:
        for e in errors[:10]:
            print(f"   {e}")
    else:
        print("   无错误")

    browser.close()
    print(f"\n完成。截图保存于: {OUT}")
