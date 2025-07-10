import asyncio
from rednote.client import RedNoteClient
from rednote.models import XHSNote

async def main():
    """Main function to publish a note."""
    # IMPORTANT: Create a placeholder image file for testing if you don't have one.
    # For example:
    # from PIL import Image
    # img = Image.new('RGB', (600, 400), color = 'red')
    # img.save('placeholder.jpg')

    # Create a note
    note = XHSNote(
        title="My First Note via RedNote Toolkit",
        content="This is a test note published using the RedNote Toolkit.",
        # IMPORTANT: Replace with a real, absolute image path
        images=["./GvWVgMiaYAI0psE.jpeg"], 
        topics=["testing", "automation"]
    )

    # Publish the note
    storage_state_path = "storage_state.json"
    async with RedNoteClient(storage_state_path) as client:
        result = await client.publish_note(note)
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        print(f"URL: {result.final_url}")

if __name__ == "__main__":
    asyncio.run(main())