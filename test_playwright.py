import asyncio

from collections import deque

from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse, urldefrag


def is_internal_link(base_url: str, link_url: str) -> bool:

    base_domain = urlparse(base_url).hostname
    link_domain = urlparse(link_url).hostname

    return base_domain == link_domain


async def main():

    website_url = "https://qaoncloud.com/"

    # STEP 2: Start with the homepage
    queue = deque([website_url])

    # STEP 3: Store pages we've already visited
    visited = set()

    max_pages = 10

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=False
        )

        try:

            # STEP 4: Continue while pages are waiting

            while queue and len(queue) < max_pages:

                # Get the next URL from the queue
                current_url = queue.popleft()

                # Skip pages already visited
                if current_url in visited:
                    continue

                # Skip external links
                if not is_internal_link(
                    website_url, current_url
                ):
                    continue

                # Mark this URL as visited
                visited.add(current_url)

                # Open a new browser tab
                page = await browser.new_page()

                try:

                    # STEP 5: Visit the page
                    response = await page.goto(
                        current_url,
                        wait_until="domcontentloaded",
                        timeout=15000
                    )

                    #check the final URL after redirects
                    if not is_internal_link(
                        website_url, page.url
                    ):

                        print("SKIPPED REDIRECT:", page.url)
                        continue

                    if response is None or response.status >= 400:
                        print("PAGE UNAVAILABLE:", current_url)
                        continue

                    print("\nVISITING:", page.url)
                    print("TITLE:", await page.title())

                    # STEP 6: Find links on the current page
                    links = page.locator("a[href]")

                    total_links = await links.count()

                    for index in range(total_links):

                        href = await links.nth(
                            index
                        ).get_attribute("href")

                        if not href:
                            continue

                        # Convert relative URL into full URL
                        full_url = urljoin(page.url, href)

                        # Remove #fragments
                        full_url = urldefrag(full_url).url

                        # Only collect internal website links
                        if not is_internal_link(
                            website_url, full_url
                        ):
                            continue

                        # Avoid adding duplicates
                        if (
                            full_url not in visited
                            and full_url not in queue
                        ):
                            queue.append(full_url)

                        print("PAGES WAITING:", len(queue))
                    print("PAGES VISITED:", len(visited))

                except Exception as error:
                    print("ERROR:", current_url, error)    

                finally:
                    await page.close()
        finally:
            await browser.close()

    # STEP 7: Print visited URLs
    print("\n========== CRAWL RESULT ==========")

    for url in visited:
        print(url)

    print("TOTAL VISITED:", len(visited))

asyncio.run(main())