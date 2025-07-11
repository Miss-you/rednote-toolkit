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

    async def publish_note(self, note: RedNote, auto_publish: bool = True) -> RedPublishResult:
        """Publishes a note following the correct sequence.
        
        Args:
            note: The note to publish.
            auto_publish: Whether to automatically click the publish button. If False, 
                         the process will stop before final submission for manual confirmation.
        """
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

            # Try to fill topics, but don't fail the entire process if it fails
            if not await self.filler.fill_topics(note.topics):
                print(f"警告: 话题填写失败，但继续发布流程。话题内容: {note.topics}")
                # Continue with the publishing process despite topics failure

            # 4. Submit the note.
            return await self._submit_note(note, auto_publish)

        except Exception as e:
            return RedPublishResult(success=False, message=f"An error occurred: {e}", note_title=note.title)

    async def _navigate_to_publish_page(self):
        """Navigates to the publish page."""
        publish_url = "https://creator.xiaohongshu.com/publish/publish"
        await self.page.goto(publish_url)
        # Wait for the title input to be visible as a sign that the page has loaded
        publish_page_locator = self.page.locator(
                "//*[text()='上传图文'] | "
                "//*[text()='上传视频']"
            )
            
        await expect(publish_page_locator.first).to_be_visible(timeout=15000)
        print("Publish page loaded")


    async def _submit_note(self, note: RedNote, auto_publish: bool) -> RedPublishResult:
        """Submits the note and waits for a success message."""
        try:
            # Save a snapshot right before the final click for debugging.
            await self._save_debug_info("final_publish_click")

            # This powerful XPath locator finds the button by its content, ignoring comments and whitespace.
            publish_button = self.page.locator("//button[.//span[normalize-space(.) = '发布']]")
            
            # 根据发布模式调整等待时间
            if auto_publish:
                wait_time = 10000  # 自动发布模式等待10秒
                print("Waiting 10 seconds for uploads to finalize...")
            else:
                wait_time = 3000   # 手动确认模式等待3秒
                print("Waiting 3 seconds for uploads to finalize...")
            
            await self.page.wait_for_timeout(wait_time)
            
            # Ensure the publish button is enabled
            await expect(publish_button).to_be_enabled(timeout=10000)
            
            if not auto_publish:
                print("内容已准备完毕，发布按钮已启用。")
                print("auto_publish=False，等待手动确认发布...")
                print("请在10分钟内手动点击发布按钮完成发布")
                
                # Wait for the "发布成功" success message to appear within 10 minutes
                print("等待手动发布确认，最长等待10分钟...")
                try:
                    success_locator = self.page.locator("//*[contains(text(), '发布成功')]")
                    await expect(success_locator).to_be_visible(timeout=600000)  # 10 minutes = 600,000ms
                    
                    print("检测到发布成功确认消息！")
                    return RedPublishResult(
                        success=True, 
                        message="手动发布成功。", 
                        note_title=note.title,
                        final_url=self.page.url
                    )
                except Exception as e:
                    print("10分钟内未检测到发布成功消息，可能是超时或用户未完成发布")
                    return RedPublishResult(
                        success=False, 
                        message="等待手动发布超时，10分钟内未检测到发布成功消息。", 
                        note_title=note.title,
                        final_url=self.page.url
                    )
            
            print("Attempting to click the final publish button...")
            await publish_button.click()
            
            # Wait for the "发布成功" success message to appear. This is the most reliable indicator.
            print("Waiting for '发布成功' confirmation message...")
            success_locator = self.page.locator("//*[contains(text(), '发布成功')]")
            await expect(success_locator).to_be_visible(timeout=30000)

            print("Confirmation message received. Note published successfully.")
            return RedPublishResult(success=True, message="Note published successfully.", note_title=note.title, final_url=self.page.url)
        except Exception as e:
            print(f"Failed to submit note or confirm success. Check 'debug_final_publish_click.html' and '.png' for details.")
            return RedPublishResult(success=False, message=f"Failed to submit note: {e}", note_title=note.title)

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
