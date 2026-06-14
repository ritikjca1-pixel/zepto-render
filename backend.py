import os
import re
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright, Page, BrowserContext
import uvicorn

app = FastAPI(title="Zepto Category Scraper API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load category map from categories_urls (1).json verbatim
_JSON_PATH = os.path.join(os.path.dirname(__file__), "categories_urls (1).json")

def _load_category_map() -> dict:
    with open(_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CATEGORY_MAP: dict = _load_category_map()

PINCODE_COORDS: dict[str, tuple[float, float]] = {
    "110001": (28.6357, 77.2245), "110002": (28.6406, 77.2359), "110003": (28.6525, 77.2090),
    "110005": (28.6563, 77.1908), "110006": (28.6514, 77.1904), "110007": (28.6758, 77.2097),
    "110008": (28.6582, 77.1697), "110009": (28.6685, 77.2282), "110010": (28.6289, 77.2569),
    "110011": (28.6012, 77.2090), "110012": (28.6431, 77.1603), "110013": (28.6082, 77.2431),
    "110014": (28.5969, 77.2631), "110015": (28.6352, 77.1481), "110016": (28.5494, 77.1951),
    "110017": (28.5494, 77.2001), "110018": (28.6244, 77.1355), "110019": (28.5400, 77.2500),
    "110020": (28.5714, 77.1894), "110021": (28.5604, 77.1792), "110022": (28.6122, 77.1553),
    "110023": (28.6337, 77.2098), "110024": (28.5700, 77.2400), "110025": (28.5733, 77.2090),
    "110026": (28.6520, 77.1250), "110027": (28.6352, 77.1097), "110028": (28.5982, 77.1691),
    "110029": (28.5454, 77.2231), "110030": (28.5274, 77.1895), "110031": (28.6827, 77.2907),
    "110032": (28.6727, 77.3090), "110033": (28.6924, 77.1480), "110034": (28.7165, 77.1488),
    "110035": (28.7012, 77.1300), "110036": (28.7345, 77.1613), "110037": (28.5802, 77.1278),
    "110038": (28.5641, 77.1097), "110039": (28.5800, 77.1097), "110040": (28.7179, 77.1064),
    "110041": (28.7000, 77.0836), "110042": (28.7258, 77.1900), "110043": (28.6197, 77.0642),
    "110044": (28.5327, 77.2951), "110045": (28.5891, 77.1102), "110046": (28.5697, 77.0886),
    "110047": (28.5410, 77.1590), "110048": (28.5562, 77.2410), "110049": (28.5274, 77.2265),
    "110051": (28.6588, 77.3064), "110052": (28.6839, 77.1698), "110053": (28.6651, 77.2959),
    "110054": (28.6696, 77.2083), "110055": (28.6451, 77.2129), "110056": (28.6308, 77.1248),
    "110057": (28.5281, 77.1673), "110058": (28.6228, 77.0934), "110059": (28.6018, 77.0724),
    "110060": (28.6344, 77.1742), "110061": (28.5478, 77.2712), "110062": (28.5194, 77.2102),
    "110063": (28.6040, 77.1046), "110064": (28.6522, 77.1523), "110065": (28.5324, 77.2195),
    "110066": (28.5802, 77.1530), "110067": (28.5196, 77.1809), "110068": (28.5085, 77.2081),
    "110069": (28.5325, 77.2092), "110070": (28.5066, 77.1617), "110071": (28.5436, 77.1292),
    "110072": (28.6065, 77.0508), "110073": (28.5934, 77.0620), "110074": (28.5586, 77.0705),
    "110075": (28.6218, 77.0500), "110076": (28.5433, 77.2928), "110077": (28.5916, 77.0358),
    "110078": (28.6036, 77.0345), "110081": (28.6857, 77.0813), "110082": (28.7201, 77.1253),
    "110083": (28.7014, 77.0614), "110084": (28.7138, 77.0948), "110085": (28.7020, 77.1108),
    "110086": (28.6888, 77.0980), "110087": (28.6740, 77.0780), "110088": (28.6946, 77.1588),
    "110089": (28.5986, 77.2898), "110090": (28.6445, 77.3167), "110091": (28.6188, 77.3129),
    "110092": (28.6454, 77.3381), "110093": (28.6124, 77.3410), "110094": (28.6274, 77.3511),
    "110095": (28.6668, 77.3408), "110096": (28.5866, 77.3282), "201301": (28.5706, 77.3260),
    "201304": (28.5356, 77.3910), "400001": (18.9322, 72.8264), "400050": (19.0596, 72.8295),
    "400051": (19.0748, 72.8856), "400053": (19.0728, 72.8427), "400054": (19.0503, 72.8422),
    "400057": (19.0760, 72.8777), "400058": (19.0531, 72.8355), "400059": (19.0669, 72.8553),
    "400060": (19.0453, 72.8479), "400061": (19.0533, 72.8611), "400062": (19.1117, 72.8361),
    "400063": (19.1341, 72.8392), "400064": (19.1093, 72.8486), "400066": (19.1213, 72.8534),
    "400067": (19.1398, 72.8549), "400068": (19.0947, 72.8593), "400069": (19.1026, 72.8697),
    "400070": (19.0696, 72.8780), "400071": (19.0610, 72.9003), "400072": (19.0445, 72.9094),
    "400076": (19.0302, 72.8565), "400077": (19.0217, 72.8487), "400078": (19.0321, 72.9076),
    "400079": (19.0230, 72.9016), "400080": (19.0116, 72.8480), "400081": (18.9783, 72.8350),
    "400086": (19.0272, 72.8419), "400088": (19.0104, 72.8654), "400089": (18.9935, 72.8310),
    "400093": (19.0864, 72.8985), "400097": (19.1284, 72.8759), "400098": (19.1407, 72.8879),
    "400099": (19.1606, 72.8573), "400101": (19.1700, 72.8399), "400102": (19.1839, 72.8306),
    "400103": (19.1898, 72.8487), "400104": (19.2052, 72.8397), "560001": (12.9716, 77.5946),
    "560002": (12.9780, 77.5989), "560003": (12.9901, 77.5688), "560004": (12.9826, 77.5779),
    "560008": (13.0026, 77.5695), "560010": (12.9667, 77.5745), "560011": (12.9487, 77.5716),
    "560016": (12.9201, 77.6246), "560017": (13.0183, 77.6437), "560020": (12.9784, 77.6436),
    "560021": (12.9478, 77.5900), "560022": (12.9347, 77.5686), "560023": (12.9213, 77.6129),
    "560024": (12.9629, 77.6423), "560025": (13.0050, 77.5950), "560027": (12.9948, 77.5584),
    "560029": (12.9569, 77.5508), "560030": (12.9412, 77.5505), "560032": (13.0311, 77.5633),
    "560033": (13.0445, 77.5820), "560034": (12.9352, 77.6245), "560035": (12.9094, 77.6450),
    "560036": (12.9162, 77.5979), "560037": (12.9291, 77.6381), "560038": (12.9053, 77.5754),
    "560040": (13.0100, 77.5427), "560041": (12.9905, 77.5405), "560042": (12.9729, 77.5318),
    "560043": (13.0396, 77.5453), "560045": (12.9082, 77.6218), "560046": (13.0648, 77.6019),
    "560047": (13.0516, 77.6210), "560048": (12.9190, 77.5481), "560050": (13.0267, 77.5241),
    "560051": (13.0602, 77.5640), "560052": (13.0727, 77.5940), "560053": (13.0556, 77.5426),
    "560054": (13.0779, 77.5636), "560055": (13.0918, 77.5699), "560056": (13.0777, 77.5282),
    "560057": (12.9942, 77.5193), "560058": (12.9756, 77.5175), "560059": (12.9600, 77.5155),
    "560060": (12.9431, 77.5226), "560061": (12.9270, 77.5261), "560062": (12.9129, 77.5385),
    "560063": (12.8982, 77.5487), "560064": (12.8829, 77.5549), "560065": (12.8681, 77.5605),
    "560066": (12.8556, 77.5641), "560067": (12.8418, 77.5677), "560068": (12.8296, 77.5704),
    "560069": (12.8171, 77.5741), "560070": (12.8034, 77.5777), "560071": (12.9467, 77.6589),
    "560072": (12.9601, 77.6744), "560073": (12.9749, 77.6899), "560074": (12.9874, 77.7036),
    "560075": (13.0013, 77.7171), "560076": (13.0204, 77.6891), "560077": (13.0332, 77.6738),
    "560078": (13.0442, 77.6593), "560079": (13.0561, 77.6442), "560080": (13.0672, 77.6283),
    "560082": (13.0804, 77.5968), "560083": (13.0953, 77.5820), "560085": (13.1082, 77.5601),
    "560086": (13.1205, 77.5396), "560087": (13.1332, 77.5203), "560088": (13.1453, 77.5008),
    "560089": (13.1590, 77.4822), "560090": (13.1723, 77.4611), "560091": (13.1868, 77.4418),
    "560092": (12.8989, 77.6446), "560093": (12.8849, 77.6543), "560094": (12.8698, 77.6627),
    "560095": (12.8552, 77.6688), "560096": (12.8413, 77.6756), "560097": (12.8268, 77.6823),
    "560098": (12.8129, 77.6893), "560099": (12.7989, 77.6957), "560100": (13.1968, 77.7066),
    "560103": (13.0155, 77.7337), "560104": (13.0305, 77.7487), "560105": (12.8398, 77.7303),
    "560107": (13.0450, 77.7641), "560109": (12.9149, 77.6382), "560110": (12.9014, 77.6301),
    "600001": (13.0827, 80.2707), "700001": (22.5726, 88.3639), "500001": (17.3850, 78.4867),
    "411001": (18.5204, 73.8567), "380001": (23.0225, 72.5714), "302001": (26.9124, 75.7873),
    "226001": (26.8467, 80.9462),
}

def _launch_browser(p) -> tuple[BrowserContext, Page]:
    profile_dir = os.path.join(os.getcwd(), "zepto_profile")
    os.makedirs(profile_dir, exist_ok=True)
    kwargs = dict(
        headless=True,  # Changed to True for running on headless Render nodes
        viewport={"width": 1366, "height": 768},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    try:
        ctx = p.chromium.launch_persistent_context(profile_dir, channel="chrome", **kwargs)
    except Exception:
        ctx = p.chromium.launch_persistent_context(profile_dir, **kwargs)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return ctx, page

def _inject_pincode(page: Page, pincode: str):
    coords = PINCODE_COORDS.get(pincode, (28.6139, 77.2090))
    lat, lng = coords
    print(f"📍 Pincode {pincode}  →  lat={lat}  lng={lng}")
    page.evaluate(f"""() => {{
        const loc = {{lat:{lat}, lng:{lng}, address:"{pincode}, India",
                      pincode:"{pincode}", city:"India"}};
        localStorage.setItem('userLocation', JSON.stringify(loc));
        localStorage.setItem('zepto_user_pincode', '{pincode}');
        localStorage.setItem('pincode', '{pincode}');
        document.cookie = 'pincode={pincode}; path=/';
        document.cookie = 'userPincode={pincode}; path=/';
    }}""")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

def _extract_products(page: Page, source_label: str) -> list[dict]:
    for _ in range(8):
        page.keyboard.press("End")
        page.wait_for_timeout(800)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1500)

    cards = page.locator('a[href*="/pn/"]').all()
    print(f"  ↳ {len(cards)} card(s) found on '{source_label}'")

    products: list[dict] = []
    seen: set[str] = set()

    for card in cards:
        try:
            href = card.get_attribute("href") or ""
            if not href or href in seen:
                continue
            seen.add(href)

            full_url = f"https://www.zepto.com{href}" if href.startswith("/") else href
            text = card.inner_text().strip()
            if not text:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            title = "Unknown Product"
            for line in lines:
                if (
                    "₹" not in line
                    and "Rs." not in line
                    and line.upper() not in ("ADD", "OUT OF STOCK", "NOTIFY", "SOLD OUT")
                    and len(line) > 3
                ):
                    title = line
                    break

            prices = [
                float(m)
                for m in re.findall(r'(?:₹|Rs\.?)\s*(\d+(?:\.\d+)?)', text)
            ]
            if not prices:
                continue

            sp  = prices[0]
            mrp = prices[1] if len(prices) > 1 else prices[0]
            if sp > mrp:
                sp, mrp = mrp, sp

            disc = round((mrp - sp) / mrp * 100, 2) if mrp > 0 and sp < mrp else 0.0

            products.append({
                "product_name":    title,
                "product_link":    full_url,
                "mrp":             mrp,
                "selling_price":   sp,
                "discount_percent": disc,
                "source":          source_label,
            })
        except Exception:
            continue

    return products

def scrape_urls(urls: list[tuple[str, str]], pincode: str) -> list[dict]:
    all_products: list[dict] = []
    with sync_playwright() as p:
        ctx, page = _launch_browser(p)
        print("🏠 Loading Zepto homepage…")
        page.goto("https://www.zepto.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        _inject_pincode(page, pincode)

        for label, url in urls:
            print(f"\n📂 Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(4500)
            products = _extract_products(page, label)
            all_products.extend(products)
        ctx.close()

    seen: set[str] = set()
    unique: list[dict] = []
    for p in all_products:
        if p["product_link"] not in seen:
            seen.add(p["product_link"])
            unique.append(p)
    return unique

@app.get("/api/categories")
def get_categories():
    result = {}
    for cat, data in CATEGORY_MAP.items():
        result[cat] = list(data["subcategories"].keys())
    return {"categories": result}

@app.get("/api/check-discount")
def check_discount(
    category: str   = Query(...,    description="Category name"),
    subcategory: Optional[str] = Query(None, description="Subcategory name (omit = entire category)"),
    alert_threshold: float     = Query(20.0, description="Min discount % to flag"),
    pincode: str               = Query("110017"),
):
    if category not in CATEGORY_MAP:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not in map.")

    cat_data = CATEGORY_MAP[category]
    subcats  = cat_data["subcategories"]

    if subcategory:
        if subcategory not in subcats:
            raise HTTPException(status_code=404, detail=f"Subcategory '{subcategory}' not found.")
        urls_to_scrape = [(f"{category} › {subcategory}", subcats[subcategory])]
    else:
        urls_to_scrape = [
            (f"{category} › {sub}", url)
            for sub, url in subcats.items()
        ]

    print(f"\n🗂  Scraping {len(urls_to_scrape)} URL(s) for '{category}'"
          f"{' › ' + subcategory if subcategory else ''} | pincode={pincode}")

    try:
        products = scrape_urls(urls_to_scrape, pincode)
    except Exception as e:
        return {"status": "error", "error_type": type(e).__name__, "details": str(e)}

    alerts = [p for p in products if p["discount_percent"] >= alert_threshold]

    return {
        "status":               "success",
        "category":             category,
        "subcategory":          subcategory,
        "pincode":              pincode,
        "urls_scraped":         len(urls_to_scrape),
        "total_items_scanned":  len(products),
        "total_alerts_triggered": len(alerts),
        "high_discount_items":  alerts,
        "all_scanned_items":    products,
    }

from pydantic import BaseModel

class Selection(BaseModel):
    category: str
    subcategory: Optional[str] = None

class MultiScrapeRequest(BaseModel):
    selections: list[Selection]
    alert_threshold: float = 20.0
    pincode: str = "110017"

@app.post("/api/check-discount-multi")
def check_discount_multi(req: MultiScrapeRequest):
    urls_to_scrape: list[tuple[str, str]] = []

    for sel in req.selections:
        cat = sel.category
        sub = sel.subcategory

        if cat not in CATEGORY_MAP:
            raise HTTPException(status_code=404, detail=f"Category '{cat}' not in map.")

        subcats = CATEGORY_MAP[cat]["subcategories"]

        if sub:
            if sub not in subcats:
                raise HTTPException(status_code=404, detail=f"Subcategory '{sub}' not found in '{cat}'.")
            urls_to_scrape.append((f"{cat} › {sub}", subcats[sub]))
        else:
            for subcat_name, url in subcats.items():
                urls_to_scrape.append((f"{cat} › {subcat_name}", url))

    seen_urls: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for label, url in urls_to_scrape:
        if url not in seen_urls:
            seen_urls.add(url)
            deduped.append((label, url))

    print(f"\n🗂  Multi-scrape: {len(deduped)} unique URL(s) | pincode={req.pincode}")

    try:
        products = scrape_urls(deduped, req.pincode)
    except Exception as e:
        return {"status": "error", "error_type": type(e).__name__, "details": str(e)}

    alerts = [p for p in products if p["discount_percent"] >= req.alert_threshold]

    return {
        "status":                 "success",
        "pincode":                req.pincode,
        "urls_scraped":           len(deduped),
        "total_items_scanned":    len(products),
        "total_alerts_triggered": len(alerts),
        "high_discount_items":    alerts,
        "all_scanned_items":      products,
    }

if __name__ == "__main__":
    # Render assigns dynamic ports via environment variable. 0.0.0.0 enables outside routing.
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
