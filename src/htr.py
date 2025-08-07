import os
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import anthropic
from PIL import Image
import pandas as pd
import re
import csv


class ClaudeBase:
    """A Base Class for Claude Requests"""
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude client."""
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get(
                "CLAUDE_API"
            )
        )
    
    def get_prompt(self, prompt_file):
        """A method to get the prompt text from a markdown file.
        
        Args:
            prompt_file (str): A markdown file including a prompt

        Returns:
            str: The contents of the file.

        Examples:
            >>> ClaudeBase().get_prompt("htr.md")
            You are an expert historical document transcriber specializing in 19th-century correspondence. Your task is to transcribe all handwritten text from this 1800s letter written in cursive script.

            ## Instructions:
            - Transcribe all visible handwritten text exactly as written, preserving original spelling, punctuation, and capitalization  
            - Maintain the original line breaks and paragraph structure when possible  
            - For words that are unclear due to handwriting, fading, or damage, provide your best interpretation followed by `[illegible]` in brackets  
            - If a word is completely unreadable, use `[illegible]` as a placeholder  
            - Note any significant damage, tears, or missing sections that affect readability as `[damaged]` or `[torn]`  
            - Include any marginalia, postscripts, or text written in different orientations  
            - If the letter spans multiple pages or has text on both sides, clearly indicate page/side transitions  

            ## Return the results in this JSON format:
            ```json
            {
            "extracted_text": "full text content",
            "confidence_assesment": "high/medium/low",
            "legibility_notes": "any notes about difficult to read sections"
            }

        """
        with open(f'prompts/{prompt_file}', 'r') as f:
            text = f.read()
        return text
    
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
    """A Class to Represet Pages as Claude Requests"""
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.prompt = self.get_prompt("htr.md")

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

    def extract_text_with_claude(self, image_path: str, model: str = "claude-3-5-haiku-20241022") -> Tuple[str, Dict]:
        """Uses Claude AI to extract the contents of a handwritten document
        
        Args:
            image_path (str): The path to an image
            model (str): The Claude model to use

        Returns:
            tuple: original response text, a dict with information about the response text
        """
        try:
            image_data, media_type = self.encode_image(image_path)
            
            message = self.client.messages.create(
                model=model,
                max_tokens=1000,
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
            self._store_response_data(message, model)
            
            response_text = message.content[0].text.strip()
            
            try:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        parsed_data = json.loads(json_str)
                    except json.JSONDecodeError:
                        def escape_string_content(match):
                            content = match.group(1)
                            content = content.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
                            return f'"{content}"'
                        
                        cleaned_json = re.sub(r'"([^"]*)"', escape_string_content, json_str)
                        parsed_data = json.loads(cleaned_json)
                    
                    return parsed_data.get("extracted_text", ""), parsed_data
                else:
                    return response_text, {
                        "extracted_text": response_text,
                        "confidence_assessment": "unknown",
                        "text_type": "unknown",
                        "legibility_notes": "No JSON object found in response"
                    }
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Problematic JSON string: {repr(json_str[:200])}...")
                return response_text, {
                    "extracted_text": response_text,
                    "confidence_assessment": "unknown",
                    "text_type": "unknown",
                    "legibility_notes": "Could not parse JSON response"
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
    def __init__(self, pages=None, api_key: Optional[str] = None):
        """Generates a Claude Work.
        
        pages (None or list): Paths to each canvas image of the work ordered logically.
        api_key (Optional[str] or None): Your Claude API Key.
        """
        super().__init__(api_key)
        self.pages = pages if pages is not None else []
        self.full_text, self.full_page_responses = self.get_page_text()
        self.prompt = self.get_prompt("metadata.md").replace("[INSERT LETTER TEXT HERE]", self.full_text)

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
            claude_page = ClaudePage()
            claude_page_text = claude_page.extract_text_with_claude(page)
            just_the_text.append(claude_page_text[0])
            full_response.append(claude_page_text[1])
        return "\n\n".join(just_the_text), full_response
    
    def get_metadata(self, model: str = "claude-3-5-haiku-20241022"):
        """Extracts Dublin Core metadata from the letter text

        Args:
            model (str): The Claude Model to Use
        
        Returns:
            tuple: str (the response from Claude), dict (the metadata)

        Example:
            >>> ClaudeWork(["test_files/amctrial_mcinnis_0004.jpg", "test_files/amctrial_mcinnis_0005.jpg"]).get_metadata() 
        """
        try:
            response = self.client.messages.create(
                model=model,
                # TODO: tokens should be defineable -- not hardcoded
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": self.prompt}
                ]
            )
            
            # Store the Cost
            self._store_response_data(response, model)

            response_text = response.content[0].text.strip()
            print(response_text)
            
            # Extract JSON from response (Claude might include explanatory text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    metadata = json.loads(json_str)
                    return response_text, metadata
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in metadata: {e}")
                    return response_text, {"error": "Could not parse JSON response"}
            else:
                print("No JSON object found in metadata response")
                return response_text, {"error": "No JSON object found in response"}
                
        except Exception as e:
            print(f"Error getting metadata: {str(e)}")
            return "", {"error": str(e)}
    
    def format_metadata_readable(self, metadata: Dict) -> str:
        """Format Dublin Core metadata as human-readable report
        
        Args:
            metadata(dict): The metadata from Claude as a dict

        Returns:
            str: The metadata output as a str separated by newlines.

        Example:
                >>> ClaudeWork(["test_files/amctrial_mcinnis_0004.jpg", "test_files/amctrial_mcinnis_0005.jpg"]).format_metadata_readable({
                    "dublin_core": {
                      "title": {
                        "value": "Personal Letter from Bingley in Columbus, Texas, Describing Family Grief",
                        "confidence": "high",
                        "reasoning": "Derived from letter's content and personal narrative",
                        "source_text": "Though I feel very little like writing you I much feel you the condition I am in"
                    }})
        """
        if "error" in metadata:
            return f"Error in metadata: {metadata['error']}"
        
        output = []
        output.append("=" * 60)
        output.append("DUBLIN CORE METADATA ANALYSIS")
        output.append("=" * 60)
        
        # Core Dublin Core elements
        dc = metadata.get('dublin_core', {})
        
        for element, data in dc.items():
            if isinstance(data, dict) and data.get('value'):
                output.append(f"\n{element.upper().replace('_', ' ')}:")
                output.append(f"  Value: {data['value']}")
                output.append(f"  Confidence: {data.get('confidence', 'unknown')}")
                if data.get('reasoning'):
                    output.append(f"  Reasoning: {data['reasoning']}")
                if data.get('source_text'):
                    source_text = data['source_text']
                    if len(source_text) > 100:
                        source_text = source_text[:100] + "..."
                    output.append(f"  Source: \"{source_text}\"")
        
        # Additional elements
        additional = metadata.get('additional_elements', {})
        if additional:
            output.append(f"\n{'=' * 30}")
            output.append("ADDITIONAL ELEMENTS:")
            output.append(f"{'=' * 30}")
            
            for element, data in additional.items():
                if isinstance(data, dict) and data.get('value'):
                    output.append(f"\n{element.upper().replace('_', ' ')}:")
                    output.append(f"  {data['value']} (confidence: {data.get('confidence', 'unknown')})")
        
        # Flags and warnings
        flags = metadata.get('flags', {})
        if any(flags.values()):
            output.append(f"\n{'=' * 30}")
            output.append("REVIEW REQUIRED:")
            output.append(f"{'=' * 30}")
            
            for flag_type, items in flags.items():
                if items:
                    output.append(f"\n{flag_type.replace('_', ' ').title()}:")
                    for item in items:
                        output.append(f"  • {item}")
        
        return "\n".join(output)
    
    def save_metadata(self, metadata: Dict, output_path: str = "metadata", formats: List[str] = ["json", "readable"]):
        """Save metadata in various formats
        
        Args:
            metadata (dict): The metadata from claude
            output_path (str): Where to save the metadata on disk
            formats (list): The formats to save.

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
        """Helper method to save metadata as CSV
        
        Args:
            metadata (dict): The metadata as a dict
            filepath (str): The path to the csv on disk.
        
        Returns:
            None

        """
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Element', 'Value', 'Confidence', 'Reasoning', 'Source_Text'])
            
            dc = metadata.get('dublin_core', {})
            for element, data in dc.items():
                if isinstance(data, dict) and data.get('value'):
                    value = data['value']
                    if isinstance(value, list):
                        value = '; '.join(str(v) for v in value)
                    
                    writer.writerow([
                        element,
                        str(value),
                        data.get('confidence', ''),
                        data.get('reasoning', ''),
                        data.get('source_text', '')
                    ])


if __name__ == "__main__":
    # Define a set of pages for a work
    pages = ["test_files/amctrial_mcinnis_0004.jpg", "test_files/amctrial_mcinnis_0005.jpg"]
    work = ClaudeWork(pages=pages)
    
    # Let's print the HTR it found
    print("Extracted text:")
    print(work.full_text)
    print("\n" + "="*50 + "\n")
    
    # Now, let's use that to get some good ole descriptive metadata and print it
    raw_response, metadata = work.get_metadata()
    print(work.format_metadata_readable(metadata))
    
    # Finally, let's save the output in every imaginable format
    work.save_metadata(metadata, formats=["json", "readable", "csv"])
    
    try:
        cost_info = work.calculate_cost()
        print(f"Cost Analysis:")
        print(f"Model: {cost_info['model']}")
        print(f"Input tokens: {cost_info['input_tokens']:,}")
        print(f"Output tokens: {cost_info['output_tokens']:,}")
        print(f"Input cost: ${cost_info['input_cost_usd']:.6f}")
        print(f"Output cost: ${cost_info['output_cost_usd']:.6f}")
        print(f"Total cost: ${cost_info['total_cost_usd']:.6f}")
    except ValueError as e:
        print(f"Could not calculate cost: {e}")