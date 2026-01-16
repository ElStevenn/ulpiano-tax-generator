"""
OpenAI Vision client for document analysis and structured data extraction.
"""

import json
from typing import TypeVar, Type
from openai import OpenAI
from pydantic import BaseModel

from ..config import config
from ..utils.image_utils import encode_image_to_base64, get_mime_type

T = TypeVar("T", bound=BaseModel)


class OpenAIVisionClient:
    """
    Client for interacting with OpenAI's Vision API.
    
    Provides methods for analyzing images and extracting structured data
    from documents using GPT-4 Vision capabilities.
    """
    
    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        Initialize the OpenAI Vision client.
        
        Args:
            api_key: OpenAI API key (defaults to config value)
            model: Model to use (defaults to config value, e.g., 'gpt-4o')
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = model or config.OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def analyze_image(self, image_bytes: bytes, prompt: str) -> str:
        """
        Analyze an image with a text prompt.
        
        Args:
            image_bytes: Raw image bytes
            prompt: Text prompt describing what to analyze
            
        Returns:
            Text response from the model
        """
        base64_image = encode_image_to_base64(image_bytes)
        mime_type = get_mime_type(image_bytes)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096
        )
        
        return response.choices[0].message.content or ""
    
    def analyze_multiple_images(
        self, 
        images: list[tuple[str, bytes]], 
        prompt: str
    ) -> str:
        """
        Analyze multiple images with a single prompt.
        
        Args:
            images: List of (label, image_bytes) tuples
            prompt: Text prompt describing what to analyze
            
        Returns:
            Text response from the model
        """
        content = [{"type": "text", "text": prompt}]
        
        for label, image_bytes in images:
            base64_image = encode_image_to_base64(image_bytes)
            mime_type = get_mime_type(image_bytes)
            
            # Add label as text before each image
            content.append({
                "type": "text",
                "text": f"\n[{label}]:"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            })
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096
        )
        
        return response.choices[0].message.content or ""
    
    def extract_structured(
        self, 
        image_bytes: bytes, 
        schema: Type[T],
        additional_instructions: str = ""
    ) -> T:
        """
        Extract structured data from an image according to a Pydantic schema.
        
        Args:
            image_bytes: Raw image bytes
            schema: Pydantic model class defining the expected structure
            additional_instructions: Extra instructions for extraction
            
        Returns:
            Instance of the schema populated with extracted data
        """
        schema_json = schema.model_json_schema()
        
        prompt = f"""Extract the following information from this document image.
Return the data as a valid JSON object matching this schema:

{json.dumps(schema_json, indent=2)}

{additional_instructions}

Important:
- Extract only the information visible in the document
- Use null for fields that cannot be determined
- For dates, use ISO format (YYYY-MM-DD)
- Be precise and accurate with the extracted values
- Return ONLY the JSON object, no additional text
"""
        
        base64_image = encode_image_to_base64(image_bytes)
        mime_type = get_mime_type(image_bytes)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=4096
        )
        
        response_text = response.choices[0].message.content or "{}"
        data = json.loads(response_text)
        
        return schema.model_validate(data)
    
    def extract_structured_from_multiple(
        self,
        images: list[tuple[str, bytes]],
        schema: Type[T],
        additional_instructions: str = ""
    ) -> T:
        """
        Extract structured data from multiple images according to a Pydantic schema.
        
        Args:
            images: List of (label, image_bytes) tuples
            schema: Pydantic model class defining the expected structure
            additional_instructions: Extra instructions for extraction
            
        Returns:
            Instance of the schema populated with extracted data
        """
        # Build a simple field list from schema instead of full JSON schema
        fields_info = self._get_fields_description(schema)
        
        prompt = f"""You are a document data extraction assistant. Extract information from the provided document images.

{additional_instructions}

Return a JSON object with these exact fields:
{fields_info}

CRITICAL RULES:
- Extract ACTUAL DATA from the images, not field descriptions
- Use null for fields you cannot find in the images
- Dates must be in YYYY-MM-DD format (e.g., "2003-02-19")
- Return ONLY the JSON object with extracted values
"""
        
        content = [{"type": "text", "text": prompt}]
        
        for label, image_bytes in images:
            base64_image = encode_image_to_base64(image_bytes)
            mime_type = get_mime_type(image_bytes)
            
            content.append({
                "type": "text",
                "text": f"\n[{label}]:"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            })
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            max_tokens=4096
        )
        
        response_text = response.choices[0].message.content or "{}"
        data = json.loads(response_text)
        
        return schema.model_validate(data)
    
    def _get_fields_description(self, schema: Type[BaseModel]) -> str:
        """
        Get a simple description of fields for the prompt.
        
        Args:
            schema: Pydantic model class
            
        Returns:
            String describing the fields
        """
        lines = []
        for field_name, field_info in schema.model_fields.items():
            annotation = field_info.annotation
            description = field_info.description or ""
            
            # Simplify type annotation to string
            type_str = str(annotation).replace("typing.", "").replace("<class '", "").replace("'>", "")
            
            if description:
                lines.append(f'- "{field_name}": {type_str} - {description}')
            else:
                lines.append(f'- "{field_name}": {type_str}')
        
        return "\n".join(lines)
    
    def classify_document(self, image_bytes: bytes, document_types: list[str]) -> str:
        """
        Classify a document image into one of the provided types.
        
        Args:
            image_bytes: Raw image bytes
            document_types: List of possible document type names
            
        Returns:
            The identified document type (or "unknown")
        """
        types_list = ", ".join(document_types)
        
        prompt = f"""Analyze this document image and identify its type.
        
Possible document types: {types_list}, unknown

Respond with ONLY the document type name (one of the options above), nothing else.
If you cannot identify the document type, respond with "unknown".
"""
        
        result = self.analyze_image(image_bytes, prompt)
        result = result.strip().lower()
        
        # Validate the response is one of the expected types
        if result in document_types or result == "unknown":
            return result
        
        # Try to find a partial match
        for doc_type in document_types:
            if doc_type in result:
                return doc_type
        
        return "unknown"
