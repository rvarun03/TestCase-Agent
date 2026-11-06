import asyncio
import json

from app.services.website_crawler import crawl_website


async def main():

    pages_data = await crawl_website(
        "https://qaoncloud.com/",
        max_pages=10
    )

    with open(
        "website_analysis.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            pages_data,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("PAGES ANALYZED:", len(pages_data))


if __name__ == "__main__":
    asyncio.run(main())