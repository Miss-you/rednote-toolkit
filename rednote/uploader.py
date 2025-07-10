import os
from playwright.async_api import Page, expect

class Uploader:
    """Handles file uploads."""
    def __init__(self, page: Page):
        self.page = page

    async def upload_files(self, files: list[str], file_type: str) -> bool:
        """Uploads files using Playwright's file chooser."""
        if not files:
            return True

        # Verify that all files exist before starting the upload
        for file_path in files:
            if not os.path.exists(file_path):
                print(f"Error: File not found at {file_path}")
                return False

        try:
            # Wait for the file chooser to appear and set the files
            async with self.page.expect_file_chooser() as fc_info:
                # Click the upload area to open the file dialog.
                # This selector might need to be adjusted.
                # The button text is "上传图文"
                await self.page.locator('span:has-text("上传图文")').click()

            file_chooser = await fc_info.value
            await file_chooser.set_files(files)

            # Wait for the upload to complete. This is tricky.
            # We can look for the appearance of thumbnails of the uploaded images.
            # Let's assume a selector for the thumbnail container.
            poster_selector = "div.image-poster" if file_type == "image" else "div.video-poster"
            
            # Wait for each file to appear as a thumbnail
            for i in range(len(files)):
                await expect(self.page.locator(poster_selector).nth(i)).to_be_visible(timeout=30000)

            print(f"Successfully uploaded {len(files)} files.")
            return True
        except Exception as e:
            print(f"Error uploading files: {e}")
            return False
