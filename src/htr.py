import os
import sys
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import anthropic
from PIL import Image
import pandas as pd
import re
import ast


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
                # TODO: Model should be defineable -- not hardcoded
                model="claude-3-5-haiku-20241022",
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
    def __init__(self, pages=None, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.pages = pages if pages is not None else []
        self.full_text, self.full_page_responses = self.get_page_text()
        self.prompt = self.get_prompt("metadata.md").replace("[INSERT LETTER TEXT HERE]", self.full_text)

    def get_page_text(self):
        just_the_text = []
        full_response = []
        for page in self.pages:
            claude_page = ClaudePage()
            claude_page_text = claude_page.extract_text_with_claude(page)
            just_the_text.append(claude_page_text[0])
            full_response.append(claude_page_text[1])
        return "\n\n".join(just_the_text), full_response
    
    def get_metadata(self):
        response = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": self.prmopt}
            ]
        )
    

if __name__ == "__main__":
    x = ClaudePage()
    # y = x.encode_image("test_files/amctrial_mcinnis_0004.jpg")
    # print(y)
    # y = x.extract_text_with_claude("test_files/amctrial_mcinnis_0004.jpg")
    # print(y)
    # x = ClaudeBase()
    # print(x.get_prompt("htr.md"))
