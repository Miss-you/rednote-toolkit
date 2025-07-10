from playwright.async_api import Page, expect

class Filler:
    """Fills the note's content."""
    def __init__(self, page: Page):
        self.page = page

    async def fill_title(self, title: str) -> bool:
        """Fills the note's title."""
        try:
            title_selector = "input[placeholder*='填写标题']"
            title_element = self.page.locator(title_selector)
            await expect(title_element).to_be_visible(timeout=10000)
            await title_element.fill(title)
            return True
        except Exception as e:
            print(f"Error filling title: {e}")
            return False

    async def fill_content(self, content: str) -> bool:
        """Fills the note's main content using the correct editor locator."""
        try:
            # This is the correct locator for the Quill editor used by Xiaohongshu.
            content_selector = "div.ql-editor"
            content_element = self.page.locator(content_selector)
            
            await expect(content_element).to_be_visible(timeout=10000)
            await content_element.click() # Focus the editor
            await content_element.fill(content) # Use fill for reliability
            return True
        except Exception as e:
            print(f"Error filling content: {e}")
            # Save debug info if it fails, to catch any future layout changes.
            await self._save_debug_info("content_fill_error")
            return False

    async def fill_topics(self, topics: list[str]) -> bool:
        """Fills the note's topics by typing, selecting from the suggestion list, and then adding a space."""
        if not topics:
            return True
            
        try:
            print("Filling topics...")
            editor_locator = self.page.locator("div.ql-editor")
            await expect(editor_locator).to_be_visible()

            for topic in topics:
                print(f"  - Adding topic: {topic}")
                # Step 1: Type the '#' and the topic keyword without a trailing space.
                await editor_locator.type(f"#{topic}")

                # Step 2: Wait for the topic suggestion dropdown to appear.
                suggestion_list_locator = self.page.locator("#quill-mention-list")
                await expect(suggestion_list_locator).to_be_visible(timeout=5000)

                # Step 3: Click the first suggestion to confirm the topic.
                await suggestion_list_locator.locator(".mention-item").first.click()
                
                # Step 4: After confirming, type a space to separate from the next content.
                await editor_locator.type(" ")

            return True
        except Exception as e:
            print(f"Error filling topics: {e}")
            # Save debug info if it fails, to catch any future layout changes.
            await self._save_debug_info("topics_fill_error")
            return False

    async def _save_debug_info(self, base_filename: str):
        """Saves a screenshot and HTML content for debugging."""
        screenshot_path = f"debug_{base_filename}.png"
        html_path = f"debug_{base_filename}.html"
        print(f"\n--- Saving debug info to {screenshot_path} and {html_path} ---")
        try:
            await self.page.screenshot(path=screenshot_path, full_page=True)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(await self.page.content())
            print("--- Debug info saved successfully. ---")
        except Exception as e:
            print(f"--- Failed to save debug info: {e} ---")
