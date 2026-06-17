import json
from scrapling import StealthyFetcher

def get_subcategories_recursive(base_url: str, parent_names: list = []) -> list:
    page = StealthyFetcher.fetch(base_url, headless=True, network_idle=True, timeout=90000)
    subcats = []
    
    base_path = base_url.split("?")[0].replace("https://qatarsale.com", "")
    
    links = page.find_all("[data-testid^='at-sub-category-']")
    links = [l for l in links if l.attrib.get("data-testid", "").replace("at-sub-category-", "") != "0"]
    
    real_children = [l for l in links if l.attrib.get("href", "").startswith(base_path + "-")]
    
    if not real_children:
        return []
    
    for link in real_children:
        href = link.attrib.get("href", "").strip()
        if not href:
            continue
        name_el = link.find("p")
        name = name_el.text.strip() if name_el else href.split("-")[-1]
        full_url = f"https://qatarsale.com{href}"
        slug = href.rstrip("/").split("/")[-1]
        
        children = get_subcategories_recursive(full_url, parent_names + [name])
        
        if children:
            subcats.extend(children)
        else:
            if parent_names:
                brackets = "".join([f" [{p}]" for p in parent_names])
                display_name = f"{name}{brackets}"
            else:
                display_name = name
            subcats.append({
                "name": display_name,
                "slug": slug,
                "url": full_url
            })
    
    return subcats


def get_subcategories(base_url: str) -> list:
    return get_subcategories_recursive(base_url)


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