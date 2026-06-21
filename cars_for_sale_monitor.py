import sys
import time
import random
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from scrapling.fetchers import StealthyFetcher

LISTING_URL = "https://qatarsale.com/ar/products/cars_for_sale?basic_search:StatusFilter=0"


def get_last_page():

    StealthyFetcher.configure(auto_match=False)
    fetcher = StealthyFetcher()
    page = fetcher.fetch(LISTING_URL, timeout=30)

    if page.status != 200:
        raise Exception(f"HTTP {page.status} on {LISTING_URL}")

    soup = BeautifulSoup(page.content, "html.parser")

    pages = []
    for a in soup.select("a[href*='page=']"):
        href = a.get("href", "")
        if "page=" not in href:
            continue
        try:
            pages.append(int(href.split("page=")[-1]))
        except ValueError:
            pass

    return max(pages) if pages else 1


def scrape_page(page_num: int, fetcher: StealthyFetcher) -> list:  # ← session → fetcher
    url = f"{LISTING_URL}&page={page_num}"

    try:
        page = fetcher.fetch(url, timeout=30)

        if page.status != 200:
            print(f"Page {page_num}: HTTP {page.status}")
            return []

        soup = BeautifulSoup(page.content, "html.parser")
        cards = soup.find_all("qs-product-card-v2")

        results = []

        for card in cards:

            a_tag = card.find("a", href=lambda h: h and "/product/" in h)

            if not a_tag:
                continue

            href = a_tag["href"]

            if href.startswith("/"):
                href = "https://qatarsale.com" + href

            is_new = bool(
                card.find(
                    "div",
                    class_=lambda c: c and "ribbon-classic" in c and "new" in c
                )
            )

            is_sold = bool(
                card.find(
                    "div",
                    class_=lambda c: c and "ribbon-classic" in c and "sold" in c
                )
            )

            is_expired = bool(
                card.find(
                    lambda tag: (
                        tag.name == "p"
                        and "منتهي" in tag.get_text(strip=True)
                    )
                )
            )

            results.append({
                "product_url": href,
                "is_new": is_new,
                "is_sold": is_sold,
                "is_expired": is_expired,
            })

        print(
            f"Page {page_num}: "
            f"{len(results)} listings "
            f"(new={sum(r['is_new'] for r in results)}, "
            f"sold={sum(r['is_sold'] for r in results)}, "
            f"expired={sum(r['is_expired'] for r in results)})"
        )

        return results

    except Exception as e:
        print(f"Page {page_num}: Error - {e}")
        return []


def run(start_page: int, end_page: int):

    StealthyFetcher.configure(auto_match=False)
    fetcher = StealthyFetcher()

    all_results = []

    for page_num in range(start_page, end_page + 1):
        results = scrape_page(page_num, fetcher)  
        all_results.extend(results)
        if page_num < end_page:
            time.sleep(random.uniform(2, 4))

    df = pd.DataFrame(all_results)

    if not df.empty:
        df = df.drop_duplicates(subset=["product_url"])

    filename = f"cars_for_sale_monitor_{start_page}_{end_page}.csv"

    df.to_csv(
        filename,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n==========================")
    print(f"Pages      : {start_page}-{end_page}")
    print(f"Rows       : {len(df)}")
    print(f"Output File: {filename}")
    print("==========================\n")

    return df


if __name__ == "__main__":
    start_page = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_page = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    run(start_page, end_page)
