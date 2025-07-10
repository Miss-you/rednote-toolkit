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
        """Fills the note's main content."""
        try:
            content_selector = "div.ProseMirror"
            content_element = self.page.locator(content_selector)
            await expect(content_element).to_be_visible(timeout=10000)
            await content_element.click() # Focus the editor
            await content_element.type(content)
            return True
        except Exception as e:
            print(f"Error filling content: {e}")
            return False

    async def fill_topics(self, topics: list[str]) -> bool:
        """Fills the note's topics."""
        if not topics:
            return True
            
        try:
            content_selector = "div.ProseMirror"
            content_element = self.page.locator(content_selector)
            await expect(content_element).to_be_visible(timeout=10000)
            
            for topic in topics:
                await content_element.type(f" #{topic} ")
            
            return True
        except Exception as e:
            print(f"Error filling topics: {e}")
            return False
