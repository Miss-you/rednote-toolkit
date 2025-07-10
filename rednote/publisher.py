from playwright.async_api import Page, expect
from .models import RedNote, RedPublishResult
from .uploader import Uploader
from .filler import Filler

class Publisher:
    """Publishes a Xiaohongshu note."""
    def __init__(self, page: Page):
        self.page = page
        self.uploader = Uploader(page)
        self.filler = Filler(page)

    async def publish_note(self, note: RedNote) -> RedPublishResult:
        """Publishes a note following the correct sequence."""
        try:
            # 1. Navigate to the publish page first.
            await self._navigate_to_publish_page()

            # 2. Handle file uploads.
            files_to_upload = note.images or note.videos
            if files_to_upload:
                file_type = "image" if note.images else "video"
                print(f"Uploading {len(files_to_upload)} files of type {file_type}")
                if not await self.uploader.upload_files(files_to_upload, file_type):
                    return RedPublishResult(success=False, message="File upload failed.", note_title=note.title)

            # 3. Fill in the text content after files are handled.
            if not await self.filler.fill_title(note.title):
                return RedPublishResult(success=False, message="Failed to fill title.", note_title=note.title)

            if not await self.filler.fill_content(note.content):
                return RedPublishResult(success=False, message="Failed to fill content.", note_title=note.title)

            if not await self.filler.fill_topics(note.topics):
                return RedPublishResult(success=False, message="Failed to fill topics.", note_title=note.title)

            # 4. Submit the note.
            return await self._submit_note(note)

        except Exception as e:
            return RedPublishResult(success=False, message=f"An error occurred: {e}", note_title=note.title)

    async def _navigate_to_publish_page(self):
        """Navigates to the publish page."""
        publish_url = "https://creator.xiaohongshu.com/publish/publish"
        await self.page.goto(publish_url)
        # Wait for the title input to be visible as a sign that the page has loaded
        await expect(self.page.locator('input[placeholder*="填写标题"]')).to_be_visible(timeout=15000)


    async def _submit_note(self, note: RedNote) -> RedPublishResult:
        """Submits the note."""
        try:
            # The selector for the publish button might need to be adjusted.
            # Using a more generic selector based on text content.
            publish_button = self.page.locator('button:has-text("发布")')
            await publish_button.click()
            
            # Wait for a success indicator. This could be a URL change,
            # or a "published successfully" message.
            # For now, we'll wait for a reasonable time, but a more robust
            # solution would be to wait for a specific element.
            await self.page.wait_for_timeout(5000)

            return RedPublishResult(success=True, message="Note published successfully.", note_title=note.title, final_url=self.page.url)
        except Exception as e:
            return RedPublishResult(success=False, message=f"Failed to submit note: {e}", note_title=note.title)
