# Deployment script for Render environment
import os
import json
from pathlib import Path

def setup_render_config():
    """Setup configuration for Render deployment"""
    
    # Load existing config or create new one
    config_file = Path("mcp-wordpress.config.json")
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {"sites": []}
    
    # Check for environment-based WordPress sites
    sites_from_env = []
    i = 1
    while True:
        site_url = os.environ.get(f"WORDPRESS_SITE_URL_{i}")
        if not site_url:
            break
            
        username = os.environ.get(f"WORDPRESS_USERNAME_{i}")
        app_password = os.environ.get(f"WORDPRESS_APP_PASSWORD_{i}")
        auth_method = os.environ.get(f"WORDPRESS_AUTH_METHOD_{i}", "app-password")
        site_name = os.environ.get(f"WORDPRESS_SITE_NAME_{i}", f"Site {i}")
        
        if username and app_password:
            site_config = {
                "id": f"site-{i}",
                "name": site_name,
                "config": {
                    "WORDPRESS_SITE_URL": site_url,
                    "WORDPRESS_USERNAME": username,
                    "WORDPRESS_APP_PASSWORD": app_password,
                    "WORDPRESS_AUTH_METHOD": auth_method
                }
            }
            sites_from_env.append(site_config)
            print(f"✅ Added WordPress site from environment: {site_name} ({site_url})")
        
        i += 1
    
    # Use environment sites if available, otherwise keep existing
    if sites_from_env:
        config["sites"] = sites_from_env
        print(f"📊 Configured {len(sites_from_env)} WordPress sites from environment variables")
    elif config.get("sites"):
        print(f"📊 Using {len(config['sites'])} WordPress sites from config file")
    else:
        print("⚠️  No WordPress sites configured. Add sites via environment variables or config file.")
    
    # Update server configuration for Render
    config["server"] = {
        "host": "0.0.0.0",
        "port": int(os.environ.get("PORT", 10000)),
        "ssl_cert_path": None,
        "ssl_key_path": None,
        "api_key": os.environ.get("MCP_API_KEY"),
        "cors_origins": [
            "https://claude.ai",
            "https://app.claude.ai", 
            "*"  # Allow all for development
        ],
        "mount_path": "/mcp"
    }
    
    # Save updated configuration
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Render configuration updated")
    print(f"🌐 Server will run on port: {config['server']['port']}")
    print(f"🔑 API Key: {config['server']['api_key'] or 'Will be auto-generated'}")
    print(f"🔗 MCP Endpoint: http://0.0.0.0:{config['server']['port']}/mcp")

if __name__ == "__main__":
    setup_render_config()
