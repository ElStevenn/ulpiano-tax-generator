"""
Image utility functions for processing document images.
"""

import base64
from io import BytesIO
from PIL import Image


def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Encode image bytes to base64 string for OpenAI API.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Base64 encoded string of the image
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def validate_image(image_bytes: bytes) -> bool:
    """
    Validate that the provided bytes represent a valid image.
    
    Args:
        image_bytes: Raw image bytes to validate
        
    Returns:
        True if valid image, False otherwise
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()
        return True
    except Exception:
        return False


def get_image_format(image_bytes: bytes) -> str | None:
    """
    Get the format of an image from its bytes.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Image format string (e.g., 'JPEG', 'PNG') or None if invalid
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        return image.format
    except Exception:
        return None


def get_mime_type(image_bytes: bytes) -> str:
    """
    Get the MIME type for an image based on its format.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        MIME type string (defaults to 'image/jpeg' if unknown)
    """
    format_to_mime = {
        "JPEG": "image/jpeg",
        "JPG": "image/jpeg",
        "PNG": "image/png",
        "GIF": "image/gif",
        "WEBP": "image/webp",
    }
    
    image_format = get_image_format(image_bytes)
    if image_format:
        return format_to_mime.get(image_format.upper(), "image/jpeg")
    return "image/jpeg"
