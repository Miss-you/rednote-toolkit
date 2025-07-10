import os
import json
import asyncio
from playwright.async_api import async_playwright, Page, Browser, Playwright, expect

class BrowserManager:
    """Manages the Playwright browser."""
    def __init__(self, storage_state_path: str):
        self.storage_state_path = storage_state_path
        self.p: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def start_browser(self, headless=False):
        """Creates and configures the Playwright browser, handling login."""
        self.p = await async_playwright().start()
        self.browser = await self.p.chromium.launch(headless=headless)
        
        context_args = {}
        if os.path.exists(self.storage_state_path):
            context_args['storage_state'] = self.storage_state_path

        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()
        
        await self.page.goto("https://creator.xiaohongshu.com/creator/home")

        try:
            # Quick check to see if we are already logged in.
            print("Checking for '发布笔记' button to verify login status...")
            await expect(self.page.get_by_role("button", name="发布笔记")).to_be_visible(timeout=10000)
            print("Logged in successfully using stored state.")
            return
        except Exception:
            print("Initial check failed. Proceeding to manual login.")

        # Not logged in, so let's guide the user through the login process.
        print("Redirecting to login page...")
        await self.page.goto("https://creator.xiaohongshu.com/login?source=&redirectReason=401&lastUrl=%252Fcreator%252Fhome")
        
        print("Please scan the QR code to log in. The script will automatically detect successful login.")

        try:
            # Wait for successful login by polling for either the URL change or the presence of the publish button.
            await self._wait_for_login_completion(timeout=120) # 2 minutes timeout
            
            print("Login successful and creator page loaded.")
            
            # Save storage state for future sessions.
            storage = await self.page.context.storage_state()
            with open(self.storage_state_path, 'w') as f:
                json.dump(storage, f)
            print(f"Storage state saved to {self.storage_state_path}")

        except Exception as e:
            print(f"Login failed after timeout or due to an error: {e}")
            print("Saving current page content to 'page_content_error.html' for analysis.")
            page_content = await self.page.content()
            with open("page_content_error.html", "w", encoding="utf-8") as f:
                f.write(page_content)
            raise  # Re-raise the exception to stop the script

    async def _wait_for_login_completion(self, timeout: int):
        """
        Waits for the user to log in by checking for navigation to the creator home
        or the appearance of a key element on the page.
        """
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Condition 1: Check if the URL is the creator home page.
                if "creator.xiaohongshu.com/creator/home" in self.page.url:
                    print("Login detected: Navigated to creator home page.")
                    # Even if URL matches, wait for the button to ensure the page is interactive
                    await expect(self.page.get_by_role("button", name="发布笔记")).to_be_visible(timeout=20000)
                    return

                # Condition 2: Check if the "发布笔记" button is visible (a strong indicator of being logged in)
                await expect(self.page.get_by_role("button", name="发布笔记")).to_be_visible(timeout=5000)
                print("Login detected: '发布笔记' button is visible.")
                return

            except Exception:
                # This is expected if the login is not yet complete.
                print(f"Waiting for login... (elapsed: {int(asyncio.get_event_loop().time() - start_time)}s)")
                await asyncio.sleep(5) # Wait 5 seconds before the next check.
        
        raise TimeoutError(f"Login was not completed within the {timeout} second timeout.")

    async def navigate_to(self, url: str):
        """Navigates the browser to a specific URL."""
        if self.page:
            await self.page.goto(url)

    async def close_browser(self):
        """Closes the browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.p:
            await self.p.stop()

    def get_page(self) -> Page:
        """Returns the Page instance."""
        if not self.page:
            raise Exception("Browser not started. Call start_browser() first.")
        return self.page
