from .browser import BrowserManager
from .publisher import Publisher
from .models import RedNote, RedPublishResult

class RedNoteClient:
    """A client for publishing notes to Xiaohongshu."""
    def __init__(self, storage_state_path: str):
        self.browser_manager = BrowserManager(storage_state_path)
        self.publisher = None

    async def __aenter__(self):
        await self.browser_manager.start_browser()
        print("Browser started")
        self.publisher = Publisher(self.browser_manager.get_page())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.browser_manager.close_browser()

    async def publish_note(self, note: RedNote) -> RedPublishResult:
        """
        Publishes a note to Xiaohongshu.

        Args:
            note: The note to publish.

        Returns:
            The result of the publishing attempt.
        """
        if not self.publisher:
            raise Exception("Client not initialized. Use 'async with' statement.")
            
        return await self.publisher.publish_note(note)