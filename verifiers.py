#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import subprocess
from PIL import Image

def check_file_exists(file_path):
    """Checks if a file exists on the filesystem."""
    exists = os.path.exists(file_path)
    print(f"[*] Verifier: Checking if {file_path} exists -> {exists}")
    return exists

def check_file_size(file_path, min_bytes=100):
    """Checks if a file exists and has size >= min_bytes."""
    if not os.path.exists(file_path):
        print(f"[-] Verifier: File {file_path} does not exist.")
        return False
    size = os.path.getsize(file_path)
    ok = size >= min_bytes
    print(f"[*] Verifier: Checking size of {file_path} ({size} bytes) >= {min_bytes} -> {ok}")
    return ok

def check_python_test(test_script_path, cwd=None):
    """Runs a Python script (like a unit test) and verifies if it exits with code 0."""
    if not os.path.exists(test_script_path):
        print(f"[-] Verifier: Test script {test_script_path} not found.")
        return False
    print(f"[*] Verifier: Running test script {test_script_path}...")
    try:
        res = subprocess.run([sys.executable, test_script_path], capture_output=True, text=True, cwd=cwd, timeout=60)
        ok = res.returncode == 0
        print(f"[*] Verifier: Exit code {res.returncode}. Output:\n{res.stdout}\nErrors:\n{res.stderr}")
        return ok
    except Exception as e:
        print(f"[-] Verifier Error: Exception running test: {e}")
        return False

def check_image_corrupted(image_path):
    """Verifies that an image exists and can be loaded successfully without corruption."""
    if not os.path.exists(image_path):
        return False
    try:
        with Image.open(image_path) as img:
            img.verify()
        print(f"[*] Verifier: Image {image_path} verified successfully.")
        return True
    except Exception as e:
        print(f"[-] Verifier: Image {image_path} is corrupted or invalid. Error: {e}")
        return False

def check_layout_overlaps(bbox_json_path):
    """
    Checks if bounding boxes inside a JSON file overlap.
    Expected JSON structure: { "filename": [ { "bbox": [[x,y], ...], "translated": "text" }, ... ] }
    Or list of items with "bbox" field.
    """
    if not os.path.exists(bbox_json_path):
        print(f"[-] Verifier: Bounding box JSON {bbox_json_path} not found.")
        return False
        
    try:
        with open(bbox_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        def get_rect(bbox):
            # Convert 4 corner pts [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] to min/max box
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            return [min(xs), min(ys), max(xs), max(ys)]
            
        def has_overlap(r1, r2):
            # Check overlap between two rectangles: [x1, y1, x2, y2]
            # Add 2px margin tolerance
            if r1[2] <= r2[0] + 2 or r1[0] + 2 >= r2[2]:
                return False
            if r1[3] <= r2[1] + 2 or r1[1] + 2 >= r2[3]:
                return False
            return True

        overlaps_found = 0
        
        # Structure could be dict or list
        if isinstance(data, dict):
            for file, items in data.items():
                rects = []
                for item in items:
                    if "bbox" in item:
                        rects.append((item.get("translated", "text"), get_rect(item["bbox"])))
                
                # Compare all pairs
                for i in range(len(rects)):
                    for j in range(i + 1, len(rects)):
                        if has_overlap(rects[i][1], rects[j][1]):
                            print(f"[-] Layout Overlap detected in {file} between:\n    '{rects[i][0]}' and '{rects[j][0]}'")
                            overlaps_found += 1
        elif isinstance(data, list):
            rects = []
            for item in data:
                if "bbox" in item:
                    rects.append((item.get("translated", "text"), get_rect(item["bbox"])))
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    if has_overlap(rects[i][1], rects[j][1]):
                        print(f"[-] Layout Overlap detected between:\n    '{rects[i][0]}' and '{rects[j][0]}'")
                        overlaps_found += 1
                        
        if overlaps_found > 0:
            print(f"[-] Verifier: Total {overlaps_found} overlaps detected.")
            return False
            
        print("[*] Verifier: Layout verified. No overlapping text boxes detected.")
        return True
    except Exception as e:
        print(f"[-] Verifier Error: Exception checking layouts: {e}")
        return False

def check_python_syntax(file_path):
    """Parses a Python file using AST to ensure there are no syntax errors."""
    if not os.path.exists(file_path):
        print(f"[-] Verifier: Python file {file_path} not found.")
        return False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        import ast
        ast.parse(source)
        print(f"[*] Verifier: AST syntax check for {file_path} PASSED.")
        return True
    except SyntaxError as e:
        print(f"[-] Verifier: Syntax error in {file_path}:\n    Line {e.lineno}: {e.msg}\n    Code: {e.text.strip() if e.text else ''}")
        return False
    except Exception as e:
        print(f"[-] Verifier: Error parsing syntax for {file_path}: {e}")
        return False

if __name__ == "__main__":
    # Test verifier functions if run directly
    print("[*] Verifiers library loaded.")
