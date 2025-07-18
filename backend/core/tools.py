import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from PIL import Image, ImageDraw, ImageFont
import qrcode
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "datastore"))

# Ensure the datastore directory exists
DATABASE_PATH.mkdir(exist_ok=True)

# --- Database Tool ---

def create_memory(summary_data: Dict[str, Any]) -> str:
    """
    Saves a dictionary of summary data to a JSON file with a unique UUID.
    
    Args:
        summary_data: A dictionary containing the diary summary.

    Returns:
        The UUID string of the newly created memory file.
    """
    memory_uuid = str(uuid.uuid4())
    file_path = DATABASE_PATH / f"{memory_uuid}.json"
    
    # Add timestamp to the data
    summary_data["created_at"] = datetime.utcnow().isoformat()
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=4)
        
    print(f"Memory created: {file_path}")
    return memory_uuid

def read_memory(memory_uuid: str) -> Dict[str, Any]:
    """
    Reads a memory JSON file from the datastore.
    
    Args:
        memory_uuid: The UUID of the memory to read.

    Returns:
        A dictionary with the content of the memory file.
        
    Raises:
        FileNotFoundError: If the memory file does not exist.
    """
    file_path = DATABASE_PATH / f"{memory_uuid}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Memory with UUID {memory_uuid} not found.")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def update_memory(memory_uuid: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates a memory JSON file with new data.
    
    Args:
        memory_uuid: The UUID of the memory to update.
        update_data: A dictionary with the fields to update.

    Returns:
        The full, updated memory dictionary.
    """
    file_path = DATABASE_PATH / f"{memory_uuid}.json"
    memory_data = read_memory(memory_uuid)
    
    # Add updated timestamp
    update_data["updated_at"] = datetime.utcnow().isoformat()
    memory_data.update(update_data)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, ensure_ascii=False, indent=4)
        
    print(f"Memory updated: {file_path}")
    return memory_data

# --- Printer Tool ---

def _get_font_path(font_name="jf-openhuninn-2.1.ttf"):
    """Helper to find a font file, falling back to a default."""
    # This is a very basic check. For a real app, you might search system font paths.
    if os.path.exists(font_name):
        return font_name
    # On non-Windows, Arial may not be available.
    # A more robust solution would check the OS and look in standard font dirs.
    # For now, we return None to let Pillow use its default.
    print(f"Warning: Font '{font_name}' not found. Using Pillow's default font.")
    return None

def generate_card_image(date_str: str, short_summary: str, qr_data: str, output_path: str) -> str:
    """
    Generates a card image with date, summary, and a QR code.

    Args:
        date_str: The date to display on the card.
        short_summary: The short, poetic summary.
        qr_data: The data to encode in the QR code (e.g., a URL to the memory).
        output_path: The file path to save the generated image.

    Returns:
        The path where the image was saved.
    """
    # Create a new image
    width, height = 1080, 720
    bg_color = "#FDF6E3"  # Creamy beige
    image = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)

    # Load fonts
    try:
        font_path = _get_font_path()
        date_font = ImageFont.truetype(font_path, 48) if font_path else ImageFont.load_default()
        summary_font = ImageFont.truetype(font_path, 72) if font_path else ImageFont.load_default()
    except IOError:
        print("Defaulting to built-in font due to loading error.")
        date_font = ImageFont.load_default()
        summary_font = ImageFont.load_default()
    
    text_color = "#333333" # Dark grey

    # Draw text
    draw.text((60, 60), date_str, font=date_font, fill=text_color)
    # Simple word wrapping for the summary
    wrapped_summary = ""
    line = ""
    # A very basic wrapper, assumes around 15 chars fit on a line.
    for word in short_summary.split():
        if len(line + word) < 18:
            line += word + " "
        else:
            wrapped_summary += line + "\n"
            line = word + " "
    wrapped_summary += line
    draw.text((60, 200), wrapped_summary, font=summary_font, fill=text_color, spacing=15)

    # Generate and paste QR code
    qr_img = qrcode.make(qr_data, box_size=8, border=2)
    qr_img = qr_img.resize((250, 250))
    image.paste(qr_img, (780, 470))

    # Save the image
    image.save(output_path)
    print(f"Card image saved to: {output_path}")
    return output_path

# --- Light Control Tool Placeholder ---

# The actual LightControlTool will need access to the WebSocket manager.
# It will be fully implemented in main.py or passed in during initialization.
def set_light_effect(effect_name: str):
    """
    Placeholder for the light control tool. This will be connected
    to the WebSocket manager in the main application file.
    """
    print(f"[LightControlTool] Setting effect to: {effect_name}")
    # In the final implementation, this will call a method on the WebSocket manager.
    pass

class LightControlTool:
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager

    async def set_light_effect(self, effect_name: str, is_mode: bool = False):
        """
        Sends a light effect command to all connected projector clients.
        """
        if is_mode:
            message = {"type": "SET_MODE", "payload": {"mode": effect_name}}
        else:
            message = {"type": "SET_EMOTION", "payload": {"emotion": effect_name}}
        
        await self.websocket_manager.broadcast(message)
        print(f"Sent light effect '{effect_name}' to projectors.") 