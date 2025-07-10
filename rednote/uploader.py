import os
import re
from playwright.async_api import Page, expect

class Uploader:
    """Handles file uploads."""
    def __init__(self, page: Page):
        self.page = page

    async def upload_files(self, files: list[str], file_type: str) -> bool:
        """Uploads files by directly interacting with the hidden file input element."""
        if not files:
            return True

        for file_path in files:
            if not os.path.exists(file_path):
                print(f"Error: File not found at {file_path}")
                return False

        try:
            if file_type == "image":
                print("Switching to the '图文' tab...")
                await self.page.locator('div.creator-tab:has-text("上传图文"):not([style*="left: -9999px"])').click()
                
                print("Directly setting files on the hidden input element...")
                # This is the most robust way: find the hidden input and set files on it.
                input_locator = self.page.locator('input.upload-input[type="file"]')
                await input_locator.set_input_files(files)

            elif file_type == "video":
                print("Switching to the '视频' tab...")
                await self.page.locator('div.creator-tab:has-text("上传视频")').click()
                
                print("Directly setting files for video...")
                # Assuming a similar hidden input exists for videos
                video_input_locator = self.page.locator('input[type="file"][accept*="video"]')
                await video_input_locator.set_input_files(files)
            else:
                print(f"Error: Unknown file type '{file_type}'")
                return False

            # Wait for the upload to complete by checking for the editor interface to appear,
            # as suggested by the user. This is a much more robust signal.
            print("Waiting for editor to appear after upload...")
            editor_locator = self.page.locator(
                "//*[contains(text(), '正文内容')] | //*[contains(text(), '笔记预览')]"
            )
            await expect(editor_locator.first).to_be_visible(timeout=60000)

            print(f"Successfully uploaded {len(files)} files and editor is ready.")
            return True
        except Exception as e:
            # If something still goes wrong, save the final state for analysis.
            await self._save_debug_info("final_upload_error")
            print(f"An unexpected error occurred during file upload: {e}")
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
