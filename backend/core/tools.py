import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from PIL import Image, ImageDraw, ImageFont
import qrcode
from dotenv import load_dotenv
import requests

# --- Load Environment Variables ---
load_dotenv()
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "datastore"))

# --- Hardware Gateway Configuration ---
# As per specification, printing is handled by the gateway on port 8002.
PRINTER_GATEWAY_URL = "http://localhost:8002"
# Other hardware commands (if any) are handled by the gateway on port 8001.
GENERAL_GATEWAY_URL = "http://localhost:8001"


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

# --- Card and Printer Tool ---

class CardAndPrinterTool:
    """
    A tool that handles the generation of the summary card image
    and triggers the physical printing job via the hardware gateway.
    """
    def __init__(self, card_output_dir: str = "generated_cards"):
        self.output_path = Path(card_output_dir)
        self.output_path.mkdir(exist_ok=True)
        print(f"CardAndPrinterTool initialized. Cards will be saved to '{self.output_path}'.")

    def _trigger_print_job(self) -> bool:
        """
        Sends a command to the hardware gateway to start the printing process.
        (This is a private method, the main entry point is `generate_and_print_card`)
        """
        try:
            url = f"{PRINTER_GATEWAY_URL}/hardware/command"
            payload = {"command": "PRINT_CARD"}
            response = requests.post(url, json=payload, timeout=5) # 5-second timeout
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            
            print(f"Successfully sent 'PRINT_CARD' command to hardware gateway. Response: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error: Could not send command to hardware gateway at {PRINTER_GATEWAY_URL}.")
            print(f"Please ensure the arduino_gateway.py service on port 8002 is running and accessible.")
            print(f"Details: {e}")
            return False

    def generate_and_print_card(self, date_str: str, short_summary: str, qr_data: str) -> str:
        """
        Generates the card image and then triggers the physical print job.
        
        Args:
            date_str: The date to display on the card.
            short_summary: The short, poetic summary.
            qr_data: The data to encode in the QR code (e.g., a URL).

        Returns:
            The path to the generated image file, or an empty string if printing failed.
        """
        # Step 1: Generate the image
        # Use a unique filename to avoid overwriting
        filename = f"memory_card_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_file_path = self.output_path / filename
        
        self._generate_card_image(date_str, short_summary, qr_data, str(output_file_path))

        # Step 2: Trigger the printer
        print("Image generated. Now attempting to trigger printer...")
        if self._trigger_print_job():
            print("Print job successfully triggered.")
            return str(output_file_path)
        else:
            print("Failed to trigger print job. The card image has been saved but not printed.")
            # Return path anyway, so the digital version exists
            return str(output_file_path)


    def _generate_card_image(self, date_str: str, short_summary: str, qr_data: str, output_path: str):
        """
        (Internal) Generates the card image itself.
        """
        # Create a new image
        width, height = 1080, 720
        bg_color = "#FDF6E3"  # Creamy beige
        image = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)

        font_name = "jf-openhuninn-2.1.ttf"

        try:
            date_font = ImageFont.truetype(font_name, 48)
            summary_font = ImageFont.truetype(font_name, 72)
        except IOError:
            print(f"Font '{font_name}' not found. Using Pillow's default font.")
            date_font = ImageFont.load_default()
            summary_font = ImageFont.load_default()
        
        text_color = "#333333" # Dark grey

        # Draw text
        draw.text((60, 60), date_str, font=date_font, fill=text_color)
        
        # Simple word wrapping for the summary
        wrapped_summary = ""
        line = ""
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