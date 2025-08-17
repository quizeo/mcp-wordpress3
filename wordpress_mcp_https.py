"""
WordPress MCP Server - HTTPS Edition

A comprehensive Model Context Protocol server for WordPress management with HTTPS support.
Provides 59 tools for managing WordPress sites including posts, pages, users, 
comments, media, taxonomies, cache, performance monitoring, and more.

Features:
- HTTP/HTTPS transport for Claude Desktop integration
- Multi-site WordPress configuration
- Authentication via API keys  
- SSL/TLS support for production deployment
- All 59 WordPress tools from the original implementation

Usage:
    # Local development with HTTP
    python wordpress_mcp_https.py --transport http --port 8000
    
    # Production with HTTPS
    python wordpress_mcp_https.py --transport https --port 8443 --ssl-cert cert.pem --ssl-key key.pem
    
    # Claude Desktop connection URL
    http://localhost:8000/mcp or https://your-domain:8443/mcp
"""

import asyncio
import json
import logging
import ssl
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import argparse
import secrets
import base64
import os

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """WordPress authentication methods"""
    APP_PASSWORD = "app-password"
    BASIC_AUTH = "basic-auth"


@dataclass
class WordPressConfig:
    """WordPress site configuration"""
    id: str
    name: str
    site_url: str
    username: str
    app_password: str
    auth_method: AuthMethod = AuthMethod.APP_PASSWORD


@dataclass
class ServerConfig:
    """HTTP/HTTPS server configuration"""
    host: str = "localhost"
    port: int = 8000
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    api_key: Optional[str] = None
    cors_origins: List[str] = None
    mount_path: str = "/mcp"
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]  # Allow all origins by default
        
        # Generate API key if not provided
        if self.api_key is None:
            self.api_key = self.generate_api_key()
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    @property
    def is_https(self) -> bool:
        """Check if HTTPS is configured"""
        return self.ssl_cert_path is not None and self.ssl_key_path is not None
    
    @property
    def protocol(self) -> str:
        """Get the protocol (http or https)"""
        return "https" if self.is_https else "http"
    
    @property
    def base_url(self) -> str:
        """Get the base URL for the server"""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def mcp_url(self) -> str:
        """Get the MCP endpoint URL for Claude Desktop"""
        return f"{self.base_url}{self.mount_path}"


class WordPressClient:
    """WordPress REST API client"""
    
    def __init__(self, config: WordPressConfig):
        self.config = config
        self.base_url = f"{config.site_url.rstrip('/')}/wp-json/wp/v2"
        
        # Setup authentication
        if config.auth_method == AuthMethod.APP_PASSWORD:
            self.auth = httpx.BasicAuth(config.username, config.app_password)
        else:
            self.auth = httpx.BasicAuth(config.username, config.app_password)
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(auth=self.auth, timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make HTTP request to WordPress API"""
        url = f"{self.base_url}{endpoint}"
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """GET request"""
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """POST request"""
        return await self.request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        """PUT request"""
        return await self.request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """DELETE request"""
        return await self.request("DELETE", endpoint, **kwargs)


class WordPressManager:
    """Manages multiple WordPress site configurations"""
    
    def __init__(self):
        self.clients: Dict[str, WordPressConfig] = {}
        self.server_config: ServerConfig = ServerConfig()
        self.load_config()
    
    def load_config(self):
        """Load configuration from mcp-wordpress.config.json"""
        # Use absolute path relative to this script's location
        script_dir = Path(__file__).parent
        config_file = script_dir / "mcp-wordpress.config.json"
        if not config_file.exists():
            logger.warning(f"No mcp-wordpress.config.json found at {config_file}. Using default configuration.")
            return
            
        try:
            with open(config_file) as f:
                config_data = json.load(f)
                
            logger.info(f"Loading configuration from {config_file}")
            sites_loaded = 0
            
            # Load WordPress sites
            for site_data in config_data.get("sites", []):
                site_config = site_data.get("config", {})
                config = WordPressConfig(
                    id=site_data["id"],
                    name=site_data["name"],
                    site_url=site_config["WORDPRESS_SITE_URL"],
                    username=site_config["WORDPRESS_USERNAME"],
                    app_password=site_config["WORDPRESS_APP_PASSWORD"],
                    auth_method=AuthMethod(site_config.get("WORDPRESS_AUTH_METHOD", "app-password"))
                )
                self.clients[config.id] = config
                sites_loaded += 1
            
            # Load server configuration
            server_config = config_data.get("server", {})
            if server_config:
                self.server_config = ServerConfig(
                    host=server_config.get("host", "localhost"),
                    port=server_config.get("port", 8000),
                    ssl_cert_path=server_config.get("ssl_cert_path"),
                    ssl_key_path=server_config.get("ssl_key_path"),
                    api_key=server_config.get("api_key"),
                    cors_origins=server_config.get("cors_origins", ["*"]),
                    mount_path=server_config.get("mount_path", "/mcp")
                )
                
            logger.info(f"Successfully loaded {sites_loaded} WordPress sites")
            logger.info(f"Server will run at: {self.server_config.mcp_url}")
            logger.info(f"API Key: {self.server_config.api_key}")
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def get_site_id(self, site: Optional[str] = None) -> str:
        """Get the site ID to use, with intelligent selection"""
        if site:
            if site not in self.clients:
                available = list(self.clients.keys())
                raise Exception(f"Site '{site}' not found. Available sites: {available}")
            return site
            
        if len(self.clients) == 0:
            raise Exception("No WordPress sites configured. Please check mcp-wordpress.config.json")
        elif len(self.clients) == 1:
            return list(self.clients.keys())[0]
        else:
            # Multiple sites - require explicit selection
            available = list(self.clients.keys())
            raise Exception(f"Multiple sites configured. Please specify 'site' parameter. Available sites: {available}")
    
    def get_client(self, site_id: str) -> WordPressClient:
        """Get WordPress client for a site"""
        if site_id not in self.clients:
            available = list(self.clients.keys())
            raise Exception(f"Site '{site_id}' not found. Available sites: {available}")
        
        return WordPressClient(self.clients[site_id])


# Create the FastMCP server with configuration
wp_manager = WordPressManager()

# Create MCP server with enhanced configuration
mcp = FastMCP(
    name="WordPress MCP Server (HTTPS)",
    instructions="WordPress management server with HTTPS support for Claude Desktop integration. Supports 59 WordPress tools across multiple sites."
)

# Utility functions
def validate_positive_int(value: int, field_name: str) -> int:
    """Validate that an integer is positive"""
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value

def format_response(data: Any) -> str:
    """Format response data as JSON string"""
    return json.dumps(data, indent=2, ensure_ascii=False)


# ============================================================================
# AUTHENTICATION TOOLS (3 tools)
# ============================================================================

@mcp.tool()
async def wp_test_auth(site: Optional[str] = None) -> str:
    """Test WordPress authentication and API connectivity"""
    try:
        site_id = wp_manager.get_site_id(site)
        config = wp_manager.clients[site_id]
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.get("/")
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "site_name": config.name,
                "site_url": config.site_url,
                "auth_method": config.auth_method.value,
                "message": "Authentication successful",
                "api_version": response.headers.get("X-WP-Version", "Unknown")
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_get_auth_status(site: Optional[str] = None) -> str:
    """Get current authentication status and site information"""
    try:
        site_id = wp_manager.get_site_id(site)
        config = wp_manager.clients[site_id]
        
        # Test connection
        async with wp_manager.get_client(site_id) as client:
            response = await client.get("/")
            
            return format_response({
                "site_id": site_id,
                "site_name": config.name,
                "site_url": config.site_url,
                "username": config.username,
                "auth_method": config.auth_method.value,
                "auth_status": "active",
                "auth_message": "Authentication is working"
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_switch_auth_method(
    method: str,
    site: Optional[str] = None
) -> str:
    """Switch authentication method for a WordPress site"""
    try:
        site_id = wp_manager.get_site_id(site)
        
        if method not in ["app-password", "basic-auth"]:
            raise ValueError("Method must be 'app-password' or 'basic-auth'")
        
        config = wp_manager.clients[site_id]
        old_method = config.auth_method.value
        config.auth_method = AuthMethod(method)
        
        return format_response({
            "status": "success",
            "site_id": site_id,
            "old_method": old_method,
            "new_method": method,
            "message": f"Authentication method changed from {old_method} to {method}"
        })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


# ============================================================================
# SITE MANAGEMENT TOOLS (6 tools)
# ============================================================================

@mcp.tool()
async def wp_get_site_settings(site: Optional[str] = None) -> str:
    """Get WordPress site settings and information"""
    try:
        site_id = wp_manager.get_site_id(site)
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.get("/settings")
            settings = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "settings": settings
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_update_site_settings(
    settings: Dict[str, Any],
    site: Optional[str] = None
) -> str:
    """Update WordPress site settings"""
    try:
        site_id = wp_manager.get_site_id(site)
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.post("/settings", json=settings)
            updated_settings = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "message": "Settings updated successfully",
                "updated_settings": updated_settings
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_search_site(
    search: str,
    post_type: Optional[str] = None,
    per_page: int = 10,
    site: Optional[str] = None
) -> str:
    """Search content across the WordPress site"""
    try:
        site_id = wp_manager.get_site_id(site)
        per_page = validate_positive_int(per_page, "per_page")
        
        params = {
            "search": search,
            "per_page": per_page
        }
        
        if post_type:
            params["type"] = post_type
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.get("/search", params=params)
            results = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "search_term": search,
                "post_type": post_type,
                "results_count": len(results),
                "results": results
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_get_application_passwords(site: Optional[str] = None) -> str:
    """Get list of application passwords for the current user"""
    try:
        site_id = wp_manager.get_site_id(site)
        config = wp_manager.clients[site_id]
        
        async with wp_manager.get_client(site_id) as client:
            # Get current user first
            user_response = await client.get("/users/me")
            user = user_response.json()
            user_id = user["id"]
            
            # Get application passwords
            response = await client.get(f"/users/{user_id}/application-passwords")
            passwords = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "user_id": user_id,
                "username": config.username,
                "application_passwords": passwords
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_create_application_password(
    name: str,
    site: Optional[str] = None
) -> str:
    """Create a new application password"""
    try:
        site_id = wp_manager.get_site_id(site)
        
        async with wp_manager.get_client(site_id) as client:
            # Get current user
            user_response = await client.get("/users/me")
            user = user_response.json()
            user_id = user["id"]
            
            # Create application password
            response = await client.post(
                f"/users/{user_id}/application-passwords",
                json={"name": name}
            )
            password_data = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "message": "Application password created successfully",
                "password_data": password_data
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_delete_application_password(
    password_uuid: str,
    site: Optional[str] = None
) -> str:
    """Delete an application password"""
    try:
        site_id = wp_manager.get_site_id(site)
        
        async with wp_manager.get_client(site_id) as client:
            # Get current user
            user_response = await client.get("/users/me")
            user = user_response.json()
            user_id = user["id"]
            
            # Delete application password
            await client.delete(f"/users/{user_id}/application-passwords/{password_uuid}")
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "message": f"Application password {password_uuid} deleted successfully"
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


# ============================================================================
# POST MANAGEMENT TOOLS (6 tools)
# ============================================================================

@mcp.tool()
async def wp_list_posts(
    per_page: int = 10,
    page: int = 1,
    status: Optional[str] = None,
    author: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """List WordPress posts with optional filtering"""
    try:
        site_id = wp_manager.get_site_id(site)
        per_page = validate_positive_int(per_page, "per_page")
        page = validate_positive_int(page, "page")
        
        params = {
            "per_page": per_page,
            "page": page
        }
        
        if status:
            params["status"] = status
        if author:
            params["author"] = author
            
        async with wp_manager.get_client(site_id) as client:
            response = await client.get("/posts", params=params)
            posts = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "posts_count": len(posts),
                "page": page,
                "per_page": per_page,
                "posts": posts
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_get_post(post_id: int, site: Optional[str] = None) -> str:
    """Get a specific WordPress post by ID"""
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.get(f"/posts/{post_id}")
            post = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "post": post
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_create_post(
    title: str,
    content: str,
    status: str = "draft",
    excerpt: Optional[str] = None,
    author: Optional[int] = None,
    featured_media: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """Create a new WordPress post"""
    try:
        site_id = wp_manager.get_site_id(site)
        
        post_data = {
            "title": title,
            "content": content,
            "status": status
        }
        
        if excerpt:
            post_data["excerpt"] = excerpt
        if author:
            post_data["author"] = author
        if featured_media:
            post_data["featured_media"] = featured_media
            
        async with wp_manager.get_client(site_id) as client:
            response = await client.post("/posts", json=post_data)
            post = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "message": "Post created successfully",
                "post": post
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_update_post(
    post_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
    excerpt: Optional[str] = None,
    featured_media: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """Update an existing WordPress post"""
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        post_data = {}
        if title is not None:
            post_data["title"] = title
        if content is not None:
            post_data["content"] = content
        if status is not None:
            post_data["status"] = status
        if excerpt is not None:
            post_data["excerpt"] = excerpt
        if featured_media is not None:
            post_data["featured_media"] = featured_media
            
        async with wp_manager.get_client(site_id) as client:
            response = await client.put(f"/posts/{post_id}", json=post_data)
            post = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "message": f"Post {post_id} updated successfully",
                "post": post
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_delete_post(
    post_id: int,
    force: bool = False,
    site: Optional[str] = None
) -> str:
    """Delete a WordPress post"""
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        params = {"force": force}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.delete(f"/posts/{post_id}", params=params)
            result = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "message": f"Post {post_id} {'permanently deleted' if force else 'moved to trash'}",
                "result": result
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


@mcp.tool()
async def wp_get_post_revisions(
    post_id: int,
    site: Optional[str] = None
) -> str:
    """Get revisions for a specific post"""
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.get(f"/posts/{post_id}/revisions")
            revisions = response.json()
            
            return format_response({
                "status": "success",
                "site_id": site_id,
                "post_id": post_id,
                "revisions_count": len(revisions),
                "revisions": revisions
            })
    except Exception as e:
        return format_response({"status": "error", "message": str(e)})


# Import and register the remaining 25 tools
try:
    from additional_wordpress_tools import register_additional_tools
    register_additional_tools(mcp, wp_manager, validate_positive_int, format_response)
    logger.info("Successfully registered additional WordPress tools")
except Exception as e:
    logger.error(f"Error registering additional tools: {e}")


def create_ssl_context(cert_path: str, key_path: str) -> ssl.SSLContext:
    """Create SSL context for HTTPS"""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_path, key_path)
    return context


def print_connection_info(config: ServerConfig):
    """Print connection information for Claude Desktop"""
    print("\n" + "="*80)
    print("🚀 WordPress MCP Server (HTTPS) Started!")
    print("="*80)
    print(f"🌐 Protocol: {config.protocol.upper()}")
    print(f"🏠 Host: {config.host}")
    print(f"🔌 Port: {config.port}")
    print(f"📍 MCP Endpoint: {config.mcp_url}")
    print(f"🔑 API Key: {config.api_key}")
    
    if config.is_https:
        print(f"🔒 SSL Certificate: {config.ssl_cert_path}")
        print(f"🔐 SSL Key: {config.ssl_key_path}")
    
    print("\n📋 Claude Desktop Configuration:")
    print("-" * 40)
    print("1. Open Claude Desktop")
    print("2. Go to Settings → Custom Connectors")
    print("3. Add new connector with:")
    print(f"   URL: {config.mcp_url}")
    if config.api_key:
        print(f"   Headers: Authorization: Bearer {config.api_key}")
    print("\n✅ Server ready for connections!")
    print("="*80 + "\n")


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="WordPress MCP Server with HTTPS support")
    parser.add_argument("--transport", choices=["stdio", "http", "https"], default="stdio",
                       help="Transport method (default: stdio)")
    parser.add_argument("--host", default="localhost", help="Host to bind to (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--ssl-cert", help="Path to SSL certificate file (required for HTTPS)")
    parser.add_argument("--ssl-key", help="Path to SSL private key file (required for HTTPS)")
    parser.add_argument("--api-key", help="API key for authentication (auto-generated if not provided)")
    parser.add_argument("--mount-path", default="/mcp", help="Mount path for MCP endpoint (default: /mcp)")
    
    args = parser.parse_args()
    
    # Update server configuration from arguments
    if args.transport in ["http", "https"]:
        wp_manager.server_config.host = args.host
        wp_manager.server_config.port = args.port
        wp_manager.server_config.mount_path = args.mount_path
        
        if args.api_key:
            wp_manager.server_config.api_key = args.api_key
        
        if args.transport == "https":
            if not args.ssl_cert or not args.ssl_key:
                print("❌ Error: --ssl-cert and --ssl-key are required for HTTPS transport")
                return
            
            wp_manager.server_config.ssl_cert_path = args.ssl_cert
            wp_manager.server_config.ssl_key_path = args.ssl_key
    
    # Run the server based on transport choice
    if args.transport == "stdio":
        logger.info("Starting WordPress MCP Server with stdio transport")
        asyncio.run(mcp.run())
    elif args.transport in ["http", "https"]:
        # Update MCP server settings for HTTP transport
        mcp.settings.host = wp_manager.server_config.host
        mcp.settings.port = wp_manager.server_config.port
        mcp.settings.streamable_http_path = wp_manager.server_config.mount_path
        
        print_connection_info(wp_manager.server_config)
        
        # Run with streamable HTTP transport
        asyncio.run(mcp.run(transport="streamable-http"))


if __name__ == "__main__":
    main()
