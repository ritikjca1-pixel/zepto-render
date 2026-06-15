import os
import streamlit as st
import requests
import pandas as pd

# The exact target link for your active Render backend service
API_BASE = "https://zepto-render-1.onrender.com"

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Zepto Discount Tracker",
    page_icon="🛒",
    layout="wide",
)

st.title("🛒 Zepto Discount Alert Tracker")
st.caption(
    "Navigates directly to Zepto's real category/subcategory pages "
    "and scrapes every product — no keyword search."
)

# ─────────────────────────────────────────────
#  TELEGRAM HELPER
# ─────────────────────────────────────────────
def send_telegram_alert(bot_token: str, chat_id: str, products: list[dict], threshold: float):
    if not bot_token or not chat_id:
        return 0, "Bot token or Chat ID is missing."

    base_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    sent = 0
    errors = []

    header = (
        f"🛒 *Zepto Discount Alert*\n"
        f"🔥 *{len(products)}* product(s) with ≥ {threshold:.0f}% off\n"
        f"{'─' * 28}"
    )
    try:
        requests.post(base_url, json={
            "chat_id":    chat_id,
            "text":       header,
            "parse_mode": "Markdown",
        }, timeout=10)
    except Exception as e:
        errors.append(str(e))

    for prod in products[:20]:
        disc  = prod.get("discount_percent", 0)
        mrp   = prod.get("mrp", 0)
        price = prod.get("selling_price", 0)
        link  = prod.get("product_link", "")
        name  = prod.get("product_name", "Unknown")
        src   = prod.get("source", "")

        msg = (
            f"🏷️ *{name}*\n"
            f"📂 {src}\n"
            f"💰 ~~₹{mrp:.0f}~~ → *₹{price:.0f}* (*{disc:.1f}% off*)\n"
            f"🔗 [View on Zepto]({link})"
        )
        try:
            r = requests.post(base_url, json={
                "chat_id":                  chat_id,
                "text":                     msg,
                "parse_mode":               "Markdown",
                "disable_web_page_preview": True,
            }, timeout=10)
            if r.status_code == 200:
                sent += 1
            else:
                errors.append(r.text)
        except Exception as e:
            errors.append(str(e))

    if len(products) > 20:
        try:
            requests.post(base_url, json={
                "chat_id":    chat_id,
                "text":       f"ℹ️ _+{len(products) - 20} more products — download the CSV for the full list._",
                "parse_mode": "Markdown",
            }, timeout=10)
        except Exception:
            pass

    err_str = "; ".join(errors) if errors else None
    return sent, err_str

# ─────────────────────────────────────────────
#  SIDEBAR — Settings + Telegram
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    pincode = st.text_input("📍 Delivery Pincode", value="110017", max_chars=6)
    alert_threshold = st.slider(
        "🔔 Minimum Discount Alert (%)",
        min_value=0, max_value=90, value=20, step=5,
    )

    st.divider()
    st.subheader("📲 Telegram Alerts")
    tg_enabled  = st.toggle("Enable Telegram Alerts", value=False)
    tg_token    = st.text_input(
        "Bot Token",
        type="password",
        placeholder="123456:ABC-DEF...",
        help="Get this from @BotFather on Telegram.",
        disabled=not tg_enabled,
    )
    tg_chat_id  = st.text_input(
        "Chat ID",
        placeholder="-100123456789",
        help="Your personal chat ID or a group/channel ID.",
        disabled=not tg_enabled,
    )

# ─────────────────────────────────────────────
#  HARDCODED VERBATIM MAPPING ENGINE (No Network Dependencies)
# ─────────────────────────────────────────────
RAW_MAP = {
    "Snacks": {
        "subcategories": {
            "Chips & Crisps": "https://www.zepto.com/cn/snacks/chips-crisps/cid/99320b92-fc15-4ba5-bc4e-2895a12f4df6/scid/77ab36f4-c8c7-43f1-b8ef-0d48ff0070bc",
            "Nachos & Popcorn": "https://www.zepto.com/cn/snacks/nachos-popcorn/cid/99320b92-fc15-4ba5-bc4e-2895a12f4df6/scid/8c156477-9ca6-4fb4-81d7-21a4f00fe772",
            "Namkeen & Bhujia": "https://www.zepto.com/cn/snacks/namkeen-bhujia/cid/99320b92-fc15-4ba5-bc4e-2895a12f4df6/scid/be268045-8fbe-4ee5-bc65-0a379f648d70",
            "Puffs & Rice Snacks": "https://www.zepto.com/cn/snacks/puffs-rice-snacks/cid/99320b92-fc15-4ba5-bc4e-2895a12f4df6/scid/e634795b-cbef-4573-95ca-9d22bf6ebcf0",
            "Biscuits": "https://www.zepto.com/cn/snacks/biscuits/cid/99320b92-fc15-4ba5-bc4e-2895a12f4df6/scid/fbe9725f-2c7c-47bc-ad77-3e1a129d3326",
            "Cookies": "https://www.zepto.com/cn/snacks/cookies/cid/99320b92-fc15-4ba5-bc4e-2895a12f4df6/scid/efae2a11-5b72-46a4-bb0a-a037803ba9ef",
            "Rusks & Wafers": "https://www.zepto.com/cn/snacks/rusks-wafers/cid/99320b92-fc15-4ba5-bc4e-2895a12f4df6/scid/f56f4d85-a7b5-4b0e-b7f7-b8dbf9de4cf6"
        }
    }
}

cat_names = list(RAW_MAP.keys())

# ─────────────────────────────────────────────
#  MULTI-SELECT BUILDER
# ─────────────────────────────────────────────
st.subheader("📂 Select What to Scrape")

if "selections" not in st.session_state:
    st.session_state.selections = [{"category": cat_names[0], "subcategory": None}]

def add_row():
    st.session_state.selections.append({"category": cat_names[0], "subcategory": None})

def remove_row(idx: int):
    if len(st.session_state.selections) > 1:
        st.session_state.selections.pop(idx)

for i, sel in enumerate(st.session_state.selections):
    c_cat, c_sub, c_del = st.columns([3, 3, 0.6])

    with c_cat:
        chosen_cat = st.selectbox(
            f"Category" if i == 0 else " ", options=cat_names,
            index=cat_names.index(sel["category"]) if sel["category"] in cat_names else 0,
            key=f"cat_{i}", label_visibility="visible" if i == 0 else "collapsed"
        )
        st.session_state.selections[i]["category"] = chosen_cat

    with c_sub:
        subcat_list = list(RAW_MAP[chosen_cat]["subcategories"].keys())
        subcat_options = ["— All subcategories —"] + subcat_list
        current_sub = sel.get("subcategory") or "— All subcategories —"
        if current_sub not in subcat_options:
            current_sub = "— All subcategories —"

        chosen_sub = st.selectbox(
            "Subcategory (optional)" if i == 0 else " ", options=subcat_options,
            index=subcat_options.index(current_sub), key=f"sub_{i}",
            label_visibility="visible" if i == 0 else "collapsed"
        )
        st.session_state.selections[i]["subcategory"] = None if chosen_sub == "— All subcategories —" else chosen_sub

    with c_del:
        if i == 0: st.write("")
        if st.button("✖", key=f"del_{i}", disabled=len(st.session_state.selections) == 1):
            remove_row(i)
            st.rerun()

st.button("➕ Add another", on_click=add_row)
st.divider()

# Resolve endpoints natively out of local map state
queue = []
for sel in st.session_state.selections:
    cat = sel["category"]
    sub = sel.get("subcategory")
    subcats = RAW_MAP[cat]["subcategories"]
    if sub:
        queue.append((f"{cat} › {sub}", subcats[sub]))
    else:
        for sname, surl in subcats.items():
            queue.append((f"{cat} › {sname}", surl))

st.success(f"🔍 Queued **{len(queue)} page(s)** for localized processing.")

go = st.button("🚀 Browse & Track Discounts", type="primary", use_container_width=True)

if go:
    all_products = []
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    
    # Run sequential API calls one URL at a time to prevent Render memory crashes
    for index, (label, target_url) in enumerate(queue):
        status_text.caption(f"🔄 Processing layer ({index+1}/{len(queue)}): **{label}**...")
        try:
            res = requests.get(
                f"{API_BASE}/api/scrape-single",
                params={"label": label, "url": target_url, "pincode": pincode},
                timeout=180
            )
            data = res.json()
            if data.get("status") == "success":
                all_products.extend(data.get("products", []))
        except Exception as e:
            st.warning(f"⚠️ Layer response skipped on '{label}': {e}")
            
        progress_bar.progress((index + 1) / len(queue))
        
    status_text.empty()
    progress_bar.empty()
    
    # Deduplicate product lists
    seen_links = set()
    unique_items = []
    for item in all_products:
        if item["product_link"] not in seen_links:
            seen_links.add(item["product_link"])
            unique_items.append(item)

    alert_items = [p for p in unique_items if p["discount_percent"] >= alert_threshold]

    # Metrics Layout
    c1, c2, c3 = st.columns(3)
    c1.metric("📂 Pages Extracted", len(queue))
    c2.metric("📦 Products Found", len(unique_items))
    c3.metric(f"🔥 ≥ {alert_threshold}% Off", len(alert_items))
    
    st.divider()

    if tg_enabled and alert_items:
        with st.spinner("📲 Sending Telegram alerts…"):
            sent, err = send_telegram_alert(tg_token, tg_chat_id, alert_items, alert_threshold)
        if err: st.warning(f"⚠️ Telegram notice: {err}")
        else: st.success(f"✅ Telegram: {sent} alerts sent.")

    if alert_items:
        st.subheader("🔥 High-Discount Products Found")
        df_disp = pd.DataFrame(alert_items).rename(columns={
            "product_name": "Product", "mrp": "MRP (₹)", "selling_price": "Price (₹)",
            "discount_percent": "Discount %", "product_link": "Link", "source": "Subcategory"
        }).sort_values("Discount %", ascending=False)
        df_disp["Link"] = df_disp["Link"].apply(lambda u: f'<a href="{u}" target="_blank">🔗 View</a>')
        st.write(df_disp.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("ℹ️ No items matched your discount threshold.")
