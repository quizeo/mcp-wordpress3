#!/usr/bin/env python3
"""
Script to fix all client = wp_manager.get_client(site_id) calls to use async context managers
"""

import re

def fix_context_managers(file_path):
    """Fix all non-context manager client calls in a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match the problematic calls
    # Look for: site_id = wp_manager.get_site_id(site)
    #           client = wp_manager.get_client(site_id)
    #           ... code that uses client ...
    
    # This is a complex regex replacement, so let's do it step by step
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Look for the pattern: client = wp_manager.get_client(site_id)
        if 'client = wp_manager.get_client(site_id)' in line:
            # This line needs to be replaced with async context manager
            indent = len(line) - len(line.lstrip())
            
            # Find the end of the try block to know where to place the async with
            j = i + 1
            client_usage_lines = []
            
            # Collect all lines that use the client until we hit except
            while j < len(lines) and 'except Exception as e:' not in lines[j]:
                if lines[j].strip():  # Skip empty lines
                    client_usage_lines.append(lines[j])
                j += 1
            
            # Replace the client assignment with async context manager
            new_lines.append(' ' * indent + 'async with wp_manager.get_client(site_id) as client:')
            
            # Add the client usage lines with additional indent
            for usage_line in client_usage_lines:
                if usage_line.strip():  # Skip empty lines
                    new_lines.append('    ' + usage_line)
                else:
                    new_lines.append(usage_line)
            
            i = j  # Skip to the except line
        else:
            new_lines.append(line)
            i += 1
    
    # Write the fixed content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

if __name__ == '__main__':
    fix_context_managers('additional_wordpress_tools.py')
    print("Fixed context managers in additional_wordpress_tools.py")
