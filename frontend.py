import os
import streamlit as st
import requests
import pandas as pd

# Clean target URL string with NO trailing slash to maintain valid route concatenations
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

    st.divider()
    st.info(
        "**How it works**\n\n"
        "1. Add one or more **Category / Subcategory** rows.\n"
        "   - Leaving Subcategory blank → whole category scraped.\n"
        "   - Mix freely across categories.\n"
        "2. Click **Browse & Track Discounts**.\n\n"
        "The scraper opens Zepto's real pages directly\n"
        "— no keyword search at all."
    )

# ─────────────────────────────────────────────
#  LOAD CATEGORIES FROM BACKEND
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_categories() -> dict:
    try:
        r = requests.get(f"{API_BASE}/api/categories", timeout=8)
        r.raise_for_status()
        return r.json().get("categories", {})
    except Exception:
        return {}

categories = fetch_categories()

if not categories:
    st.warning("⚠️ Cannot reach backend. Start it first:")
    st.code("python backend.py", language="bash")
    st.stop()

cat_names = list(categories.keys())

# ─────────────────────────────────────────────
#  MULTI-SELECT BUILDER
# ─────────────────────────────────────────────
st.subheader("📂 Select What to Scrape")
st.caption("Add as many category/subcategory combinations as you like. "
           "Leave Subcategory blank to scrape the whole category.")

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
            f"Category" if i == 0 else " ",
            options=cat_names,
            index=cat_names.index(sel["category"]) if sel["category"] in cat_names else 0,
            key=f"cat_{i}",
            label_visibility="visible" if i == 0 else "collapsed",
        )
        st.session_state.selections[i]["category"] = chosen_cat

    with c_sub:
        subcat_options = ["— All subcategories —"] + categories[chosen_cat]
        current_sub = sel.get("subcategory") or "— All subcategories —"
        if current_sub not in subcat_options:
            current_sub = "— All subcategories —"

        chosen_sub = st.selectbox(
            "Subcategory (optional)" if i == 0 else " ",
            options=subcat_options,
            index=subcat_options.index(current_sub),
            key=f"sub_{i}",
            label_visibility="visible" if i == 0 else "collapsed",
        )
        st.session_state.selections[i]["subcategory"] = (
            None if chosen_sub == "— All subcategories —" else chosen_sub
        )

    with c_del:
        if i == 0:
            st.write("")
        if st.button("✖", key=f"del_{i}", help="Remove this row",
                     disabled=len(st.session_state.selections) == 1):
            remove_row(i)
            st.rerun()

st.button("➕ Add another", on_click=add_row)

# ── Scope summary ─────────────────────────────
st.divider()
total_pages = 0
summary_lines = []
for sel in st.session_state.selections:
    cat = sel["category"]
    sub = sel.get("subcategory")
    if sub:
        summary_lines.append(f"• **{cat}  ›  {sub}** (1 page)")
        total_pages += 1
    else:
        n = len(categories[cat])
        summary_lines.append(f"• **{cat}** — all {n} subcategor{'ies' if n != 1 else 'y'}")
        total_pages += n

st.success(
    f"🔍 **{total_pages} page(s)** queued across "
    f"**{len(st.session_state.selections)} selection(s)**\n\n"
    + "\n".join(summary_lines)
)
st.caption(f"📌 Prices will reflect pincode **{pincode}**.")

if total_pages > 8:
    st.warning(
        f"⚠️ {total_pages} pages selected — this may take several minutes. "
        "Consider narrowing to specific subcategories."
    )

st.divider()

# ─────────────────────────────────────────────
#  SEARCH BUTTON
# ─────────────────────────────────────────────
go = st.button(
    "🚀 Browse & Track Discounts",
    type="primary",
    use_container_width=True,
)

if go:
    payload = {
        "selections": [
            {
                "category":    sel["category"],
                "subcategory": sel.get("subcategory"),
            }
            for sel in st.session_state.selections
        ],
        "alert_threshold": alert_threshold,
        "pincode":         pincode,
    }

    scope_label = ", ".join(
        f"{s['category']} › {s['subcategory']}" if s.get("subcategory")
        else s["category"]
        for s in st.session_state.selections
    )

    with st.spinner(
        f"🔄 Scraping **{total_pages}** page(s) for: {scope_label} | pincode {pincode}…  "
        "Please wait, browser is running."
    ):
        try:
            resp = requests.post(
                f"{API_BASE}/api/check-discount-multi",
                json=payload,
                timeout=900,
            )
            data = resp.json()
        except requests.exceptions.Timeout:
            st.error("⏱️ Timed out. Try selecting fewer subcategories.")
            st.stop()
        except Exception as e:
            st.error(f"❌ API error: {e}")
            st.stop()

    if data.get("status") == "error":
        st.error(f"❌ {data.get('details', 'Unknown scraper error')}")
        st.stop()

    elif data.get("status") == "success":
        total        = data["total_items_scanned"]
        n_alerts     = data["total_alerts_triggered"]
        all_items    = data.get("all_scanned_items", [])
        alert_items  = data.get("high_discount_items", [])
        urls_scraped = data.get("urls_scraped", 1)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📂 Pages Scraped",  urls_scraped)
        c2.metric("📦 Products Found", total)
        c3.metric(f"🔥 ≥ {alert_threshold}% Off", n_alerts)
        c4.metric(
            "💰 Best Discount",
            f"{max((p['discount_percent'] for p in all_items), default=0):.1f}%",
        )
        c5.metric("📍 Pincode", pincode)

        st.divider()

        if tg_enabled and alert_items:
            with st.spinner("📲 Sending Telegram alerts…"):
                sent, err = send_telegram_alert(
                    tg_token, tg_chat_id, alert_items, alert_threshold
                )
            if err:
                st.warning(f"⚠️ Telegram: sent {sent} message(s), but some errors occurred: {err}")
            else:
                st.success(f"✅ Telegram: {sent} alert(s) sent to chat `{tg_chat_id}`")
        elif tg_enabled and not alert_items:
            st.info("📲 Telegram: no alerts to send (no products met the threshold).")

        if alert_items:
            st.subheader(f"🔥 {n_alerts} Product(s) with ≥ {alert_threshold}% Discount")

            df_a = (
                pd.DataFrame(alert_items)
                .rename(columns={
                    "product_name":     "Product",
                    "mrp":              "MRP (₹)",
                    "selling_price":    "Price (₹)",
                    "discount_percent": "Discount %",
                    "product_link":     "Link",
                    "source":           "Subcategory",
                })
                .sort_values("Discount %", ascending=False)
            )
            df_disp = df_a.copy()
            df_disp["Link"] = df_disp["Link"].apply(
                lambda u: f'<a href="{u}" target="_blank">🔗 View</a>'
            )
            st.write(df_disp.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info(
                f"ℹ️ No products with ≥ {alert_threshold}% discount found.  "
                "Try lowering the discount threshold in the sidebar."
            )

        st.divider()

        with st.expander(f"📋 All {total} Scanned Products", expanded=False):
            if all_items:
                df_all = (
                    pd.DataFrame(all_items)
                    .rename(columns={
                        "product_name":     "Product",
                        "mrp":              "MRP (₹)",
                        "selling_price":    "Price (₹)",
                        "discount_percent": "Discount %",
                        "product_link":     "Link",
                        "source":           "Subcategory",
                })
                .sort_values("Discount %", ascending=False)
                )

                def colour_discount(val):
                    if val >= 40: return "background-color:#c6efce;color:#276221"
                    if val >= 20: return "background-color:#ffeb9c;color:#9c5700"
                    if val >  0:  return "background-color:#fff2cc"
                    return ""

                df_all_disp = df_all.copy()
                df_all_disp["Link"] = df_all_disp["Link"].apply(
                    lambda u: f'<a href="{u}" target="_blank">🔗 View</a>'
                )
                st.write(
                    df_all_disp.style.map(colour_discount, subset=["Discount %"])
                    .to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )

                csv  = df_all.to_csv(index=False).encode("utf-8")
                safe = scope_label.replace(" ", "_").replace("›", "-").replace("/", "-")[:60]
                st.download_button(
                    "⬇️ Download as CSV",
                    data=csv,
                    file_name=f"zepto_{safe}_{pincode}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No products were returned from Zepto.")
    else:
        st.error("Unexpected response from backend.")
else:
    st.info(
        "👆 Build your selection above (add as many rows as you like), "
        "then click **Browse & Track Discounts**."
                         )
        
