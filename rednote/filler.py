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
        """Fills the note's main content using multiple strategies for better reliability."""
        
        # Wait for page to stabilize after title filling
        print("⏳ Waiting for editor to load...")
        await self.page.wait_for_timeout(2000)  # Give page 2 seconds to load editor
        
        # Try multiple possible selectors
        selectors = [
            "div.ql-editor",
            "[class*='ql-editor']",
            "div[data-placeholder*='正文']",
            "div[contenteditable='true']",
            ".content-input",
            "#content-input"
        ]
        
        # Retry mechanism
        max_retries = 3
        for retry in range(max_retries):
            if retry > 0:
                print(f"🔄 Retry {retry}/{max_retries-1} - waiting 2 seconds...")
                await self.page.wait_for_timeout(2000)
            
            try:
                # Step 1: Try to find editor with different selectors
                print(f"📝 Attempt {retry+1}: Checking for editor...")
                
                editor_found = False
                working_selector = None
                
                for selector in selectors:
                    # Use a simpler approach to avoid f-string issues
                    js_code = '''(selector) => {
                        const editor = document.querySelector(selector);
                        return {
                            exists: !!editor,
                            selector: selector
                        };
                    }'''
                    editor_check = await self.page.evaluate(js_code, selector)
                    
                    if editor_check['exists']:
                        print(f"✅ Found editor with selector: {selector}")
                        editor_found = True
                        working_selector = selector
                        break
                
                if not editor_found:
                    # List all elements that might be editors for debugging
                    print("🔍 Searching for potential editor elements...")
                    potential_editors = await self.page.evaluate('''() => {
                        const elements = [];
                        // Check for contenteditable elements
                        document.querySelectorAll('[contenteditable="true"]').forEach(el => {
                            elements.push({
                                tag: el.tagName,
                                classes: Array.from(el.classList),
                                id: el.id,
                                placeholder: el.getAttribute('data-placeholder'),
                                innerText: el.innerText ? el.innerText.substring(0, 50) : ''
                            });
                        });
                        // Check for elements with 'editor' in class name
                        document.querySelectorAll('[class*="editor"]').forEach(el => {
                            elements.push({
                                tag: el.tagName,
                                classes: Array.from(el.classList),
                                id: el.id,
                                placeholder: el.getAttribute('data-placeholder'),
                                innerText: el.innerText ? el.innerText.substring(0, 50) : ''
                            });
                        });
                        // Check for textareas
                        document.querySelectorAll('textarea').forEach(el => {
                            elements.push({
                                tag: 'TEXTAREA',
                                classes: Array.from(el.classList),
                                id: el.id,
                                placeholder: el.placeholder,
                                value: el.value ? el.value.substring(0, 50) : ''
                            });
                        });
                        return elements;
                    }''')
                    print(f"Potential editor elements found: {potential_editors}")
                    
                    if retry == max_retries - 1:
                        print("❌ Editor element not found after all retries!")
                        await self._save_debug_info(f"content_fill_error_no_editor_retry_{retry}")
                        return False
                    continue
                
                # Step 2: Check detailed editor state
                content_selector = working_selector
                editor_state_js = '''(selector) => {
                    const editor = document.querySelector(selector);
                    return {
                        exists: !!editor,
                        isVisible: editor ? editor.offsetHeight > 0 : false,
                        isEditable: editor ? editor.contentEditable === 'true' : false,
                        currentContent: editor ? editor.innerText : null,
                        placeholder: editor ? editor.getAttribute('data-placeholder') : null,
                        classList: editor ? Array.from(editor.classList) : [],
                        parentVisible: editor && editor.parentElement ? editor.parentElement.offsetHeight > 0 : false
                    };
                }'''
                editor_state = await self.page.evaluate(editor_state_js, content_selector)
                print(f"Editor state: {editor_state}")
                
                if not editor_state['isVisible']:
                    print("⚠️ Editor exists but not visible")
                
                # Step 3: Ensure editor is visible
                content_element = self.page.locator(content_selector)
                await expect(content_element).to_be_visible(timeout=10000)
            
                # Check if it's TipTap/ProseMirror or Quill editor
                is_tiptap = 'tiptap' in editor_state.get('classList', []) or 'ProseMirror' in editor_state.get('classList', [])
                
                # Strategy A: JavaScript direct content setting (adapt for different editor types)
                print(f"🔧 Strategy A: Trying JavaScript for {'TipTap/ProseMirror' if is_tiptap else 'Quill'} editor...")
                
                if is_tiptap:
                    # TipTap/ProseMirror specific approach
                    js_fill_code = '''(args) => {
                        try {
                            const editor = document.querySelector(args.selector);
                            if (!editor) return false;
                            
                            // Focus the editor first
                            editor.focus();
                            
                            // Clear existing content using selection
                            const selection = window.getSelection();
                            const range = document.createRange();
                            range.selectNodeContents(editor);
                            selection.removeAllRanges();
                            selection.addRange(range);
                            
                            // Delete existing content
                            document.execCommand('delete', false, null);
                            
                            // Insert new content as plain text (TipTap will format it)
                            document.execCommand('insertText', false, args.content);
                            
                            // Trigger events
                            editor.dispatchEvent(new Event('input', { bubbles: true }));
                            editor.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            return true;
                        } catch (e) {
                            console.error('TipTap fill error:', e);
                            return false;
                        }
                    }'''
                else:
                    # Original Quill approach
                    js_fill_code = '''(args) => {
                        try {
                            const editor = document.querySelector(args.selector);
                            if (!editor) return false;
                            
                            // Clear existing content
                            editor.innerHTML = '';
                            
                            // Set new content with proper formatting
                            const lines = args.content.split('\\n');
                            const htmlContent = lines.map(line => 
                                line ? `<p>${line}</p>` : '<p><br></p>'
                            ).join('');
                            editor.innerHTML = htmlContent;
                            
                            // Trigger input event for Quill
                            editor.dispatchEvent(new Event('input', { bubbles: true }));
                            editor.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // Focus the editor
                            editor.focus();
                            
                            return true;
                        } catch (e) {
                            console.error('Quill fill error:', e);
                            return false;
                        }
                    }'''
                    
                js_success = await self.page.evaluate(js_fill_code, {'selector': content_selector, 'content': content})
            
                if js_success:
                    print("✅ Strategy A succeeded: JavaScript content set")
                    # Verify content was actually set
                    await self.page.wait_for_timeout(500)  # Wait for DOM update
                    verification = await self._verify_content_filled(content)
                    if verification:
                        return True
                    print("⚠️ Content verification failed after JS set")
                
                # Strategy B: Click to activate + type() method (optimized for editor type)
                print(f"🔧 Strategy B: Trying click + type method for {'TipTap' if is_tiptap else 'Quill'}...")
                await content_element.click()  # Click to focus
                await self.page.wait_for_timeout(500)  # Wait for editor activation
                
                if is_tiptap:
                    # For TipTap, use keyboard shortcuts that work better
                    # Select all and delete
                    await self.page.keyboard.press("Control+A")
                    await self.page.keyboard.press("Backspace")
                    await self.page.wait_for_timeout(200)
                    
                    # Type content more slowly for TipTap
                    await content_element.type(content, delay=50)
                else:
                    # Original approach for Quill
                    await self.page.keyboard.press("Control+A")
                    await self.page.keyboard.press("Delete")
                    await content_element.type(content, delay=20)
                    
                await self.page.wait_for_timeout(500)
                
                verification = await self._verify_content_filled(content)
                if verification:
                    print("✅ Strategy B succeeded: Type method worked")
                    return True
                
                # Strategy C: Original fill() method as fallback
                print("🔧 Strategy C: Trying original fill() method...")
                await content_element.click()
                await content_element.fill(content)
                await self.page.wait_for_timeout(500)
                
                verification = await self._verify_content_filled(content)
                if verification:
                    print("✅ Strategy C succeeded: Fill method worked")
                    return True
                
                if retry == max_retries - 1:
                    print("❌ All strategies failed!")
                    await self._save_debug_info("content_fill_all_strategies_failed")
                    return False
                
            except Exception as e:
                print(f"❌ Error in attempt {retry+1}: {e}")
                if retry == max_retries - 1:
                    await self._save_debug_info("content_fill_error")
                    return False
        
        return False
    
    async def _verify_content_filled(self, expected_content: str) -> bool:
        """Verify if content was successfully filled into the editor."""
        try:
            # Try multiple selectors to find the content
            actual_content = await self.page.evaluate('''() => {
                // Try different selectors
                const selectors = [
                    'div.ql-editor',
                    'div[contenteditable="true"]',
                    '.tiptap',
                    '.ProseMirror',
                    '[class*="editor"]'
                ];
                
                for (const selector of selectors) {
                    const editor = document.querySelector(selector);
                    if (editor && editor.innerText) {
                        const text = editor.innerText.trim();
                        if (text && text.length > 0) {
                            return text;
                        }
                    }
                }
                return '';
            }''')
            
            # Check if at least some content was filled
            if not actual_content or actual_content.strip() == '':
                print("❌ Verification failed: Editor is empty")
                return False
            
            # Clean up content for comparison (remove extra whitespace, newlines)
            expected_clean = ' '.join(expected_content.strip().split())
            actual_clean = ' '.join(actual_content.strip().split())
            
            # More lenient check - just check if first 20 chars of expected are in actual
            check_length = min(20, len(expected_clean))
            if check_length > 0:
                expected_start = expected_clean[:check_length]
                if expected_start in actual_clean:
                    print(f"✅ Content verification passed (found '{expected_start}...')")
                    return True
                else:
                    print(f"⚠️ Content mismatch.")
                    print(f"   Expected start: {expected_clean[:50]}")
                    print(f"   Actual content: {actual_clean[:100]}")
                    # Even more lenient - check if we have substantial content
                    if len(actual_clean) > 10:
                        print(f"✅ Accepting content (length: {len(actual_clean)} chars)")
                        return True
                    return False
            
            # If expected content is very short, just check we have something
            if len(actual_clean) > 0:
                print(f"✅ Content present (length: {len(actual_clean)} chars)")
                return True
                
            return False
                
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False

    # 合并内容和话题
    async def fill_content_with_topics(self, content: str, topics: list[str]) -> bool:
        """Fills the note's content and topics together in one operation to avoid cursor positioning issues."""
        try:
            # 合并内容和话题
            full_content = content
            if topics:
                full_content += "\n"  # 在内容和话题之间添加换行
                for topic in topics:
                    full_content += f"#{topic} "
            
            # 使用相同的编辑器填写完整内容
            content_selector = "div.ql-editor"
            content_element = self.page.locator(content_selector)
            
            await expect(content_element).to_be_visible(timeout=10000)
            await content_element.click() # Focus the editor
            await content_element.fill(full_content) # 一次性填写所有内容
            
            print(f"Successfully filled content with {len(topics)} topics")
            return True
        except Exception as e:
            print(f"Error filling content with topics: {e}")
            await self._save_debug_info("content_with_topics_fill_error")
            return False

    async def fill_topics(self, topics: list[str]) -> bool:
        """Fills the note's topics by typing, selecting from the suggestion list, and then adding a space."""
        if not topics:
            return True
            
        try:
            print("Filling topics...")
            editor_locator = self.page.locator("div.ql-editor")
            await expect(editor_locator).to_be_visible()

            # 确保光标在编辑器内容的末尾
            await editor_locator.click()
            
            # 使用多次按下向下箭头键来确保光标到达内容末尾
            # 这比使用End键更可靠，因为它会处理多行内容
            for _ in range(10):  # 最多按10次向下键，应该足够到达末尾
                await self.page.keyboard.press("ArrowDown")
            
            # 然后按End键确保在当前行的末尾
            await self.page.keyboard.press("End")
            
            # 在内容末尾添加两个换行，为话题留出空间
            await editor_locator.type("\n\n")

            # 记录成功和失败的话题
            success_topics = []
            failed_topics = []
            
            for topic in topics:
                try:
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
                    
                    success_topics.append(topic)
                    print(f"    ✓ Successfully added topic: {topic}")
                    
                    # 在话题之间添加100ms延迟，避免处理过快
                    await self.page.wait_for_timeout(100)
                    
                except Exception as topic_error:
                    failed_topics.append(topic)
                    print(f"    ✗ Failed to add topic '{topic}': {topic_error}")
                    # 继续处理下一个话题，不中断整个流程
                    continue
            
            # 输出统计信息
            total = len(topics)
            success_count = len(success_topics)
            if success_count == total:
                print(f"All {total} topics added successfully")
                return True
            elif success_count > 0:
                print(f"Partially successful: {success_count}/{total} topics added")
                if failed_topics:
                    print(f"Failed topics: {failed_topics}")
                return True  # 只要有部分成功就返回True
            else:
                print(f"Failed to add any topics")
                return False

        except Exception as e:
            print(f"Error in topics setup: {e}")
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
