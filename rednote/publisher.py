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

        # Check and close any promotional popups
        await self._close_promotional_popup()

    async def _close_promotional_popup(self):
        """检测并关闭可能出现的推广弹窗（如"试试文字配图吧"等）

        该方法会尝试查找并关闭弹窗。支持多种关闭方式：
        - 点击关闭按钮（如果有）
        - 按 ESC 键
        - 点击外部区域
        - 使用 JavaScript 隐藏弹窗
        """
        print("\n" + "="*60)
        print("🔍 开始检测推广弹窗...")
        print("="*60)

        try:
            # 等待短暂时间让弹窗完全加载（如果存在的话）
            print("⏳ 等待2秒，让弹窗完全加载...")
            await self.page.wait_for_timeout(2000)

            # 保存当前页面状态用于调试
            print("📸 保存当前页面状态（用于调试）...")
            try:
                await self.page.screenshot(path="debug_popup_detection.png", full_page=True)
                with open("debug_popup_detection.html", "w", encoding="utf-8") as f:
                    f.write(await self.page.content())
                print("✅ 调试文件已保存: debug_popup_detection.png / debug_popup_detection.html")
            except Exception as e:
                print(f"⚠️ 保存调试文件失败: {e}")

            # 首先检测是否存在 d-popover 弹窗（小红书特有的 popover）
            print("\n🔎 检测小红书 popover 弹窗...")
            popover_selectors = [
                ".d-popover",
                ".short-note-tooltip",
                "[class*='short-note-tooltip']",
            ]

            popover_found = False
            for selector in popover_selectors:
                popover = self.page.locator(selector)
                count = await popover.count()
                if count > 0:
                    print(f"✅ 检测到 popover 弹窗！选择器: {selector}, 数量: {count}")
                    popover_found = True
                    break

            if popover_found:
                print("\n📋 尝试多种方法关闭 popover 弹窗...")

                # 方法1: 点击「立即体验」按钮（小红书特有的关闭方式）
                print("\n[方法1] 尝试点击「立即体验」按钮...")
                try:
                    # 多种选择器尝试找到「立即体验」按钮
                    button_selectors = [
                        "button.short-note-rooltip-button",  # 注意拼写是 rooltip
                        "button:has-text('立即体验')",
                        ".short-note-tooltip button",
                        ".d-popover button:has-text('立即体验')",
                    ]

                    button_clicked = False
                    for btn_selector in button_selectors:
                        try:
                            button = self.page.locator(btn_selector)
                            count = await button.count()
                            print(f"   尝试选择器: {btn_selector}, 找到 {count} 个元素")

                            if count > 0:
                                is_visible = await button.first.is_visible(timeout=1000)
                                if is_visible:
                                    print(f"   ✅ 找到可见的「立即体验」按钮！")
                                    await button.first.click(timeout=3000)
                                    print(f"   🖱️ 已点击按钮")
                                    await self.page.wait_for_timeout(1000)
                                    button_clicked = True
                                    break
                        except Exception as e:
                            print(f"   ⚠️ 选择器 {btn_selector} 失败: {e}")
                            continue

                    if button_clicked:
                        # 检查弹窗是否已关闭
                        popover_after_click = self.page.locator(selector)
                        count_after = await popover_after_click.count()

                        if count_after == 0:
                            print("   ✅ 点击「立即体验」后弹窗已消失！")
                            await self.page.screenshot(path="debug_popup_after_close.png", full_page=True)
                            print("\n" + "="*60)
                            print("🎉 推广弹窗已成功关闭（点击「立即体验」），继续发布流程")
                            print("="*60 + "\n")
                            return True
                        else:
                            # 检查是否只是隐藏了
                            is_visible = await popover_after_click.first.is_visible(timeout=1000)
                            if not is_visible:
                                print("   ✅ 点击「立即体验」后弹窗已隐藏！")
                                await self.page.screenshot(path="debug_popup_after_close.png", full_page=True)
                                print("\n" + "="*60)
                                print("🎉 推广弹窗已成功关闭（点击「立即体验」），继续发布流程")
                                print("="*60 + "\n")
                                return True
                            else:
                                print("   ⚠️ 点击按钮后弹窗仍然可见，尝试其他方法...")
                    else:
                        print("   ❌ 未找到可点击的「立即体验」按钮")

                except Exception as e:
                    print(f"   ❌ 点击「立即体验」按钮失败: {e}")

                # 方法2: 按 ESC 键（备用方案）
                print("\n[方法2] 尝试按 ESC 键关闭...")
                try:
                    await self.page.keyboard.press("Escape")
                    await self.page.wait_for_timeout(500)

                    # 检查弹窗是否已关闭
                    popover_after_esc = self.page.locator(selector)
                    count_after_esc = await popover_after_esc.count()

                    if count_after_esc == 0:
                        print("   ✅ ESC 键成功关闭弹窗！")
                        await self.page.screenshot(path="debug_popup_after_close.png", full_page=True)
                        print("\n" + "="*60)
                        print("🎉 推广弹窗已成功关闭（ESC 键），继续发布流程")
                        print("="*60 + "\n")
                        return True
                    else:
                        # 检查弹窗是否不可见了（可能还在 DOM 中但隐藏了）
                        is_visible = await popover_after_esc.first.is_visible(timeout=1000)
                        if not is_visible:
                            print("   ✅ ESC 键成功隐藏弹窗（元素仍在 DOM 但不可见）！")
                            await self.page.screenshot(path="debug_popup_after_close.png", full_page=True)
                            print("\n" + "="*60)
                            print("🎉 推广弹窗已成功关闭（ESC 键），继续发布流程")
                            print("="*60 + "\n")
                            return True
                        else:
                            print("   ⚠️ ESC 键无效，弹窗仍然可见")
                except Exception as e:
                    print(f"   ❌ ESC 键方法失败: {e}")

                # 方法2: 使用 JavaScript 直接隐藏弹窗
                print("\n[方法2] 尝试使用 JavaScript 隐藏弹窗...")
                try:
                    js_code = """
                    const popover = document.querySelector('.d-popover, .short-note-tooltip, [class*="short-note-tooltip"]');
                    if (popover) {
                        // 尝试多种方式隐藏
                        popover.style.display = 'none';
                        popover.style.visibility = 'hidden';
                        popover.remove();  // 直接移除元素
                        return true;
                    }
                    return false;
                    """
                    result = await self.page.evaluate(js_code)
                    if result:
                        print("   ✅ JavaScript 成功移除弹窗元素！")
                        await self.page.wait_for_timeout(500)
                        await self.page.screenshot(path="debug_popup_after_close.png", full_page=True)
                        print("\n" + "="*60)
                        print("🎉 推广弹窗已成功关闭（JavaScript），继续发布流程")
                        print("="*60 + "\n")
                        return True
                    else:
                        print("   ⚠️ JavaScript 方法失败：未找到元素")
                except Exception as e:
                    print(f"   ❌ JavaScript 方法失败: {e}")

                # 方法3: 点击页面其他区域（尝试触发外部点击关闭）
                print("\n[方法3] 尝试点击页面其他区域关闭弹窗...")
                try:
                    # 点击页面左上角（通常是安全区域）
                    await self.page.click("body", position={"x": 10, "y": 10})
                    await self.page.wait_for_timeout(500)

                    # 检查弹窗是否已关闭
                    popover_after_click = self.page.locator(selector)
                    is_visible_after_click = await popover_after_click.first.is_visible(timeout=1000) if await popover_after_click.count() > 0 else False

                    if not is_visible_after_click:
                        print("   ✅ 点击外部区域成功关闭弹窗！")
                        await self.page.screenshot(path="debug_popup_after_close.png", full_page=True)
                        print("\n" + "="*60)
                        print("🎉 推广弹窗已成功关闭（外部点击），继续发布流程")
                        print("="*60 + "\n")
                        return True
                    else:
                        print("   ⚠️ 点击外部区域无效，弹窗仍然可见")
                except Exception as e:
                    print(f"   ❌ 点击外部区域方法失败: {e}")

                # 如果所有方法都失败了，记录警告但不中断流程
                print("\n⚠️ 所有关闭方法都失败了，但会继续尝试上传流程")
                print("   （弹窗可能不会影响后续操作）")
                return False
            else:
                # 没有检测到弹窗
                print("\n" + "="*60)
                print("ℹ️ 未检测到推广弹窗，继续正常流程")
                print("="*60 + "\n")
                return False

        except Exception as e:
            # 弹窗处理失败不应该影响主流程
            print("\n" + "="*60)
            print(f"⚠️ 弹窗检测过程中出现异常（不影响主流程）: {e}")
            print("="*60 + "\n")
            import traceback
            traceback.print_exc()
            return False

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
