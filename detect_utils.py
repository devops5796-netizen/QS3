import json
from scrapling import StealthyFetcher

def get_subcategories(base_url: str) -> list:
    page = StealthyFetcher.fetch(base_url, headless=True, network_idle=True, timeout=90000)
    subcats = []
    links = page.find_all("[data-testid^='at-sub-category-']")
    
    for link in links:
        testid = link.attrib.get("data-testid", "")
        idx = testid.replace("at-sub-category-", "")
        if idx == "0":
            continue
        href = link.attrib.get("href", "").strip()
        if not href:
            continue
        name_el = link.find("p")
        name = name_el.text.strip() if name_el else href.split("-")[-1]
        full_url = f"https://qatarsale.com{href}" if href.startswith("/") else href
        slug = href.rstrip("/").split("/")[-1]

        try:
            sub_page = StealthyFetcher.fetch(
                full_url,
                headless=True,
                network_idle=True,
                timeout=90000
            )
            sub_links = sub_page.find_all("[data-testid^='at-sub-category-']")
            sub_links = [
                l for l in sub_links
                if l.attrib.get("data-testid", "").replace("at-sub-category-", "") != "0"
            ]

            if sub_links:
                for sub_link in sub_links:
                    sub_href = sub_link.attrib.get("href", "").strip()
                    if not sub_href:
                        continue
                    sub_name_el = sub_link.find("p")
                    sub_name = sub_name_el.text.strip() if sub_name_el else sub_href.split("-")[-1]
                    sub_full_url = f"https://qatarsale.com{sub_href}" if sub_href.startswith("/") else sub_href
                    sub_slug = sub_href.rstrip("/").split("/")[-1]
                    subcats.append({
                        "name": f"{sub_name} [{name}]",
                        "slug": sub_slug,
                        "url":  sub_full_url
                    })
            else:
                subcats.append({"name": name, "slug": slug, "url": full_url})

        except Exception as e:
            print(f"  Failed to check sub-subcats for {name}: {e}")
            subcats.append({"name": name, "slug": slug, "url": full_url})

    return subcats


def analyze_category_with_products(url: str):
    page = StealthyFetcher.fetch(
        f"{url}&page=1",
        headless=True,
        network_idle=True,
        timeout=90000
    )

    # 1. check if products exist
    product_cards = page.find_all("qs-product-card-v2")
    if not product_cards:
        product_cards = page.find_all("qs-product-card-classic")
    
    # If no product cards at all → no products
    if not product_cards:
        return 0, False

    # 2. extract pagination
    numbers = []
    pagination_els = page.find_all("[data-testid^='at-paginator-page-']")
    for el in pagination_els:
        a = el.find("a")
        if not a:
            continue
        href = a.attrib.get("href", "")
        if "page=" in href:
            try:
                numbers.append(int(href.split("page=")[-1]))
            except ValueError:
                pass

    last_page = max(numbers) if numbers else 1
    return last_page, True