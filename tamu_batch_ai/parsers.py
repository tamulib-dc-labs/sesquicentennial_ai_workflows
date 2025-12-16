"""Parsers for different response formats (TOON, JSON)."""

import json
import re
from typing import Any, Dict


class TOONParser:
    """Parser for Token Object Notation (TOON) format.

    TOON is a more compact representation than JSON, saving tokens:

    Example TOON:
        title|
          val: Letter from John
          conf: high
          why: Found in header
        subjects: [War, Politics]

    Equivalent JSON:
        {
            "title": {
                "val": "Letter from John",
                "conf": "high",
                "why": "Found in header"
            },
            "subjects": ["War", "Politics"]
        }
    """

    @staticmethod
    def parse(toon_text: str) -> Dict[str, Any]:
        """Parse TOON format text into a Python dictionary.

        Args:
            toon_text: Text in TOON format

        Returns:
            Parsed dictionary
        """
        lines = toon_text.strip().split('\n')
        result = {}
        stack = [(result, -1)]  # (current_dict, indent_level)

        for line in lines:
            if not line.strip():
                continue

            # Calculate indentation
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()

            # Skip empty or comment lines
            if not stripped or stripped.startswith('#'):
                continue

            # Pop stack until we find the right parent level
            while stack and stack[-1][1] >= indent:
                stack.pop()

            current_dict = stack[-1][0] if stack else result

            # Parse key-value pair
            if ':' in stripped:
                key, value = stripped.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Check if this is a nested object (ends with |)
                if key.endswith('|'):
                    key = key[:-1].strip()
                    nested_dict = {}
                    current_dict[key] = nested_dict
                    stack.append((nested_dict, indent))
                else:
                    # Parse the value
                    parsed_value = TOONParser._parse_value(value)
                    current_dict[key] = parsed_value

        return result

    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse a TOON value into appropriate Python type.

        Args:
            value: String value to parse

        Returns:
            Parsed value (str, list, bool, etc.)
        """
        value = value.strip()

        # Empty value
        if not value:
            return ""

        # Array notation [item1, item2, ...]
        if value.startswith('[') and value.endswith(']'):
            items_str = value[1:-1].strip()
            if not items_str:
                return []
            items = [item.strip() for item in items_str.split(',')]
            return items

        # Boolean values
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False

        # Null/None
        if value.lower() in ('null', 'none'):
            return None

        # Number (int or float)
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Default to string
        return value


class ResponseParser:
    """Unified parser for Claude API responses."""

    @staticmethod
    def parse_response(response_text: str, format_hint: str = "auto") -> Dict[str, Any]:
        """Parse a Claude API response in JSON or TOON format.

        Args:
            response_text: Raw response text from Claude
            format_hint: Format hint - "json", "toon", or "auto" to detect

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If parsing fails
        """
        response_text = response_text.strip()

        # Auto-detect format if needed
        if format_hint == "auto":
            format_hint = ResponseParser._detect_format(response_text)

        if format_hint == "json":
            return ResponseParser._parse_json(response_text)
        elif format_hint == "toon":
            return ResponseParser._parse_toon(response_text)
        else:
            # Try JSON first, then TOON
            try:
                return ResponseParser._parse_json(response_text)
            except (json.JSONDecodeError, ValueError):
                return ResponseParser._parse_toon(response_text)

    @staticmethod
    def _detect_format(text: str) -> str:
        """Detect if text is JSON or TOON format.

        Args:
            text: Response text

        Returns:
            "json" or "toon"
        """
        # Look for JSON markers
        if re.search(r'^\s*\{', text, re.MULTILINE):
            return "json"

        # Look for TOON markers (key: value or key|)
        if re.search(r'^\w+(\|)?:\s*', text, re.MULTILINE):
            return "toon"

        # Default to JSON
        return "json"

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Extract and parse JSON from response text.

        Args:
            text: Response text potentially containing JSON

        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in code blocks first
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}")

    @staticmethod
    def _parse_toon(text: str) -> Dict[str, Any]:
        """Extract and parse TOON from response text.

        Args:
            text: Response text potentially containing TOON

        Returns:
            Parsed TOON dictionary
        """
        # Try to find TOON in code blocks
        toon_match = re.search(r'```(?:toon)?\s*(.*?)\s*```', text, re.DOTALL)
        if toon_match:
            toon_str = toon_match.group(1)
        else:
            # Use the whole text
            toon_str = text

        return TOONParser.parse(toon_str)
