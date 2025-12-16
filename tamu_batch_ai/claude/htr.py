import os
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import anthropic
import re
import csv
import PyPDF2

# Import new utilities
from ..config import model_config
from ..prompt_manager import prompt_manager
from ..parsers import ResponseParser


class ClaudeBase:
    """Base class for Claude API requests with common functionality."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to CLAUDE_API environment variable)
            model: Model to use (defaults to config.model_config.default_model)
        """
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("CLAUDE_API")
        )
        self.model = model or model_config.default_model

    def get_prompt(self, prompt_file: str, **kwargs) -> str:
        """Load and optionally render a prompt template.

        Args:
            prompt_file: Name of the prompt file (e.g., "htr.md" or "htr")
            **kwargs: Variables to substitute in the template

        Returns:
            Prompt text (rendered if kwargs provided)

        Examples:
            >>> base = ClaudeBase()
            >>> base.get_prompt("htr.md")
            >>> base.get_prompt("metadata", letter_text="Dear Sir...")
        """
        if kwargs:
            return prompt_manager.load_and_render(prompt_file, **kwargs)
        return prompt_manager.load_template(prompt_file)

    def encode_image(self, image_path: str) -> Tuple[str, str]:
        """Encode an image to base64 and determine its media type.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (base64_encoded_data, media_type)
        """
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        suffix = Path(image_path).suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_type_map.get(suffix, 'image/jpeg')

        return image_data, media_type

    def parse_response(self, response_text: str, format_hint: str = "auto") -> Dict:
        """Parse Claude API response in TOON or JSON format.

        Args:
            response_text: Raw response text from Claude
            format_hint: "toon", "json", or "auto" to detect

        Returns:
            Parsed dictionary
        """
        return ResponseParser.parse_response(response_text, format_hint)

    def save_json(self, data: Dict, output_path: str, include_timestamp: bool = True) -> str:
        """Save data as JSON file.

        Args:
            data: Dictionary to save
            output_path: Base output path (without extension)
            include_timestamp: Whether to add timestamp to filename

        Returns:
            Path to saved file
        """
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = f"{output_path}_{timestamp}.json"
        else:
            json_path = f"{output_path}.json"

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return json_path

    def calculate_cost(self, usage_data=None, model_name=None):
        """Calculate cost based on token usage and model.

        Args:
            usage_data (dict, optional): Token usage data with 'input_tokens' and 'output_tokens'.
                                       If None, uses self.last_response.usage
            model_name (str, optional): Model name. If None, uses self.model_used

        Returns:
            dict: Cost breakdown with input, output, and total costs in USD

        Raises:
            ValueError: If usage data or model name cannot be determined
        """
        # Updated pricing as of August 2025 (per million tokens)
        model_pricing = {
            # Claude 4 family
            "claude-4-opus": {
                "input": 15.00,
                "output": 75.00
            },
            "claude-4-sonnet": {
                "input": 3.00,
                "output": 15.00
            },
            "claude-sonnet-4-20250514": {  # Current Sonnet 4 model string
                "input": 3.00,
                "output": 15.00
            },

            # Claude 3.5 family
            "claude-3-5-sonnet-20241022": {
                "input": 3.00,
                "output": 15.00
            },
            "claude-3-5-sonnet-20240620": {
                "input": 3.00,
                "output": 15.00
            },
            "claude-3-5-haiku-20241022": {
                "input": 0.80,
                "output": 4.00
            },

            # Claude 3 family (legacy)
            "claude-3-opus-20240229": {
                "input": 15.00,
                "output": 75.00
            },
            "claude-3-sonnet-20240229": {
                "input": 3.00,
                "output": 15.00
            },
            "claude-3-haiku-20240307": {
                "input": 0.25,
                "output": 1.25
            }
        }

        # Determine usage data
        if usage_data is None:
            if hasattr(self, 'last_response') and self.last_response:
                usage_data = self.last_response.usage.__dict__
            else:
                raise ValueError("No usage data provided and no last_response available")

        # Determine model name
        if model_name is None:
            if hasattr(self, 'model_used') and self.model_used:
                model_name = self.model_used
            else:
                raise ValueError("No model name provided and no model_used available")

        # Check if model is supported
        if model_name not in model_pricing:
            available_models = list(model_pricing.keys())
            raise ValueError(f"Model '{model_name}' not found in pricing table. "
                           f"Available models: {available_models}")

        # Extract token counts
        input_tokens = usage_data.get('input_tokens', 0)
        output_tokens = usage_data.get('output_tokens', 0)

        if input_tokens == 0 and output_tokens == 0:
            raise ValueError("Both input_tokens and output_tokens are 0")

        # Calculate costs (pricing is per million tokens)
        pricing = model_pricing[model_name]
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        total_cost = input_cost + output_cost

        return {
            'model': model_name,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost_usd': round(input_cost, 6),
            'output_cost_usd': round(output_cost, 6),
            'total_cost_usd': round(total_cost, 6),
            'cost_per_token': {
                'input': pricing['input'] / 1_000_000,
                'output': pricing['output'] / 1_000_000
            }
        }

    def _store_response_data(self, response, model_name):
        """Helper method to store response data for cost calculation.

        Args:
            response: Anthropic API response object
            model_name (str): Name of the model used
        """
        self.last_response = response
        self.model_used = model_name


class ClaudePage(ClaudeBase):
    """A Class to Represent Pages as Claude Requests"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key, model)
        self.prompt = self.get_prompt("htr")

    def extract_text_with_claude(self, image_path: str) -> Tuple[str, Dict]:
        """Uses Claude AI to extract the contents of a handwritten document

        Args:
            image_path (str): The path to an image

        Returns:
            tuple: extracted text, dict with parsed response data
        """
        try:
            image_data, media_type = self.encode_image(image_path)

            message = self.client.messages.create(
                model=self.model,
                max_tokens=model_config.get_max_tokens('htr'),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": self.prompt
                            }
                        ]
                    }
                ]
            )

            # Store response data for cost calculation
            self._store_response_data(message, self.model)

            response_text = message.content[0].text.strip()

            # Parse response using unified parser (handles TOON format)
            try:
                parsed_data = self.parse_response(response_text, format_hint="toon")
                return parsed_data.get("extracted_text", ""), parsed_data
            except Exception as e:
                print(f"Parse error: {e}")
                return response_text, {
                    "extracted_text": response_text,
                    "confidence_assessment": "unknown",
                    "legibility_notes": f"Could not parse response: {e}"
                }

        except Exception as e:
            print(f"Error processing {image_path} with Claude: {str(e)}")
            return "", {"error": str(e)}


class ClaudeWork(ClaudeBase):
    """Class to represent a Work with a Claude prompt

    Attributes:
        pages (list): The individual canvases that make up a Claude work.
        full_text (str): The full text of canvases according to Claude.
        full_page_responses (list): A list of dicts with more information about the Claude full text response.

    """

    def __init__(self, pages=None, api_key: Optional[str] = None, model: Optional[str] = None):
        """Generates a Claude Work.

        pages (None or list): Paths to each canvas image of the work ordered logically.
        api_key (Optional[str] or None): Your Claude API Key.
        model (Optional[str] or None): Model to use (defaults to config)
        """
        super().__init__(api_key, model)
        self.pages = pages if pages is not None else []
        self.full_text, self.full_page_responses = self.get_page_text()
        self.prompt = self.get_prompt("metadata", letter_text=self.full_text)

    def get_page_text(self):
        """Gets the HTR page text from Claude based on canvas images.
        
        Returns:
            tuple: The full text of all pages as a str and a list of dicts with more info about each page.

        Example:
            >>> ClaudeWork(["test_files/amctrial_mcinnis_0004.jpg", "test_files/amctrial_mcinnis_0005.jpg"]).get_page_text()
        """
        just_the_text = []
        full_response = []
        for page in self.pages:
            claude_page = ClaudePage(model=self.model)
            claude_page_text = claude_page.extract_text_with_claude(page)
            just_the_text.append(claude_page_text[0])
            full_response.append(claude_page_text[1])
        return "\n\n".join(just_the_text), full_response
    
    def get_metadata(self, model: Optional[str] = None):
        """Extracts Dublin Core metadata from the letter text

        Args:
            model (Optional[str]): The Claude Model to Use (defaults to self.model)

        Returns:
            tuple: str (the response from Claude), dict (the metadata)

        Example:
            >>> ClaudeWork(["test_files/amctrial_mcinnis_0004.jpg"]).get_metadata()
        """
        try:
            model_to_use = model or self.model

            response = self.client.messages.create(
                model=model_to_use,
                max_tokens=model_config.get_max_tokens('metadata'),
                messages=[
                    {"role": "user", "content": self.prompt}
                ]
            )

            # Store the Cost
            self._store_response_data(response, model_to_use)

            response_text = response.content[0].text.strip()

            # Parse response using unified parser (handles TOON format)
            try:
                metadata = self.parse_response(response_text, format_hint="toon")
                metadata['filenames'] = self.pages
                return response_text, metadata
            except Exception as e:
                print(f"Parse error in metadata: {e}")
                return response_text, {"error": f"Could not parse response: {e}"}

        except Exception as e:
            print(f"Error getting metadata: {str(e)}")
            return "", {"error": str(e)}
    
    def save_metadata(self, metadata: Dict, output_path: str = "metadata"):
        """Save metadata as JSON.

        Args:
            metadata (dict): The metadata from claude
            output_path (str): Where to save the metadata on disk

        Returns:
            str: Path to saved file
        """
        if "error" in metadata:
            print(f"Cannot save metadata due to error: {metadata['error']}")
            return None

        json_path = self.save_json(metadata, output_path)
        print(f"Saved JSON metadata to: {json_path}")
        return json_path


class ClaudeAV(ClaudeBase):
    """Class to represent Audio/Video with WebVTT transcripts for Claude analysis"""

    def __init__(
            self,
            vtt_file,
            api_key: Optional[str] = None,
            model: Optional[str] = None
        ):
        super().__init__(api_key, model)
        self.full_text = self.get_full_text(vtt_file)
        self.prompt = self.get_prompt("vtt-mods", webvtt_content=self.full_text)

    def get_full_text(self, file_path):
        with open(file_path, 'r') as my_vtt:
            return my_vtt.read()

    def get_metadata(self, model: Optional[str] = None):
        try:
            model_to_use = model or self.model

            response = self.client.messages.create(
                model=model_to_use,
                max_tokens=model_config.get_max_tokens('av'),
                messages=[
                    {"role": "user", "content": self.prompt}
                ]
            )

            # Store the Cost
            self._store_response_data(response, model_to_use)

            response_text = response.content[0].text.strip()

            # Parse response using unified parser (handles TOON format)
            try:
                metadata = self.parse_response(response_text, format_hint="toon")
                return response_text, metadata
            except Exception as e:
                print(f"Parse error in metadata: {e}")
                return response_text, {"error": f"Could not parse response: {e}"}

        except Exception as e:
            print(f"Error getting metadata: {str(e)}")
            return "", {"error": str(e)}

    def save_metadata(self, metadata: Dict, output_path: str = "metadata"):
        """Save metadata as JSON.

        Args:
            metadata (dict): The metadata from claude
            output_path (str): Where to save the metadata on disk

        Returns:
            str: Path to saved file
        """
        if "error" in metadata:
            print(f"Cannot save metadata due to error: {metadata['error']}")
            return None

        json_path = self.save_json(metadata, output_path)
        print(f"Saved JSON metadata to: {json_path}")
        return json_path
    

class ClaudeImage(ClaudeBase):
    """Class to represent an Image or Map with existing metadata for Claude analysis
    
    Attributes:
        image_path (str): Path to the image file.
        existing_metadata (str): The existing metadata for the image/map.
        material_type (str): Type of material (MAP, PHOTOGRAPH, DRAWING, etc.).
        prompt (str): The formatted Claude prompt with metadata inserted.
    
    """
    def __init__(self, image_path: str = None, existing_metadata: str = "",
                 material_type: str = "IMAGE", api_key: Optional[str] = None,
                 model: Optional[str] = None):
        """Generates a Claude Image analysis object.

        Args:
            image_path (str): Path to the image file (optional, for reference).
            existing_metadata (str): The existing metadata text to analyze.
            material_type (str): Type of material - MAP, PHOTOGRAPH, DRAWING, PAINTING, PRINT, etc.
            api_key (Optional[str] or None): Your Claude API Key.
            model (Optional[str]): Claude model to use (defaults to config).
        """
        super().__init__(api_key, model)
        self.image_path = image_path
        self.existing_metadata = existing_metadata
        self.material_type = material_type.upper()
        self.prompt = self._format_prompt()

    def _format_prompt(self):
        """Format the prompt with existing metadata and material type

        Returns:
            str: The formatted prompt ready for Claude
        """
        return self.get_prompt("maps",
                              existing_metadata=self.existing_metadata,
                              material_type=self.material_type)

    def load_metadata_from_file(self, filepath: str, encoding: str = 'utf-8'):
        """Load existing metadata from a file
        
        Args:
            filepath (str): Path to the metadata file
            encoding (str): File encoding (default utf-8)
            
        Returns:
            None (updates self.existing_metadata and regenerates prompt)
        """
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                self.existing_metadata = f.read()
            self.prompt = self._format_prompt()
            print(f"Loaded metadata from: {filepath}")
        except Exception as e:
            print(f"Error loading metadata file: {str(e)}")

    def set_metadata(self, metadata_text: str):
        """Set the existing metadata text directly
        
        Args:
            metadata_text (str): The metadata text to analyze
            
        Returns:
            None (updates self.existing_metadata and regenerates prompt)
        """
        self.existing_metadata = metadata_text
        self.prompt = self._format_prompt()

    def encode_image(self, image_path: str) -> Tuple[str, str]:
        """Gets an image and returns a tuple with base64 encoding of the file contents and its media type
        
        Args:
            image_path (str): The path to an image

        Returns:
            tuple: base64 encoded image contents, media type
        """
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        suffix = Path(image_path).suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_type_map.get(suffix, 'image/jpeg')
        return image_data, media_type

    def analyze_image_with_metadata(self, image_path: str, model: str = None) -> Tuple[str, Dict]:
        """Analyzes an image along with existing metadata to suggest Dublin Core elements
        
        Args:
            image_path (str): The path to the image file
            model (str): The Claude Model to Use (defaults to self.model)

        Returns:
            tuple: str (the response from Claude), dict (the metadata analysis)
        """
        if model is None:
            model = self.model
            
        if not self.existing_metadata.strip():
            return "", {"error": "No existing metadata provided for analysis"}
            
        try:
            image_data, media_type = self.encode_image(image_path)
            
            response = self.client.messages.create(
                model=model,
                max_tokens=model_config.get_max_tokens('image'),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": self.prompt
                            }
                        ]
                    }
                ]
            )

            self._store_response_data(response, model)

            response_text = response.content[0].text.strip()

            # Parse response using unified parser (handles TOON format)
            try:
                metadata = self.parse_response(response_text, format_hint="toon")
                return response_text, metadata
            except Exception as e:
                print(f"Parse error in metadata: {e}")
                return response_text, {"error": f"Could not parse response: {e}"}
                
        except Exception as e:
            print(f"Error analyzing image {image_path}: {str(e)}")
            return "", {"error": str(e)}

    def get_dublin_core_analysis(self, model: str = None):
        """Analyzes existing metadata and suggests Dublin Core elements

        Args:
            model (str): The Claude Model to Use (defaults to self.model)
        
        Returns:
            tuple: str (the response from Claude), dict (the metadata analysis)

        Example:
            >>> img = ClaudeImage(existing_metadata="Title: Map of Texas, 1845...", material_type="MAP")
            >>> response, metadata = img.get_dublin_core_analysis()
        """
        if model is None:
            model = self.model
            
        if not self.existing_metadata.strip():
            return "", {"error": "No existing metadata provided for analysis"}
            
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=3000,
                messages=[
                    {"role": "user", "content": self.prompt}
                ]
            )
            
            self._store_response_data(response, model)

            response_text = response.content[0].text.strip()

            # Parse response using unified parser (handles TOON format)
            try:
                metadata = self.parse_response(response_text, format_hint="toon")
                return response_text, metadata
            except Exception as e:
                print(f"Parse error in metadata: {e}")
                return response_text, {"error": f"Could not parse response: {e}"}

        except Exception as e:
            print(f"Error getting metadata analysis: {str(e)}")
            return "", {"error": str(e)}

    def format_metadata_readable(self, metadata: Dict) -> str:
        """Format Dublin Core metadata analysis as human-readable report
        
        Args:
            metadata(dict): The metadata analysis from Claude as a dict

        Returns:
            str: The metadata output as a formatted string

        Example:
            >>> img = ClaudeImage()
            >>> response, metadata = img.get_dublin_core_analysis()
            >>> print(img.format_metadata_readable(metadata))
        """
        if "error" in metadata:
            return f"Error in metadata analysis: {metadata['error']}"
        
        output = []
        output.append("=" * 70)
        output.append(f"DUBLIN CORE METADATA ANALYSIS - {self.material_type}")
        output.append("=" * 70)
        
        if self.image_path:
            output.append(f"Image: {self.image_path}")
            output.append("")
        
        dc = metadata.get('dublin_core', {})
        
        for element, data in dc.items():
            if isinstance(data, dict) and data.get('value'):
                output.append(f"\n{element.upper().replace('_', ' ')}:")
                value = data['value']
                if isinstance(value, list):
                    output.append(f"  Value: {'; '.join(str(v) for v in value)}")
                else:
                    output.append(f"  Value: {value}")
                output.append(f"  Confidence: {data.get('confidence', 'unknown')}")
                
                if data.get('authority'):
                    authorities = data['authority'] if isinstance(data['authority'], list) else [data['authority']]
                    output.append(f"  Authority: {', '.join(authorities)}")
                    
                if data.get('reasoning'):
                    output.append(f"  Reasoning: {data['reasoning']}")
                    
                if data.get('source_metadata'):
                    source_text = data['source_metadata']
                    if len(source_text) > 100:
                        source_text = source_text[:100] + "..."
                    output.append(f"  Source: \"{source_text}\"")

        specialized = metadata.get('specialized_elements', {})
        if specialized:
            output.append(f"\n{'=' * 40}")
            output.append("SPECIALIZED ELEMENTS:")
            output.append(f"{'=' * 40}")
            
            for element, data in specialized.items():
                if isinstance(data, dict) and data.get('value'):
                    output.append(f"\n{element.upper().replace('_', ' ')}:")
                    output.append(f"  Value: {data['value']}")
                    output.append(f"  Confidence: {data.get('confidence', 'unknown')}")
                    if data.get('reasoning'):
                        output.append(f"  Reasoning: {data['reasoning']}")

        additional = metadata.get('additional_elements', {})
        if additional:
            output.append(f"\n{'=' * 40}")
            output.append("ADDITIONAL ELEMENTS:")
            output.append(f"{'=' * 40}")
            
            for element, data in additional.items():
                if isinstance(data, dict) and data.get('value'):
                    output.append(f"\n{element.upper().replace('_', ' ')}:")
                    output.append(f"  Value: {data['value']}")
                    output.append(f"  Confidence: {data.get('confidence', 'unknown')}")
                    if data.get('reasoning'):
                        output.append(f"  Reasoning: {data['reasoning']}")
        
        flags = metadata.get('flags', {})
        if any(flags.values()):
            output.append(f"\n{'=' * 40}")
            output.append("REVIEW REQUIRED:")
            output.append(f"{'=' * 40}")
            
            for flag_type, items in flags.items():
                if items:
                    output.append(f"\n{flag_type.replace('_', ' ').title()}:")
                    for item in items:
                        output.append(f"  • {item}")
        
        return "\n".join(output)
    
    def save_analysis(self, metadata: Dict, output_path: str = "image_metadata_analysis", 
                     formats: List[str] = ["json", "readable"]):
        """Save metadata analysis in various formats
        
        Args:
            metadata (dict): The metadata analysis from Claude
            output_path (str): Base path for output files
            formats (list): The formats to save ("json", "readable", "csv")

        Returns:
            None
        """
        if "error" in metadata:
            print(f"Cannot save metadata due to error: {metadata['error']}")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        material_suffix = self.material_type.lower()
        
        if "json" in formats:
            json_path = f"{output_path}_{material_suffix}_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"Saved JSON metadata to: {json_path}")
        
        if "readable" in formats:
            readable_path = f"{output_path}_{material_suffix}_{timestamp}.txt"
            readable_text = self.format_metadata_readable(metadata)
            with open(readable_path, 'w', encoding='utf-8') as f:
                f.write(readable_text)
            print(f"Saved readable metadata to: {readable_path}")
        
        if "csv" in formats:
            csv_path = f"{output_path}_{material_suffix}_{timestamp}.csv"
            self._save_metadata_csv(metadata, csv_path)
            print(f"Saved CSV metadata to: {csv_path}")

    def _save_metadata_csv(self, metadata: Dict, filepath: str):
        """Helper method to save metadata analysis as CSV
        
        Args:
            metadata (dict): The metadata as a dict
            filepath (str): The path to save the CSV file
        
        Returns:
            None
        """
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Section', 'Element', 'Value', 'Confidence', 'Authority', 'Reasoning', 'Source_Metadata'])
            
            # Dublin Core elements
            dc = metadata.get('dublin_core', {})
            for element, data in dc.items():
                if isinstance(data, dict) and data.get('value'):
                    value = data['value']
                    if isinstance(value, list):
                        value = '; '.join(str(v) for v in value)
                    
                    authority = data.get('authority', '')
                    if isinstance(authority, list):
                        authority = '; '.join(authority)
                    
                    writer.writerow([
                        'dublin_core',
                        element,
                        str(value),
                        data.get('confidence', ''),
                        authority,
                        data.get('reasoning', ''),
                        data.get('source_metadata', '')
                    ])
            
            specialized = metadata.get('specialized_elements', {})
            for element, data in specialized.items():
                if isinstance(data, dict) and data.get('value'):
                    writer.writerow([
                        'specialized',
                        element,
                        str(data['value']),
                        data.get('confidence', ''),
                        '',
                        data.get('reasoning', ''),
                        data.get('source_metadata', '')
                    ])
            
            additional = metadata.get('additional_elements', {})
            for element, data in additional.items():
                if isinstance(data, dict) and data.get('value'):
                    writer.writerow([
                        'additional',
                        element,
                        str(data['value']),
                        data.get('confidence', ''),
                        '',
                        data.get('reasoning', ''),
                        ''
                    ])

    def analyze_image_only(self, image_path: str, descriptive_prompt: str = None, model: str = None) -> Tuple[str, Dict]:
        """Analyzes an image without existing metadata to extract basic information
        
        Args:
            image_path (str): The path to the image file
            descriptive_prompt (str): Custom prompt for image analysis (optional)
            model (str): The Claude Model to Use (defaults to self.model)

        Returns:
            tuple: str (the response from Claude), dict (the extracted information)
        """
        if model is None:
            model = self.model
            
        if descriptive_prompt is None:
            descriptive_prompt = f"""Please analyze this {self.material_type.lower()} and provide the following information in JSON format:

{{
  "title": "suggested descriptive title",
  "description": "detailed description of what is shown",
  "subject_matter": ["main subjects or topics depicted"],
  "geographic_locations": ["any places that can be identified"],
  "date_clues": ["any visible dates or time period indicators"],
  "text_visible": ["any text, labels, or inscriptions visible"],
  "technical_details": {{
    "medium": "apparent medium or technique",
    "condition": "visible condition notes",
    "dimensions_apparent": "apparent size or format"
  }},
  "people_depicted": ["any people visible or identifiable"],
  "notable_features": ["distinctive or significant elements"]
}}

Focus on what can be directly observed in the image."""
            
        try:
            image_data, media_type = self.encode_image(image_path)
            
            response = self.client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": descriptive_prompt
                            }
                        ]
                    }
                ]
            )
            
            # Store the Cost
            self._store_response_data(response, model)

            response_text = response.content[0].text.strip()


            # Parse response using unified parser (handles TOON format)
            try:
                analysis = self.parse_response(response_text, format_hint="toon")
                return response_text, analysis
            except Exception as e:
                print(f"Parse error in analysis: {e}")
                return response_text, {"error": f"Could not parse response: {e}"}

        except Exception as e:
            print(f"Error analyzing image {image_path}: {str(e)}")
            return "", {"error": str(e)}

    def batch_analyze_metadata(self, metadata_list: List[Dict], output_dir: str = "batch_analysis"):
        """Analyze multiple metadata records in batch
        
        Args:
            metadata_list (list): List of dicts with 'metadata' and optional 'material_type' keys
            output_dir (str): Directory to save batch results
            
        Returns:
            list: List of analysis results
            
        Example:
            >>> img = ClaudeImage()
            >>> metadata_batch = [
            ...     {"metadata": "Title: Map of Texas...", "material_type": "MAP"},
            ...     {"metadata": "Photographer: John Smith...", "material_type": "PHOTOGRAPH"}
            ... ]
            >>> results = img.batch_analyze_metadata(metadata_batch)
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        for i, item in enumerate(metadata_list):
            print(f"Processing item {i+1}/{len(metadata_list)}...")
            
            self.set_metadata(item['metadata'])
            if 'material_type' in item:
                self.material_type = item['material_type'].upper()
                self.prompt = self._format_prompt()
            
            response, analysis = self.get_dublin_core_analysis()
            
            if 'error' not in analysis:
                output_path = os.path.join(output_dir, f"item_{i+1:03d}")
                self.save_analysis(analysis, output_path, formats=["json"])
            
            results.append({
                'item_number': i+1,
                'material_type': self.material_type,
                'response': response,
                'analysis': analysis
            })
        
        summary_path = os.path.join(output_dir, "batch_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Batch analysis complete. Summary saved to: {summary_path}")
        
        return results


class ClaudeArticle(ClaudeBase):
    """Class to analyze scholarly article first pages and abstracts for creator and subject metadata

    Attributes:
        image_path (str): Path to the article first page image file.
        existing_metadata (str): Any existing metadata for the article.
        prompt (str): The formatted Claude prompt with metadata and image location inserted.
    """

    def __init__(self, image_path: str = None, existing_metadata: str = "",
                 api_key: Optional[str] = None, model="claude-3-5-haiku-20241022"):
        """Generates a Claude Article analysis object.

        Args:
            image_path (str): Path to the article first page image.
            existing_metadata (str): Any existing metadata text to supplement analysis.
            api_key (Optional[str] or None): Your Claude API Key.
            model (str): Claude model to use.
        """
        super().__init__(api_key)
        self.image_path = image_path
        self.existing_metadata = existing_metadata
        self.model = model
        self.prompt = self._format_prompt()

    def _format_prompt(self):
        """Format the prompt with existing metadata and image location

        Returns:
            str: The formatted prompt ready for Claude
        """
        # Get the article subject and creator prompt template
        prompt_template = self.get_prompt("subjects_from_abstract.md")

        # Replace placeholders with actual data
        image_location = self.image_path if self.image_path else "Image will be provided"
        formatted_prompt = prompt_template.replace("[INSERT IMAGE LOCATION]", image_location)
        formatted_prompt = formatted_prompt.replace("[INSERT EXISTING METADATA]", self.existing_metadata)

        return formatted_prompt

    def load_metadata_from_file(self, filepath: str, encoding: str = 'utf-8'):
        """Load existing metadata from a file

        Args:
            filepath (str): Path to the metadata file
            encoding (str): File encoding (default utf-8)

        Returns:
            None (updates self.existing_metadata and regenerates prompt)
        """
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                self.existing_metadata = f.read()
            # Regenerate prompt with new metadata
            self.prompt = self._format_prompt()
            print(f"Loaded metadata from: {filepath}")
        except Exception as e:
            print(f"Error loading metadata file: {str(e)}")

    def set_metadata(self, metadata_text: str):
        """Set the existing metadata text directly

        Args:
            metadata_text (str): The metadata text to supplement analysis

        Returns:
            None (updates self.existing_metadata and regenerates prompt)
        """
        self.existing_metadata = metadata_text
        self.prompt = self._format_prompt()

    def encode_image(self, image_path: str) -> Tuple[str, str]:
        """Gets an image and returns a tuple with base64 encoding of the file contents and its media type

        Args:
            image_path (str): The path to an image

        Returns:
            tuple: base64 encoded image contents, media type
        """
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        suffix = Path(image_path).suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.pdf': 'application/pdf'
        }
        media_type = media_type_map.get(suffix, 'image/jpeg')
        return image_data, media_type

    def analyze_article(self, image_path: str = None, model: str = None) -> Tuple[str, Dict]:
        """Analyzes article first page/abstract to extract creators and FAST subject headings

        Args:
            image_path (str): Path to article image (uses self.image_path if not provided)
            model (str): The Claude Model to Use (defaults to self.model)

        Returns:
            tuple: str (the response from Claude), dict (the creator and subject analysis)

        Example:
            >>> article = ClaudeArticle(image_path="article_firstpage.jpg")
            >>> response, metadata = article.analyze_article()
        """
        if model is None:
            model = self.model

        if image_path is None:
            image_path = self.image_path

        if not image_path:
            return "", {"error": "No image path provided for analysis"}

        try:
            image_data, media_type = self.encode_image(image_path)

            response = self.client.messages.create(
                model=model,
                max_tokens=3000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": self.prompt
                            }
                        ]
                    }
                ]
            )

            # Store the Cost
            self._store_response_data(response, model)

            response_text = response.content[0].text.strip()

            # Parse response using unified parser (handles TOON format)
            try:
                metadata = self.parse_response(response_text, format_hint="toon")
                return response_text, metadata
            except Exception as e:
                print(f"Parse error in metadata: {e}")
                return response_text, {"error": f"Could not parse response: {e}"}

        except Exception as e:
            print(f"Error analyzing article {image_path}: {str(e)}")
            return "", {"error": str(e)}

    def format_metadata_readable(self, metadata: Dict) -> str:
        """Format creator and subject analysis as human-readable report

        Args:
            metadata(dict): The metadata analysis from Claude as a dict

        Returns:
            str: The metadata output as a formatted string
        """
        if "error" in metadata:
            return f"Error in metadata analysis: {metadata['error']}"

        output = []
        output.append("=" * 70)
        output.append("ARTICLE CREATOR AND SUBJECT ANALYSIS")
        output.append("=" * 70)

        if self.image_path:
            output.append(f"Article Image: {self.image_path}")
            output.append("")

        # Creator information
        creator_data = metadata.get('creator', {})
        if creator_data:
            output.append(f"\n{'=' * 40}")
            output.append("CREATORS:")
            output.append(f"{'=' * 40}")

            personal_creators = creator_data.get('personal_creators', [])
            if personal_creators:
                output.append("\nPersonal Creators:")
                for creator in personal_creators:
                    output.append(f"  • {creator.get('name', 'Unknown')}")
                    output.append(f"    Format: {creator.get('name_format', 'unknown')}")
                    output.append(f"    Confidence: {creator.get('confidence', 'unknown')}")
                    if creator.get('reasoning'):
                        output.append(f"    Reasoning: {creator['reasoning']}")

            if creator_data.get('source_metadata'):
                output.append(f"\n  Source: {creator_data['source_metadata']}")

        # Subject/FAST analysis
        subject_data = metadata.get('subject', {})
        if subject_data:
            output.append(f"\n{'=' * 40}")
            output.append("FAST SUBJECT HEADINGS:")
            output.append(f"{'=' * 40}")

            fast_headings = subject_data.get('fast_headings', [])
            if fast_headings:
                for heading in fast_headings:
                    output.append(f"\n  {heading.get('term', 'Unknown')}")
                    output.append(f"    Facet: {heading.get('facet', 'unknown')}")
                    if heading.get('fast_id'):
                        output.append(f"    FAST ID: {heading['fast_id']}")
                    output.append(f"    Confidence: {heading.get('confidence', 'unknown')}")
                    if heading.get('reasoning'):
                        output.append(f"    Reasoning: {heading['reasoning']}")
                    if heading.get('source_in_text'):
                        source = heading['source_in_text']
                        if len(source) > 100:
                            source = source[:100] + "..."
                        output.append(f"    Source: \"{source}\"")

            alternative_headings = subject_data.get('alternative_headings', [])
            if alternative_headings:
                output.append(f"\n  Alternative Headings Considered:")
                for alt in alternative_headings:
                    output.append(f"    • {alt.get('term', 'Unknown')}: {alt.get('reason_not_selected', 'N/A')}")

        # FAST analysis by facet
        fast_analysis = metadata.get('fast_analysis', {})
        if fast_analysis:
            output.append(f"\n{'=' * 40}")
            output.append("FAST FACET ANALYSIS:")
            output.append(f"{'=' * 40}")

            facets = [
                ('topical_facet', 'Topical'),
                ('geographic_facet', 'Geographic'),
                ('chronological_facet', 'Chronological'),
                ('form_facet', 'Form/Genre'),
                ('personal_facet', 'Personal Names'),
                ('corporate_facet', 'Corporate Names')
            ]

            for facet_key, facet_name in facets:
                facet_data = fast_analysis.get(facet_key, {})
                if facet_data and facet_data.get('terms'):
                    output.append(f"\n{facet_name}:")
                    output.append(f"  Terms: {'; '.join(facet_data['terms'])}")
                    output.append(f"  Confidence: {facet_data.get('confidence', 'unknown')}")

                    # Special handling for specific facets
                    if facet_key == 'topical_facet':
                        if facet_data.get('primary_concepts'):
                            output.append(f"  Primary Concepts: {'; '.join(facet_data['primary_concepts'])}")
                        if facet_data.get('secondary_concepts'):
                            output.append(f"  Secondary Concepts: {'; '.join(facet_data['secondary_concepts'])}")
                    elif facet_key == 'geographic_facet' and facet_data.get('geographic_scope'):
                        output.append(f"  Geographic Scope: {facet_data['geographic_scope']}")
                    elif facet_key == 'chronological_facet' and facet_data.get('temporal_scope'):
                        output.append(f"  Temporal Scope: {facet_data['temporal_scope']}")

        # Flags and warnings
        flags = metadata.get('flags', {})
        if any(flags.values()):
            output.append(f"\n{'=' * 40}")
            output.append("REVIEW REQUIRED:")
            output.append(f"{'=' * 40}")

            for flag_type, items in flags.items():
                if items:
                    output.append(f"\n{flag_type.replace('_', ' ').title()}:")
                    for item in items:
                        output.append(f"  • {item}")

        return "\n".join(output)

    def save_analysis(self, metadata: Dict, output_path: str = "article_analysis",
                      formats: List[str] = ["json", "readable"]):
        """Save metadata analysis in various formats

        Args:
            metadata (dict): The metadata analysis from Claude
            output_path (str): Base path for output files
            formats (list): The formats to save ("json", "readable", "csv")

        Returns:
            None
        """
        if "error" in metadata:
            print(f"Cannot save metadata due to error: {metadata['error']}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if "json" in formats:
            json_path = f"{output_path}_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"Saved JSON metadata to: {json_path}")

        if "readable" in formats:
            readable_path = f"{output_path}_{timestamp}.txt"
            readable_text = self.format_metadata_readable(metadata)
            with open(readable_path, 'w', encoding='utf-8') as f:
                f.write(readable_text)
            print(f"Saved readable metadata to: {readable_path}")

        if "csv" in formats:
            csv_path = f"{output_path}_{timestamp}.csv"
            self._save_metadata_csv(metadata, csv_path)
            print(f"Saved CSV metadata to: {csv_path}")

    def _save_metadata_csv(self, metadata: Dict, filepath: str):
        """Helper method to save metadata analysis as CSV

        Args:
            metadata (dict): The metadata as a dict
            filepath (str): The path to save the CSV file

        Returns:
            None
        """
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Creators section
            writer.writerow(['CREATORS'])
            writer.writerow(['Name', 'Format', 'Confidence', 'Reasoning'])

            creator_data = metadata.get('creator', {})
            personal_creators = creator_data.get('personal_creators', [])
            for creator in personal_creators:
                writer.writerow([
                    creator.get('name', ''),
                    creator.get('name_format', ''),
                    creator.get('confidence', ''),
                    creator.get('reasoning', '')
                ])

            writer.writerow([])  # Blank row

            # FAST Subject Headings section
            writer.writerow(['FAST SUBJECT HEADINGS'])
            writer.writerow(['Term', 'Facet', 'FAST ID', 'Confidence', 'Reasoning', 'Source in Text'])

            subject_data = metadata.get('subject', {})
            fast_headings = subject_data.get('fast_headings', [])
            for heading in fast_headings:
                writer.writerow([
                    heading.get('term', ''),
                    heading.get('facet', ''),
                    heading.get('fast_id', ''),
                    heading.get('confidence', ''),
                    heading.get('reasoning', ''),
                    heading.get('source_in_text', '')
                ])

            writer.writerow([])  # Blank row

            # FAST Facet Analysis section
            writer.writerow(['FAST FACET ANALYSIS'])
            writer.writerow(['Facet', 'Terms', 'Confidence', 'Additional Info'])

            fast_analysis = metadata.get('fast_analysis', {})
            facets = [
                ('topical_facet', 'Topical'),
                ('geographic_facet', 'Geographic'),
                ('chronological_facet', 'Chronological'),
                ('form_facet', 'Form/Genre'),
                ('personal_facet', 'Personal Names'),
                ('corporate_facet', 'Corporate Names')
            ]

            for facet_key, facet_name in facets:
                facet_data = fast_analysis.get(facet_key, {})
                if facet_data and facet_data.get('terms'):
                    terms = '; '.join(facet_data['terms'])
                    additional = ''
                    if facet_key == 'topical_facet':
                        primary = facet_data.get('primary_concepts', [])
                        if primary:
                            additional = f"Primary: {'; '.join(primary)}"
                    elif facet_key == 'geographic_facet':
                        additional = facet_data.get('geographic_scope', '')
                    elif facet_key == 'chronological_facet':
                        additional = facet_data.get('temporal_scope', '')

                    writer.writerow([
                        facet_name,
                        terms,
                        facet_data.get('confidence', ''),
                        additional
                    ])

    def batch_analyze_articles(self, article_list: List[Dict], output_dir: str = "batch_analysis"):
        """Analyze multiple articles in batch

        Args:
            article_list (list): List of dicts with 'image_path' and optional 'existing_metadata' keys
            output_dir (str): Directory to save batch results

        Returns:
            list: List of analysis results

        Example:
            >>> article = ClaudeArticle()
            >>> articles = [
            ...     {"image_path": "article1.jpg", "existing_metadata": "Title: ..."},
            ...     {"image_path": "article2.jpg"}
            ... ]
            >>> results = article.batch_analyze_articles(articles)
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        results = []
        for i, item in enumerate(article_list):
            print(f"Processing article {i + 1}/{len(article_list)}...")

            # Set metadata if provided
            if 'existing_metadata' in item:
                self.set_metadata(item['existing_metadata'])

            # Analyze
            response, analysis = self.analyze_article(item['image_path'])

            # Save individual result
            if 'error' not in analysis:
                output_path = os.path.join(output_dir, f"article_{i + 1:03d}")
                self.save_analysis(analysis, output_path, formats=["json"])

            results.append({
                'article_number': i + 1,
                'image_path': item['image_path'],
                'response': response,
                'analysis': analysis
            })

        # Save batch summary
        summary_path = os.path.join(output_dir, "batch_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Batch analysis complete. Summary saved to: {summary_path}")

        return results

    def extract_fast_headings_only(self, metadata: Dict) -> List[str]:
        """Extract just the FAST heading terms as a simple list

        Args:
            metadata (dict): The analysis metadata

        Returns:
            list: List of FAST heading strings
        """
        subject_data = metadata.get('subject', {})
        fast_headings = subject_data.get('fast_headings', [])
        return [heading.get('term') for heading in fast_headings if heading.get('term')]

    def extract_creators_only(self, metadata: Dict) -> List[str]:
        """Extract just the creator names as a simple list

        Args:
            metadata (dict): The analysis metadata

        Returns:
            list: List of creator name strings
        """
        creator_data = metadata.get('creator', {})
        personal_creators = creator_data.get('personal_creators', [])
        return [creator.get('name') for creator in personal_creators if creator.get('name')]


if __name__ == "__main__":

    # # Define a set of pages for a work
    # pages = ["test_files/amctrial_mcinnis_0004.jpg", "test_files/amctrial_mcinnis_0005.jpg"]
    # work = ClaudeWork(pages=pages)
    
    # # Let's print the HTR it found
    # print("Extracted text:")
    # print(work.full_text)
    # print("\n" + "="*50 + "\n")
    
    # # Now, let's use that to get some good ole descriptive metadata and print it
    # raw_response, metadata = work.get_metadata(
    # )
    # print(work.format_metadata_readable(metadata))
    
    # # Finally, let's save the output in every imaginable format
    # work.save_metadata(metadata, formats=["json", "readable", "csv"])
    
    # try:
    #     cost_info = work.calculate_cost()
    #     print(f"Cost Analysis:")
    #     print(f"Model: {cost_info['model']}")
    #     print(f"Input tokens: {cost_info['input_tokens']:,}")
    #     print(f"Output tokens: {cost_info['output_tokens']:,}")
    #     print(f"Input cost: ${cost_info['input_cost_usd']:.6f}")
    #     print(f"Output cost: ${cost_info['output_cost_usd']:.6f}")
    #     print(f"Total cost: ${cost_info['total_cost_usd']:.6f}")
    # except ValueError as e:
    #     print(f"Could not calculate cost: {e}")

    # vtt_file = "/Users/mark.baggett/code/whisper-reviewer/vtts/c000507_004_018_access.caption.vtt"
    # av_work = ClaudeAV(vtt_file=vtt_file)
    # raw_response, metadata = av_work.get_metadata(
    # )
    # print(av_work.format_metadata_readable(metadata))
    
    # # Finally, let's save the output in every imaginable format
    # av_work.save_metadata(metadata, formats=["json", "readable", "csv"], output_path=vtt_file.split('/')[-1].replace('.caption.vtt', ''). replace('.vtt', ''))
    
    # try:
    #     cost_info = av_work.calculate_cost()
    #     print(f"Cost Analysis:")
    #     print(f"Model: {cost_info['model']}")
    #     print(f"Input tokens: {cost_info['input_tokens']:,}")
    #     print(f"Output tokens: {cost_info['output_tokens']:,}")
    #     print(f"Input cost: ${cost_info['input_cost_usd']:.6f}")
    #     print(f"Output cost: ${cost_info['output_cost_usd']:.6f}")
    #     print(f"Total cost: ${cost_info['total_cost_usd']:.6f}")
    # except ValueError as e:
    #     print(f"Could not calculate cost: {e}")

    # Analyze image with existing metadata

    # img = ClaudeImage(
    #     image_path="test.jpg",
    #     existing_metadata="Title: To Belgium and back with the 79th Infantry Division, 31 Aug to 25 Oct, 1944, Theater: European",
    #     material_type="MAP"
    # )
    # response, metadata = img.analyze_image_with_metadata("test.jpg")
    # print(metadata)
    #
    # print(response)
    from csv import DictReader
    final_articles = []
    with open(
            "/Users/mark.baggett/code/ancient_ojs_journals/lsgnews_final_articles.csv",
            "r"
    ) as galveston:
        articles = DictReader(galveston)

        for article in articles:
            final_articles.append(
                {
                    'image_path': f"/Users/mark.baggett/code/ancient_ojs_journals/{article['bundle:THUMBNAIL']}",
                    'existing_metadata': f"Title: {article['dc.title']}, Abstract: {article['dcterms.abstract']}",
                }
             )
    article = ClaudeArticle()
    results = article.batch_analyze_articles(final_articles)

    # article = ClaudeArticle()
    # articles = [
    #     {
    #         "image_path": "/Users/mark.baggett/code/ancient_ojs_journals/thumbnails/310-1152-1-PB.png",
    #         "existing_metadata": "The Rosenberg Library in Galveston has two unsigned maps, in Spanish, apparently drawn in the year 1816. The first is listed as a photostatic copy of a map in the National Archives in Mexico City.",
    #     },
    # ]
    # results = article.batch_analyze_articles(articles)
