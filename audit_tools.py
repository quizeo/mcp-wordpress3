#!/usr/bin/env python3
"""
WordPress MCP Tools Audit
Comprehensive audit of all tools in the WordPress MCP server
"""

import re
import os

def audit_tools():
    """Audit all tools in both files"""
    print("🔍 WordPress MCP Tools Audit")
    print("="*50)
    
    # Check main file
    main_file = "wordpress_mcp_https.py"
    if os.path.exists(main_file):
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all @mcp.tool() decorators and their function names
        pattern = r'@mcp\.tool\(\)\s*(?:async\s+)?def\s+(\w+)'
        main_tools = re.findall(pattern, content)
        
        print(f"📄 {main_file}:")
        print(f"   Tools found: {len(main_tools)}")
        for i, tool in enumerate(main_tools, 1):
            print(f"   {i:2d}. {tool}")
    
    print()
    
    # Check additional file
    additional_file = "additional_wordpress_tools.py"
    if os.path.exists(additional_file):
        with open(additional_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all @mcp.tool() decorators and their function names
        pattern = r'@mcp\.tool\(\)\s*(?:async\s+)?def\s+(\w+)'
        additional_tools = re.findall(pattern, content)
        
        print(f"📄 {additional_file}:")
        print(f"   Tools found: {len(additional_tools)}")
        for i, tool in enumerate(additional_tools, 1):
            print(f"   {i:2d}. {tool}")
    
    print()
    print("="*50)
    print(f"📊 TOTAL TOOLS: {len(main_tools) + len(additional_tools)}")
    
    # Verify registration function
    if 'register_additional_tools' in content:
        print("✅ Additional tools registration function found")
    else:
        print("❌ Additional tools registration function NOT found")
    
    return len(main_tools) + len(additional_tools)

if __name__ == "__main__":
    total_tools = audit_tools()
    
    print(f"\n🎯 Expected in Claude Desktop: {total_tools} tools")
    print("📝 Note: If Claude Desktop shows a different number:")
    print("   • Try disconnecting and reconnecting the connector")
    print("   • Check if all tools are actually being used correctly")
    print("   • The number '40' might actually be correct!")
