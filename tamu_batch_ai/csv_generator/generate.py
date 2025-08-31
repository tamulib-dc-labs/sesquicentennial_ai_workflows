import json
import os
import csv
from collections import defaultdict
import pandas as pd

def extract_all_keys(obj, prefix="", keys_set=None):
    """
    Recursively extract all keys from a nested JSON object.
    Creates flattened key paths like 'content_analysis.media_type'
    """
    if keys_set is None:
        keys_set = set()
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_key = f"{prefix}.{key}" if prefix else key
            keys_set.add(current_key)
            extract_all_keys(value, current_key, keys_set)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            list_key = f"{prefix}[{i}]" if prefix else f"[{i}]"
            extract_all_keys(item, list_key, keys_set)
    
    return keys_set

def flatten_json(obj, prefix=""):
    """
    Flatten a nested JSON object into a single-level dictionary
    """
    flattened = {}
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)) and value:
                flattened.update(flatten_json(value, current_key))
            else:
                if isinstance(value, list):
                    flattened[current_key] = "; ".join(map(str, value))
                elif isinstance(value, dict):
                    flattened[current_key] = str(value)
                else:
                    flattened[current_key] = value
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            list_key = f"{prefix}[{i}]" if prefix else f"[{i}]"
            if isinstance(item, (dict, list)):
                flattened.update(flatten_json(item, list_key))
            else:
                flattened[list_key] = item
    
    return flattened

def process_json_directory(directory_path, output_csv="output.csv"):
    all_keys = set()
    json_data = []
    
    print("Scanning for unique keys...")
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_keys = extract_all_keys(data)
                    all_keys.update(file_keys)
                    print(f"Processed {filename}: {len(file_keys)} keys")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    print(f"\nFound {len(all_keys)} unique keys total")
    
    print("\nFlattening JSON files...")
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    flattened = flatten_json(data)
                    flattened['_filename'] = filename
                    json_data.append(flattened)
            except Exception as e:
                print(f"Error flattening {filename}: {e}")
    
    print(f"\nCreating CSV with {len(json_data)} records...")
    df = pd.DataFrame(json_data)
    
    df = df.fillna('')
    
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"CSV saved as {output_csv}")
    
    return df, sorted(all_keys)

def process_json_directory_csv_only(directory_path, output_csv="output.csv"):
    """
    Same functionality but using only built-in csv module
    """
    all_keys = set()
    json_data = []
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_keys = extract_all_keys(data)
                    all_keys.update(file_keys)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    sorted_keys = ['_filename'] + sorted(all_keys)
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    flattened = flatten_json(data)
                    flattened['_filename'] = filename
                    json_data.append(flattened)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=sorted_keys, extrasaction='ignore')
        writer.writeheader()
        for row in json_data:
            complete_row = {key: row.get(key, '') for key in sorted_keys}
            writer.writerow(complete_row)
    
    return sorted_keys


if __name__ == "__main__":
    directory = "tmp"
    
    df, unique_keys = process_json_directory(
        directory, 
        "flattened_data.csv"
    )
