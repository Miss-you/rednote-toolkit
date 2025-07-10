import os
import json
import re
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
        
        # Navigate to the creator home. If not logged in, this will redirect to the login page.
        await self.page.goto("https://creator.xiaohongshu.com/creator/home")
        
        print("Waiting for login and page load... Please log in if prompted.")

        try:
            # This robust locator waits for ANY of the key creator center elements to be visible.
            # This is much more reliable than checking for a single element.
            creator_home_locator = self.page.locator(
                "//button[contains(., '发布笔记')] | "
                "//*[text()='账号概览'] | "
                "//*[text()='笔记管理']"
            )
            
            await expect(creator_home_locator.first).to_be_visible(timeout=120000) # 2 minutes
            
            print("Login successful and creator page loaded.")
            
            # Save storage state for future sessions.
            storage = await self.page.context.storage_state()
            with open(self.storage_state_path, 'w') as f:
                json.dump(storage, f)
            print(f"Storage state saved to {self.storage_state_path}")

        except Exception as e:
            print(f"Login failed. The '发布笔记' button did not appear within the timeout.")
            print("Taking a screenshot and saving page content for analysis...")
            
            # Generate diagnostic files
            screenshot_path = "login_error_screenshot.png"
            html_path = "page_content_error.html"
            
            try:
                await self.page.screenshot(path=screenshot_path, full_page=True)
                print(f"Screenshot saved to: {screenshot_path}")
                
                page_content = await self.page.content()
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                print(f"Page HTML saved to: {html_path}")
                
            except Exception as diag_e:
                print(f"Could not save diagnostic files: {diag_e}")

            print(f"\nOriginal error: {e}")
            raise # Re-raise the exception to stop the script

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