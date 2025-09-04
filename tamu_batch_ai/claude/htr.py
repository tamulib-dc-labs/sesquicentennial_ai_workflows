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
    def __init__(self, api_key: Optional[str] = None, model="claude-3-5-haiku-20241022"):
        """Initialize Claude client."""
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get(
                "CLAUDE_API"
            )
        )
        self.model = model
    
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
    def __init__(self, api_key: Optional[str] = None, model="claude-3-5-haiku-20241022"):
        super().__init__(api_key)
        self.prompt = self.get_prompt("htr.md")
        self.model = model

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

    def extract_text_with_claude(self, image_path: str) -> Tuple[str, Dict]:
        """Uses Claude AI to extract the contents of a handwritten document
        
        Args:
            image_path (str): The path to an image

        Returns:
            tuple: original response text, a dict with information about the response text
        """
        try:
            image_data, media_type = self.encode_image(image_path)
            
            message = self.client.messages.create(
                model=self.model,
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
            self._store_response_data(message, self.model)
            
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
    def __init__(self, pages=None, api_key: Optional[str] = None, model="claude-3-5-haiku-20241022"):
        """Generates a Claude Work.
        
        pages (None or list): Paths to each canvas image of the work ordered logically.
        api_key (Optional[str] or None): Your Claude API Key.
        """
        super().__init__(api_key)
        self.pages = pages if pages is not None else []
        self.model = model
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
            claude_page = ClaudePage(model=self.model)
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


class ClaudeAV(ClaudeBase):
    def __init__(
            self, 
            vtt_file, 
            api_key: Optional[str] = None, 
            model="claude-3-5-haiku-20241022"
        ):
        super().__init__(api_key)
        self.model = model
        self.full_text = self.get_full_text(
            vtt_file
            )
        self.prompt = self.get_prompt(
            "vtt-mods.md"
        ).replace(
            "[INSERT WEBVTT CONTENT HERE]", 
            self.full_text
        )
        

    def get_full_text(self, file_path):
        with open(file_path, 'r') as my_vtt:
            return my_vtt.read()

    def get_metadata(self, model: str = "claude-3-5-haiku-20241022"):
        try:
            response = self.client.messages.create(
                model=model,
                # TODO: tokens should be definable -- not hardcoded
                max_tokens=4000,  # Increased for more complex MODS structure
                messages=[
                    {"role": "user", "content": self.prompt}
                ]
            )
            
            # Store the Cost
            self._store_response_data(response, model)

            response_text = response.content[0].text.strip()
            
            # Extract JSON from response since Claude might include explanatory text that will mess stuff up
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
        if "error" in metadata:
            return f"Error in metadata: {metadata['error']}"
        
        output = []
        output.append("=" * 60)
        output.append("AVALON MODS METADATA ANALYSIS")
        output.append("=" * 60)
        
        content_analysis = metadata.get('content_analysis', {})
        if content_analysis:
            output.append(f"\nCONTENT ANALYSIS:")
            output.append(f"  Media Type: {content_analysis.get('media_type', 'unknown')}")
            output.append(f"  Content Category: {content_analysis.get('content_category', 'unknown')}")
            output.append(f"  Duration Estimate: {content_analysis.get('duration_estimate', 'unknown')}")
            output.append(f"  Primary Content: {content_analysis.get('primary_content_summary', 'N/A')}")
            
            if content_analysis.get('speakers_identified'):
                output.append(f"  Speakers: {', '.join(content_analysis['speakers_identified'])}")
            if content_analysis.get('key_topics_mentioned'):
                output.append(f"  Key Topics: {', '.join(content_analysis['key_topics_mentioned'])}")

        avalon_mods = metadata.get('avalon_mods_metadata', {})
        
        required_fields = avalon_mods.get('required_fields', {})
        if required_fields:
            output.append(f"\n{'=' * 30}")
            output.append("REQUIRED FIELDS:")
            output.append(f"{'=' * 30}")
            
            for field, data in required_fields.items():
                if isinstance(data, dict) and data.get('value'):
                    output.append(f"\n{field.upper().replace('_', ' ')}:")
                    output.append(f"  Value: {data['value']}")
                    output.append(f"  Confidence: {data.get('confidence', 'unknown')}")
                    if data.get('reasoning'):
                        output.append(f"  Reasoning: {data['reasoning']}")

        core_descriptive = avalon_mods.get('core_descriptive', {})
        if core_descriptive:
            output.append(f"\n{'=' * 30}")
            output.append("CORE DESCRIPTIVE FIELDS:")
            output.append(f"{'=' * 30}")
            
            for field, data in core_descriptive.items():
                if isinstance(data, dict) and data.get('value'):
                    output.append(f"\n{field.upper().replace('_', ' ')}:")
                    value = data['value']
                    if isinstance(value, list):
                        value = '; '.join(str(v) for v in value)
                    output.append(f"  Value: {value}")
                    output.append(f"  Confidence: {data.get('confidence', 'unknown')}")
                    if data.get('authority'):
                        output.append(f"  Authority: {data['authority']}")
                    if data.get('reasoning'):
                        output.append(f"  Reasoning: {data['reasoning']}")

        subject_access = avalon_mods.get('subject_access', {})
        if subject_access:
            output.append(f"\n{'=' * 30}")
            output.append("SUBJECT ACCESS:")
            output.append(f"{'=' * 30}")
            
            for field, data in subject_access.items():
                if isinstance(data, dict) and data.get('value'):
                    output.append(f"\n{field.upper().replace('_', ' ')}:")
                    value = data['value']
                    if isinstance(value, list):
                        value = '; '.join(str(v) for v in value)
                    output.append(f"  Value: {value}")
                    output.append(f"  Confidence: {data.get('confidence', 'unknown')}")
                    if data.get('authority'):
                        output.append(f"  Authority: {data['authority']}")

        additional_fields = avalon_mods.get('additional_fields', {})
        if additional_fields:
            output.append(f"\n{'=' * 30}")
            output.append("ADDITIONAL FIELDS:")
            output.append(f"{'=' * 30}")
            
            for field, data in additional_fields.items():
                if field == 'notes' and isinstance(data, list):
                    output.append(f"\nNOTES:")
                    for note in data:
                        if note.get('note_value'):
                            output.append(f"  {note.get('note_type', 'general').title()}: {note['note_value']}")
                elif isinstance(data, dict) and data.get('value'):
                    output.append(f"\n{field.upper().replace('_', ' ')}:")
                    output.append(f"  Value: {data['value']}")
                    output.append(f"  Confidence: {data.get('confidence', 'unknown')}")

        quality = metadata.get('quality_assessment', {})
        if quality:
            output.append(f"\n{'=' * 30}")
            output.append("QUALITY ASSESSMENT:")
            output.append(f"{'=' * 30}")
            
            for field, value in quality.items():
                if value:
                    output.append(f"\n{field.replace('_', ' ').title()}:")
                    if isinstance(value, list):
                        for item in value:
                            output.append(f"  • {item}")
                    else:
                        output.append(f"  {value}")

        flags = metadata.get('validation_flags', {})
        if any(flags.values()):
            output.append(f"\n{'=' * 30}")
            output.append("VALIDATION FLAGS:")
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

        if "avalon_batch" in formats:
            batch_path = f"{output_path}_{timestamp}_avalon_batch.csv"
            self._save_avalon_batch_csv(metadata, batch_path)
            print(f"Saved Avalon batch CSV to: {batch_path}")
    
    def _save_metadata_csv(self, metadata: Dict, filepath: str):        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Section', 'Field', 'Value', 'Confidence', 'Authority', 'Reasoning'])
            
            avalon_mods = metadata.get('avalon_mods_metadata', {})
            
            sections = [
                ('Required Fields', avalon_mods.get('required_fields', {})),
                ('Core Descriptive', avalon_mods.get('core_descriptive', {})),
                ('Subject Access', avalon_mods.get('subject_access', {})),
                ('Additional Fields', avalon_mods.get('additional_fields', {}))
            ]
            
            for section_name, section_data in sections:
                for field, data in section_data.items():
                    if field == 'notes' and isinstance(data, list):
                        for note in data:
                            if note.get('note_value'):
                                writer.writerow([
                                    section_name,
                                    f"note_{note.get('note_type', 'general')}",
                                    note['note_value'],
                                    note.get('confidence', ''),
                                    '',
                                    note.get('reasoning', '')
                                ])
                    elif isinstance(data, dict) and data.get('value'):
                        value = data['value']
                        if isinstance(value, list):
                            value = '; '.join(str(v) for v in value)
                        
                        writer.writerow([
                            section_name,
                            field,
                            str(value),
                            data.get('confidence', ''),
                            data.get('authority', ''),
                            data.get('reasoning', '')
                        ])

    def _save_avalon_batch_csv(self, metadata: Dict, filepath: str):
        """Save metadata in Avalon batch import CSV format"""
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            headers = [
                'Title', 'Creator', 'Contributor', 'Genre', 'Publisher', 
                'Date Created', 'Date Issued', 'Abstract', 'Language',
                'Physical Description', 'Series', 'Related Item Label', 'Related Item URL',
                'Topical Subject', 'Geographic Subject', 'Temporal Subject',
                'Table of Contents', 'Statement of Responsibility', 'Note', 'Note Type',
                'Terms of Use'
            ]
            
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            avalon_mods = metadata.get('avalon_mods_metadata', {})
            required = avalon_mods.get('required_fields', {})
            core = avalon_mods.get('core_descriptive', {})
            subjects = avalon_mods.get('subject_access', {})
            additional = avalon_mods.get('additional_fields', {})
            
            def get_field_value(field_data):
                if isinstance(field_data, dict):
                    value = field_data.get('value', '')
                    if isinstance(value, list):
                        return '; '.join(str(v) for v in value)
                    return str(value) if value else ''
                return ''
            
            row = [
                get_field_value(required.get('title', {})),
                get_field_value(core.get('main_contributor_creator', {})),
                get_field_value(core.get('contributor', {})),
                get_field_value(core.get('genre', {})),
                get_field_value(core.get('publisher', {})),
                get_field_value(core.get('creation_date', {})),
                get_field_value(required.get('date_issued', {})),
                get_field_value(core.get('summary_abstract', {})),
                get_field_value(core.get('language', {})),
                get_field_value(additional.get('physical_description', {})),
                get_field_value(additional.get('series', {})),
                get_field_value(subjects.get('topical_subject', {})),
                get_field_value(subjects.get('geographic_subject', {})),
                get_field_value(subjects.get('temporal_subject', {})),
                get_field_value(additional.get('table_of_contents', {})),
                get_field_value(additional.get('statement_of_responsibility', {})),
                '',  #TODO: Note - would need to combine multiple notes
                '',  #TODO: Note Type - would need to handle multiple note types
            ]
            #TODO: Update original prompt to not include stuff we don't need to reduce tokens.
            # Handle notes specially (combine into single field for simplicity)
            notes_data = additional.get('notes', [])
            if notes_data and isinstance(notes_data, list):
                note_texts = []
                note_types = []
                for note in notes_data:
                    if note.get('note_value'):
                        note_texts.append(note['note_value'])
                        note_types.append(note.get('note_type', 'general'))
                
                if note_texts:
                    row[-3] = ' | '.join(note_texts)  # Note field
                    row[-2] = ' | '.join(note_types)  # Note Type field
            
            writer.writerow(row)

    def get_avalon_batch_template(self) -> Dict[str, str]:
        """Return a template dictionary for Avalon batch import"""
        return {
            'Title': '',
            'Creator': '',
            'Contributor': '', 
            'Genre': '',
            'Publisher': '',
            'Date Created': '',
            'Date Issued': '',
            'Abstract': '',
            'Language': '',
            'Physical Description': '',
            'Series': '',
            'Related Item Label': '',
            'Related Item URL': '',
            'Topical Subject': '',
            'Geographic Subject': '',
            'Temporal Subject': '',
            'Table of Contents': '',
            'Statement of Responsibility': '',
            'Note': '',
            'Note Type': '',
            'Terms of Use': ''
        }

    def extract_avalon_fields(self, metadata: Dict) -> Dict[str, str]:
        """Extract metadata into Avalon field format for easier processing"""
        if "error" in metadata:
            return {"error": metadata["error"]}
        
        avalon_fields = self.get_avalon_batch_template()
        avalon_mods = metadata.get('avalon_mods_metadata', {})
        
        required = avalon_mods.get('required_fields', {})
        core = avalon_mods.get('core_descriptive', {})
        subjects = avalon_mods.get('subject_access', {})
        additional = avalon_mods.get('additional_fields', {})
        
        def extract_value(field_data):
            if isinstance(field_data, dict):
                value = field_data.get('value', '')
                if isinstance(value, list):
                    return '; '.join(str(v) for v in value)
                return str(value) if value else ''
            return ''
        
        field_mapping = {
            'Title': extract_value(required.get('title', {})),
            'Creator': extract_value(core.get('main_contributor_creator', {})),
            'Contributor': extract_value(core.get('contributor', {})),
            'Genre': extract_value(core.get('genre', {})),
            'Publisher': extract_value(core.get('publisher', {})),
            'Date Created': extract_value(core.get('creation_date', {})),
            'Date Issued': extract_value(required.get('date_issued', {})),
            'Abstract': extract_value(core.get('summary_abstract', {})),
            'Language': extract_value(core.get('language', {})),
            'Physical Description': extract_value(additional.get('physical_description', {})),
            'Series': extract_value(additional.get('series', {})),
            'Topical Subject': extract_value(subjects.get('topical_subject', {})),
            'Geographic Subject': extract_value(subjects.get('geographic_subject', {})),
            'Temporal Subject': extract_value(subjects.get('temporal_subject', {})),
            'Table of Contents': extract_value(additional.get('table_of_contents', {})),
            'Statement of Responsibility': extract_value(additional.get('statement_of_responsibility', {}))
        }
        
        for field, value in field_mapping.items():
            if value:
                avalon_fields[field] = value
        
        return avalon_fields
    

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
                 model="claude-3-5-haiku-20241022"):
        """Generates a Claude Image analysis object.
        
        Args:
            image_path (str): Path to the image file (optional, for reference).
            existing_metadata (str): The existing metadata text to analyze.
            material_type (str): Type of material - MAP, PHOTOGRAPH, DRAWING, PAINTING, PRINT, etc.
            api_key (Optional[str] or None): Your Claude API Key.
            model (str): Claude model to use.
        """
        super().__init__(api_key)
        self.image_path = image_path
        self.existing_metadata = existing_metadata
        self.material_type = material_type.upper()
        self.model = model
        self.prompt = self._format_prompt()

    def _format_prompt(self):
        """Format the prompt with existing metadata and material type
        
        Returns:
            str: The formatted prompt ready for Claude
        """
        prompt_template = self.get_prompt("maps.md")
        
        formatted_prompt = prompt_template.replace("[INSERT EXISTING METADATA HERE]", self.existing_metadata)
        formatted_prompt = formatted_prompt.replace("[MAP | PHOTOGRAPH | DRAWING | PAINTING | PRINT | OTHER IMAGE TYPE]", self.material_type)
        
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
            
            self._store_response_data(response, model)

            response_text = response.content[0].text.strip()
            
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
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    analysis = json.loads(json_str)
                    return response_text, analysis
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in analysis: {e}")
                    return response_text, {"error": "Could not parse JSON response"}
            else:
                print("No JSON object found in analysis response")
                return response_text, {"error": "No JSON object found in response"}
                
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

    img = ClaudeImage(
        image_path="test.jpg",
        existing_metadata="Title: To Belgium and back with the 79th Infantry Division, 31 Aug to 25 Oct, 1944, Theater: European",
        material_type="MAP"
    )
    response, metadata = img.analyze_image_only("test.jpg")
    print(metadata)

    print(response)

