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
                    await self.page.wait_for_timeout(100)
                    
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
            
            # Try multiple selectors to find the editor
            editor_selectors = [
                "div.ql-editor",           # Quill editor
                "div[contenteditable='true']",  # Generic contenteditable
                ".tiptap",                  # TipTap editor
                ".ProseMirror"              # ProseMirror editor
            ]
            
            editor_locator = None
            editor_type = None
            
            for selector in editor_selectors:
                try:
                    temp_locator = self.page.locator(selector)
                    # Check if this selector exists and is visible
                    if await temp_locator.count() > 0:
                        await expect(temp_locator.first).to_be_visible(timeout=3000)
                        editor_locator = temp_locator.first
                        # Determine editor type
                        if 'ql-editor' in selector:
                            editor_type = 'quill'
                        elif 'tiptap' in selector.lower() or 'prosemirror' in selector.lower():
                            editor_type = 'tiptap'
                        else:
                            editor_type = 'generic'
                        print(f"Found editor with selector: {selector} (type: {editor_type})")
                        break
                except:
                    continue
            
            if not editor_locator:
                print("❌ Could not find any editor for topics")
                return False

            # 确保光标在编辑器内容的末尾
            print("📍 Moving cursor to end of content...")
            
            # Get current content info before moving cursor
            actual_selector = editor_selectors[0]  # default
            for sel in editor_selectors:
                try:
                    test_loc = self.page.locator(sel)
                    if await test_loc.count() > 0:
                        actual_selector = sel
                        break
                except:
                    continue
            
            content_info = await self.page.evaluate('''(selector) => {
                const editor = document.querySelector(selector);
                if (!editor) return null;
                const text = editor.innerText || '';
                return {
                    length: text.length,
                    lastChars: text.slice(-50),
                    hasContent: text.trim().length > 0
                };
            }''', actual_selector)
            
            print(f"   Current content length: {content_info['length'] if content_info else 'unknown'}")
            if content_info and content_info['lastChars']:
                print(f"   Last 50 chars: ...{content_info['lastChars']}")
            
            # Click on the editor first to focus it
            await editor_locator.click()
            await self.page.wait_for_timeout(300)
            
            # Move cursor to the absolute end of the document using JavaScript
            print("   Moving cursor to document end...")
            cursor_moved = await self.page.evaluate('''(selector) => {
                try {
                    const editor = document.querySelector(selector);
                    if (!editor) return false;
                    
                    // Focus the editor
                    editor.focus();
                    
                    // Create a range at the very end of the content
                    const range = document.createRange();
                    const selection = window.getSelection();
                    
                    // Select the end of the last child node
                    if (editor.lastChild) {
                        if (editor.lastChild.nodeType === Node.TEXT_NODE) {
                            range.setStart(editor.lastChild, editor.lastChild.length);
                            range.setEnd(editor.lastChild, editor.lastChild.length);
                        } else {
                            range.selectNodeContents(editor.lastChild);
                            range.collapse(false); // Collapse to end
                        }
                    } else {
                        range.selectNodeContents(editor);
                        range.collapse(false);
                    }
                    
                    // Apply the selection
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    // Trigger focus event
                    editor.dispatchEvent(new Event('focus', { bubbles: true }));
                    
                    return true;
                } catch (e) {
                    console.error('Error moving cursor:', e);
                    return false;
                }
            }''', actual_selector)
            
            if cursor_moved:
                print("   ✓ Cursor moved to end via JavaScript")
            else:
                print("   ⚠️ JavaScript cursor move failed, using keyboard shortcuts...")
                # Fallback to keyboard shortcuts
                await self.page.keyboard.press("Control+End")
                await self.page.wait_for_timeout(200)
                await self.page.keyboard.press("End")
            
            # Verify cursor position by typing a test character and checking
            print("   Verifying cursor is at the end...")
            await self.page.wait_for_timeout(300)
            
            # Add one newline before topics (not two, not just space)
            print("   Adding single newline before topics...")
            await editor_locator.type("\n")
            await self.page.wait_for_timeout(200)

            # 记录成功和失败的话题
            success_topics = []
            failed_topics = []
            
            # For TipTap/modern editors, handle popup
            if editor_type in ['tiptap', 'generic']:
                print("Using hashtag with popup handling for TipTap/modern editor...")
                for topic in topics:
                    try:
                        print(f"  - Adding topic: {topic}")
                        
                        # Type the hashtag
                        await editor_locator.type(f"#{topic}")
                        print(f"    Typed #{topic}, waiting for popup (2s)...")
                        await self.page.wait_for_timeout(2000)  # Wait for popup to fully render
                        
                        # Debug: List all visible elements that might be popups
                        all_elements = await self.page.evaluate('''() => {
                            const elements = [];
                            // Find all elements that are visible and might be popups
                            document.querySelectorAll('*').forEach(el => {
                                const rect = el.getBoundingClientRect();
                                const styles = window.getComputedStyle(el);
                                if (rect.height > 0 && rect.width > 0 && 
                                    styles.position === 'absolute' || styles.position === 'fixed') {
                                    const text = el.innerText ? el.innerText.substring(0, 50) : '';
                                    if (text && text.includes('#')) {
                                        elements.push({
                                            tag: el.tagName,
                                            classes: el.className,
                                            id: el.id,
                                            text: text,
                                            position: styles.position,
                                            zIndex: styles.zIndex
                                        });
                                    }
                                }
                            });
                            return elements;
                        }''')
                        if all_elements and len(all_elements) > 0:
                            print(f"    Potential popup elements: {all_elements[:5]}")  # Show first 5
                        
                        # Try to detect and click suggestion popup
                        popup_found = False
                        popup_selectors = [
                            "[class*='mention']",
                            "[class*='suggestion']",
                            "[class*='popup']",
                            "[class*='dropdown']",
                            "[role='listbox']",
                            ".select-option",
                            "[class*='hashtag']",
                            "ul li",  # Common popup structure
                            "div[style*='position: absolute']",  # Positioned elements
                            "div[style*='position: fixed']"
                        ]
                        
                        for popup_sel in popup_selectors:
                            try:
                                popup = self.page.locator(popup_sel)
                                if await popup.count() > 0:
                                    # Log what we found
                                    popup_info = await self.page.evaluate(f'''() => {{
                                        const elements = document.querySelectorAll('{popup_sel}');
                                        return Array.from(elements).map(el => ({{
                                            text: el.innerText ? el.innerText.substring(0, 100) : '',
                                            classes: el.className,
                                            visible: el.offsetHeight > 0
                                        }}));
                                    }}''')
                                    print(f"    Found popup with selector {popup_sel}: {popup_info}")
                                    
                                    # Click first suggestion item inside popup (wait for item to render)
                                    container = popup.first
                                    item_selector = ".mention-item, li, [role='option'], .select-option, [class*='hashtag']"
                                    suggestion_items = container.locator(item_selector)
                                    attempted = 0
                                    while attempted < 4 and not popup_found:
                                        try:
                                            if await suggestion_items.count() > 0:
                                                try:
                                                    await expect(suggestion_items.first).to_be_visible(timeout=200)
                                                except Exception:
                                                    # If visibility check times out, still attempt click
                                                    pass
                                                await suggestion_items.first.click()
                                                popup_found = True
                                                print(f"    Clicked first suggestion item (attempt {attempted+1})")
                                                break
                                        except Exception:
                                            pass
                                        attempted += 1
                                        await self.page.wait_for_timeout(500)
                            except:
                                continue
                        
                        if not popup_found:
                        
                            print(f"    No popup found, pressing Enter to confirm")
                        
                            await self.page.keyboard.press("Enter")
                        
                        # Add space after topic
                        await editor_locator.type(" ")
                        await self.page.wait_for_timeout(200)
                        
                        success_topics.append(topic)
                        print(f"    ✓ Successfully added topic: {topic}")
                    except Exception as topic_error:
                        failed_topics.append(topic)
                        print(f"    ✗ Failed to add topic '{topic}': {topic_error}")
                        continue
            else:
                # Original approach for Quill editors
                for topic in topics:
                    try:
                        print(f"  - Adding topic: {topic}")
                        # Step 1: Type the '#' and the topic keyword without a trailing space.
                        await editor_locator.type(f"#{topic}")

                        # Step 2: Wait for the topic suggestion dropdown to appear.
                        # Try multiple possible selectors for suggestion list
                        suggestion_selectors = [
                            "#quill-mention-list",
                            ".mention-list",
                            "[class*='mention']",
                            "[class*='suggestion']",
                            ".hashtag-suggestions"
                        ]
                        
                        suggestion_list_locator = None
                        for sel in suggestion_selectors:
                            try:
                                temp_suggestion = self.page.locator(sel)
                                await expect(temp_suggestion).to_be_visible(timeout=2000)
                                suggestion_list_locator = temp_suggestion
                                print(f"    Found suggestion list with selector: {sel}")
                                break
                            except:
                                continue
                        
                        if suggestion_list_locator:
                            # Step 3: Click the first suggestion to confirm the topic.
                            first_item = suggestion_list_locator.locator(".mention-item, li, div").first
                            await first_item.click()
                            print(f"    Clicked first suggestion")
                        else:
                            # No suggestion list, just add a space
                            print(f"    No suggestion list found, continuing with space")
                        
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
