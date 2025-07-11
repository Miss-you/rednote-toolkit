import asyncio
from rednote.client import RedNoteClient
from rednote.models import RedNote

async def main():
    """Main function to publish a note."""
    # IMPORTANT: Create a placeholder image file for testing if you don't have one.
    # For example:
    # from PIL import Image
    # img = Image.new('RGB', (600, 400), color = 'red')
    # img.save('placeholder.jpg')

    # Create a note
    note = RedNote(
        title="My First Note via RedNote Toolkit",
        content="This is a test note published using the RedNote Toolkit.",
        # IMPORTANT: Replace with a real, absolute image path
        images=["./GvWVgMiaYAI0psE.jpeg"], 
        topics=["testing", "automation"]
    )

    # Publish the note
    storage_state_path = "storage_state.json"
    client = RedNoteClient(storage_state_path)
    try:
        async with client:
            # 自动发布模式（默认）
            result = await client.publish_note(note)
            
            # 或者使用手动确认模式：
            # result = await client.publish_note(note, auto_publish=False)
            # 使用 auto_publish=False 时，程序会在最后一步停止，
            # 等待用户手动点击发布按钮进行二次确认
            
            print(f"Success: {result.success}")
            print(f"Message: {result.message}")
            print(f"URL: {result.final_url}")
    finally:
        # Explicitly close the browser to ensure cleanup,
        # even if some background tasks are lingering.
        print("Ensuring browser is closed...")
        await client.browser_manager.close_browser()
        print("Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())