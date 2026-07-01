import json
import random
import time
import pandas as pd
from scrapling import StealthyFetcher

BASE_URL = "https://qatarsale.com"
BASE_PRODUCT_URL = "https://qatarsale.com/ar/product"


# -------------------------
# DETAILS
# -------------------------


def parse_showroom_details(page, url: str) -> dict:
    name = ""
    cover_image = ""
    phones = []
    whatsapps = []
    posts_count = ""
    views_count = ""

    name_el = page.css("[data-testid='at-showroom-details-name-text'] h1")
    if name_el:
        name = name_el[0].text.strip()

    img_el = page.css("[data-testid='at-showroom-details-cover-image'] img")
    if img_el:
        cover_image = img_el[0].attrib.get("src", "")

    phone_blocks = page.css("[data-testid^='at-showroom-details-phone-link']")

    for p in phone_blocks:
        href = p.attrib.get("href", "")
        if href.startswith("tel:"):
            phones.append(href.replace("tel:", "").strip())

    whatsapp_blocks = page.css("[data-testid='at-showroom-details-whatsapp-link']")
    for w in whatsapp_blocks:
        href = w.attrib.get("href", "")
        if "phone=" in href:
            num = href.split("phone=")[-1].strip()
            whatsapps.append(num)

    posts_el = page.css("[data-testid='at-showroom-details-posts-count-text']")
    if posts_el:
        posts_count = posts_el[0].text.strip()

    views_el = page.css("[data-testid='at-showroom-details-posts-view-text']")
    if views_el:
        views_count = views_el[0].text.strip()

    return {
        "url": url,
        "name": name,
        "cover_image": cover_image,
        "phones": str(phones),
        "whatsapps": str(whatsapps),
        "posts_count": posts_count,
        "views_count": views_count
    }


# -------------------------
# PAGES COUNT (IMPORTANT FIX)
# -------------------------
def get_max_pages(page, url):
    try:
        script = page.find("script", {"id": "serverApp-state"})
        if not script:
            return []

        raw = (script.text
               .replace("&q;", '"')
               .replace("&l;", "<")
               .replace("&g;", ">")
               .replace("&a;", "&")
               .replace("&s;", "'"))

        data = json.loads(raw)

        pagesCount = data["ProductList"]['pagesCount']

    except Exception as e:
        print(f"❌ Error: {url} -> {e}")

    return pagesCount

# -------------------------
# PRODUCT LINKS ONLY
# -------------------------
def extract_product_links(page, source_url: str):
    rows = []
    try:
        script = page.find("script", {"id": "serverApp-state"})
        if not script:
            return []

        raw = (script.text
               .replace("&q;", '"')
               .replace("&l;", "<")
               .replace("&g;", ">")
               .replace("&a;", "&")
               .replace("&s;", "'"))

        data = json.loads(raw)

        if "ProductList" not in data:
            return []

        products  = data["ProductList"]["list"]
        defs_meta = {str(d["id"]): d["label"] for d in data["ProductList"].get("defsMetaData", [])}

        for product in products:
            specs = {defs_meta[k]: v for k, v in product.get("definitions", {}).items() if k in defs_meta}
            row   = {k: v for k, v in product.items() if k != "definitions"}
            row.update(specs)
            row["source_url"]  = source_url
            row["product_url"] = f"{BASE_PRODUCT_URL}/{product.get('uri', '')}" if product.get("uri") else ""
            rows.append(row)

    except Exception as e:
        print(f"  Error parsing state: {e}")

    return rows


# -------------------------
# MAIN SCRAPER
# -------------------------
def scrape_showroom(showroom_url):
    print(f"\nScraping: {showroom_url}")

    try:
        page = StealthyFetcher.fetch(
            showroom_url,
            headless=True,
            network_idle=True,
            timeout=60000,
            wait_for_idle_network_timeout=10000
        )
    except Exception as e:
        print(f"  [ERROR] Failed to fetch showroom page: {e}")
        return {}, []
    
    details = parse_showroom_details(page, showroom_url)
    max_pages = get_max_pages(page, showroom_url)
    print(f"Pages: {max_pages}")

    all_rows     = []
    failed_pages = {}
    success_count = 0

    for p in range(1, max_pages + 1):
        url = f"{showroom_url}?page={p}"

        for attempt in range(3):
            try:
                pg = StealthyFetcher.fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    timeout=60000,
                    wait_for_idle_network_timeout=10000
                )
                rows = extract_product_links(pg, showroom_url)

                if rows:
                    all_rows.extend(rows)
                    print(f"  ✓ Found {len(rows)} products")
                    success_count += 1
                    break
                else:
                    failed_pages[f"Page {p}"] = "No products found"
                    print(f"  ⚠ No products found")
                    break

            except Exception as e:
                if attempt < 2:
                    print(f"  Attempt {attempt+1} failed, retrying...")
                    time.sleep(3)
                else:
                    failed_pages[f"Page {p}"] = str(e)
                    print(f"  Error: {e}")

        if p < max_pages:
            time.sleep(random.uniform(1.0, 3.0))
    
    all_products_df = pd.DataFrame(all_rows)

    # deduplicate
    if "product_url" in all_products_df.columns:
        all_products_df = all_products_df.drop_duplicates(subset=["product_url"], keep="first")

    return details, all_products_df