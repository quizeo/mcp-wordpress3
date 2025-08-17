"""
Render Deployment Validation Script

This script helps validate that your WordPress MCP server is ready for Render deployment.
"""

import json
import os
from pathlib import Path

def check_files():
    """Check if all required files exist"""
    required_files = [
        "Dockerfile",
        "render.yaml", 
        "wordpress_mcp_https.py",
        "setup_render.py",
        "pyproject.toml",
        "mcp-wordpress.config.json"
    ]
    
    print("🔍 Checking required files...")
    missing_files = []
    
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    return len(missing_files) == 0

def check_config():
    """Check WordPress configuration"""
    print("\n🔍 Checking WordPress configuration...")
    
    config_file = Path("mcp-wordpress.config.json")
    if not config_file.exists():
        print("❌ mcp-wordpress.config.json not found")
        return False
    
    try:
        with open(config_file) as f:
            config = json.load(f)
        
        sites = config.get("sites", [])
        if not sites:
            print("⚠️  No WordPress sites configured in config file")
            print("   💡 You can configure sites via Render environment variables instead")
        else:
            print(f"✅ Found {len(sites)} WordPress sites in config")
            for site in sites:
                name = site.get("name", "Unknown")
                url = site.get("config", {}).get("WORDPRESS_SITE_URL", "Unknown")
                print(f"   📧 {name}: {url}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return False

def check_environment_config():
    """Check environment variable configuration"""
    print("\n🔍 Checking environment variable setup...")
    
    # Check for WordPress sites in environment
    site_count = 0
    i = 1
    while True:
        site_url = os.environ.get(f"WORDPRESS_SITE_URL_{i}")
        if not site_url:
            break
        
        username = os.environ.get(f"WORDPRESS_USERNAME_{i}")
        password = os.environ.get(f"WORDPRESS_APP_PASSWORD_{i}")
        
        if username and password:
            print(f"✅ WordPress site {i} configured in environment")
            site_count += 1
        else:
            print(f"⚠️  WordPress site {i} incomplete in environment")
        
        i += 1
    
    # Check API key
    api_key = os.environ.get("MCP_API_KEY")
    if api_key:
        print("✅ MCP_API_KEY configured in environment")
    else:
        print("⚠️  MCP_API_KEY not set (will be auto-generated)")
    
    if site_count > 0:
        print(f"✅ Found {site_count} WordPress sites in environment variables")
    else:
        print("⚠️  No WordPress sites configured in environment variables")
    
    return True

def generate_deployment_summary():
    """Generate deployment summary"""
    print("\n📋 Render Deployment Summary")
    print("=" * 50)
    
    # Count WordPress sites
    total_sites = 0
    
    # From config file
    config_file = Path("mcp-wordpress.config.json")
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            config_sites = len(config.get("sites", []))
            total_sites += config_sites
        except:
            config_sites = 0
    else:
        config_sites = 0
    
    # From environment
    env_sites = 0
    i = 1
    while True:
        if os.environ.get(f"WORDPRESS_SITE_URL_{i}"):
            env_sites += 1
            i += 1
        else:
            break
    
    if env_sites > 0:
        total_sites = env_sites  # Environment takes precedence
    
    print(f"🌐 WordPress sites: {total_sites}")
    print(f"📁 Config file sites: {config_sites}")
    print(f"🔧 Environment sites: {env_sites}")
    print(f"🔑 API key: {'Set' if os.environ.get('MCP_API_KEY') else 'Auto-generated'}")
    print(f"🚀 Ready for deployment: {'Yes' if total_sites > 0 else 'Configure WordPress sites first'}")

def main():
    """Main validation function"""
    print("🚀 WordPress MCP Server - Render Deployment Validation")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Check files
    if not check_files():
        all_checks_passed = False
    
    # Check configuration
    if not check_config():
        all_checks_passed = False
    
    # Check environment
    check_environment_config()
    
    # Generate summary
    generate_deployment_summary()
    
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✅ All validation checks passed!")
        print("\n🚀 Next Steps:")
        print("1. Commit and push your code to GitHub")
        print("2. Create a new Web Service on Render")
        print("3. Connect your GitHub repository")
        print("4. Set environment variables in Render dashboard")
        print("5. Deploy and test!")
        print("\n📖 See RENDER_DEPLOYMENT_GUIDE.md for detailed instructions")
    else:
        print("❌ Some validation checks failed!")
        print("🔧 Fix the issues above before deploying to Render")

if __name__ == "__main__":
    main()
