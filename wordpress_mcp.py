"""
WordPress MCP Server

A comprehensive Model Context Protocol server for WordPress management.
Provides 59 tools for managing WordPress sites including posts, pages, users, 
comments, media, taxonomies, cache, performance monitoring, and more.

Usage:
    uv run wordpress_mcp.py
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create an MCP server
mcp = FastMCP("WordPress MCP Server")


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


class WordPressClient:
    """WordPress REST API client"""
    
    def __init__(self, config: WordPressConfig):
        self.config = config
        self.base_url = f"{config.site_url.rstrip('/')}/wp-json/wp/v2"
        self.session = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    def _get_auth(self) -> tuple[str, str]:
        """Get authentication credentials"""
        return (self.config.username, self.config.app_password)
    
    async def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to WordPress API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add authentication
        kwargs.setdefault('auth', self._get_auth())
        
        try:
            response = await self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {"content": response.text}
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise Exception(f"Authentication failed for site '{self.config.id}'. Please check your credentials.")
            elif e.response.status_code == 403:
                raise Exception(f"Permission denied for site '{self.config.id}'. Check user permissions.")
            elif e.response.status_code == 404:
                raise Exception(f"Endpoint not found: {endpoint}")
            else:
                error_detail = ""
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message', str(e))
                except:
                    error_detail = str(e)
                raise Exception(f"WordPress API error ({e.response.status_code}): {error_detail}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")


class WordPressManager:
    """Manages WordPress clients and site selection"""
    
    def __init__(self):
        self.clients: Dict[str, WordPressConfig] = {}
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
                
            logger.info(f"Successfully loaded {sites_loaded} WordPress sites")
                
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
        """Get WordPress client for site"""
        if site_id not in self.clients:
            available = list(self.clients.keys())
            raise Exception(f"Site '{site_id}' not found. Available sites: {available}")
        return WordPressClient(self.clients[site_id])


# Global WordPress manager
wp_manager = WordPressManager()


def validate_positive_int(value: Any, name: str = "id") -> int:
    """Validate that a value is a positive integer"""
    try:
        int_val = int(value)
        if int_val <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return int_val
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {name}: must be a positive integer")


def format_response(data: Any) -> str:
    """Format response data for display"""
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2, default=str)


# ============================================================================
# AUTHENTICATION TOOLS
# ============================================================================

@mcp.tool()
async def wp_test_auth(site: Optional[str] = None) -> str:
    """
    Test WordPress authentication by attempting to access the WordPress API.
    
    Args:
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Authentication test results
    """
    try:
        site_id = wp_manager.get_site_id(site)
        async with wp_manager.get_client(site_id) as client:
            # Test authentication by getting site info
            response = await client.request("GET", "/")
            
            result = {
                "status": "success",
                "message": "Authentication successful",
                "site_id": site_id,
                "site_name": wp_manager.clients[site_id].name,
                "site_url": wp_manager.clients[site_id].site_url,
                "api_namespace": response.get("namespaces", [])
            }
            return format_response(result)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_auth_status(site: Optional[str] = None) -> str:
    """
    Get the current authentication status and method for a WordPress site.
    
    Args:
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Current authentication status and configuration
    """
    try:
        site_id = wp_manager.get_site_id(site)
        config = wp_manager.clients[site_id]
        
        # Test current authentication
        async with wp_manager.get_client(site_id) as client:
            try:
                await client.request("GET", "/")
                auth_status = "active"
                auth_message = "Authentication is working"
            except Exception as e:
                auth_status = "failed"
                auth_message = str(e)
        
        result = {
            "site_id": site_id,
            "site_name": config.name,
            "site_url": config.site_url,
            "username": config.username,
            "auth_method": config.auth_method.value,
            "auth_status": auth_status,
            "auth_message": auth_message
        }
        return format_response(result)
        
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_switch_auth_method(
    auth_method: str,
    username: str,
    password: str,
    site: Optional[str] = None
) -> str:
    """
    Switch authentication method for a WordPress site.
    
    Args:
        auth_method: Authentication method ('app-password' or 'basic-auth')
        username: WordPress username
        password: Application password or user password
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Results of authentication method switch
    """
    try:
        if auth_method not in ["app-password", "basic-auth"]:
            raise ValueError("auth_method must be 'app-password' or 'basic-auth'")
            
        site_id = wp_manager.get_site_id(site)
        
        # Update the configuration
        config = wp_manager.clients[site_id]
        config.username = username
        config.app_password = password
        config.auth_method = AuthMethod(auth_method)
        
        # Test new authentication
        async with wp_manager.get_client(site_id) as client:
            await client.request("GET", "/")
        
        result = {
            "status": "success",
            "message": f"Authentication method switched to {auth_method}",
            "site_id": site_id,
            "username": username,
            "auth_method": auth_method
        }
        return format_response(result)
        
    except Exception as e:
        return format_response({
            "status": "error", 
            "message": str(e)
        })


# ============================================================================
# SITE TOOLS
# ============================================================================

@mcp.tool()
async def wp_get_site_settings(site: Optional[str] = None) -> str:
    """
    Get WordPress site settings and configuration information.
    
    Args:
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Site settings and information
    """
    try:
        site_id = wp_manager.get_site_id(site)
        async with wp_manager.get_client(site_id) as client:
            settings = await client.request("GET", "/settings")
            return format_response(settings)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_update_site_settings(
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    email: Optional[str] = None,
    timezone: Optional[str] = None,
    date_format: Optional[str] = None,
    time_format: Optional[str] = None,
    start_of_week: Optional[int] = None,
    language: Optional[str] = None,
    site: Optional[str] = None
) -> str:
    """
    Update WordPress site settings.
    
    Args:
        title: Site title
        description: Site tagline/description
        url: Site URL
        email: Admin email address
        timezone: Site timezone
        date_format: Date format
        time_format: Time format  
        start_of_week: Start of week (0=Sunday, 1=Monday, etc.)
        language: Site language
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Updated site settings
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        # Build update data from provided parameters
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if url is not None:
            update_data["url"] = url
        if email is not None:
            update_data["email"] = email
        if timezone is not None:
            update_data["timezone"] = timezone
        if date_format is not None:
            update_data["date_format"] = date_format
        if time_format is not None:
            update_data["time_format"] = time_format
        if start_of_week is not None:
            update_data["start_of_week"] = start_of_week
        if language is not None:
            update_data["language"] = language
            
        if not update_data:
            raise ValueError("At least one setting must be provided to update")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", "/settings", json=update_data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_search_site(
    search: str,
    type: Optional[str] = None,
    subtype: Optional[str] = None,
    per_page: int = 10,
    page: int = 1,
    site: Optional[str] = None
) -> str:
    """
    Search content across the WordPress site.
    
    Args:
        search: Search term
        type: Content type to search ('post' or 'page', optional)
        subtype: Content subtype (optional)
        per_page: Number of results per page (max 100)
        page: Page number for pagination
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Search results
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        params = {
            "search": search,
            "per_page": min(per_page, 100),
            "page": page
        }
        
        if type:
            params["type"] = type
        if subtype:
            params["subtype"] = subtype
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", "/search", params=params)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_application_passwords(
    user_id: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Get application passwords for a user.
    
    Args:
        user_id: User ID (optional, defaults to current user)
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        List of application passwords
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        # If no user_id provided, get current user
        endpoint = "/users/me/application-passwords"
        if user_id:
            validate_positive_int(user_id, "user_id")
            endpoint = f"/users/{user_id}/application-passwords"
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", endpoint)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_create_application_password(
    name: str,
    user_id: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Create a new application password for a user.
    
    Args:
        name: Name/description for the application password
        user_id: User ID (optional, defaults to current user)
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Created application password details
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        # If no user_id provided, use current user
        endpoint = "/users/me/application-passwords"
        if user_id:
            validate_positive_int(user_id, "user_id")
            endpoint = f"/users/{user_id}/application-passwords"
        
        data = {"name": name}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", endpoint, json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_delete_application_password(
    uuid: str,
    user_id: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Delete an application password.
    
    Args:
        uuid: UUID of the application password to delete
        user_id: User ID (optional, defaults to current user)
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Deletion confirmation
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        # If no user_id provided, use current user
        endpoint = f"/users/me/application-passwords/{uuid}"
        if user_id:
            validate_positive_int(user_id, "user_id")
            endpoint = f"/users/{user_id}/application-passwords/{uuid}"
        
        async with wp_manager.get_client(site_id) as client:
            await client.request("DELETE", endpoint)
            return format_response({
                "status": "success",
                "message": f"Application password {uuid} deleted successfully"
            })
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


# ============================================================================
# POST TOOLS
# ============================================================================

@mcp.tool()
async def wp_list_posts(
    per_page: int = 10,
    page: int = 1,
    search: Optional[str] = None,
    status: Optional[str] = None,
    categories: Optional[List[int]] = None,
    tags: Optional[List[int]] = None,
    author: Optional[int] = None,
    order: str = "desc",
    orderby: str = "date",
    site: Optional[str] = None
) -> str:
    """
    List posts from a WordPress site with comprehensive filtering options.
    
    Args:
        per_page: Number of items to return per page (max 100)
        page: Page number for pagination
        search: Limit results to those matching a search term
        status: Filter by post status ('publish', 'draft', 'pending', 'private')
        categories: List of category IDs to filter by
        tags: List of tag IDs to filter by
        author: Author ID to filter by
        order: Sort order ('asc' or 'desc')
        orderby: Sort field ('date', 'title', 'slug', 'author', 'modified')
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        List of posts with metadata
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        params = {
            "per_page": min(per_page, 100),
            "page": page,
            "order": order,
            "orderby": orderby
        }
        
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if categories:
            params["categories"] = ",".join(str(c) for c in categories)
        if tags:
            params["tags"] = ",".join(str(t) for t in tags)
        if author:
            params["author"] = author
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", "/posts", params=params)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_post(post_id: int, site: Optional[str] = None) -> str:
    """
    Retrieve detailed information about a single post.
    
    Args:
        post_id: The unique identifier for the post
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Detailed post information
    """
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", f"/posts/{post_id}")
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_create_post(
    title: str,
    content: Optional[str] = None,
    status: str = "draft",
    excerpt: Optional[str] = None,
    categories: Optional[List[int]] = None,
    tags: Optional[List[int]] = None,
    meta: Optional[Dict[str, Any]] = None,
    featured_media: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Create a new WordPress post.
    
    Args:
        title: The title for the post
        content: The content for the post, in HTML format
        status: The publishing status ('draft', 'publish', 'pending', 'private')
        excerpt: The excerpt for the post
        categories: List of category IDs to assign to the post
        tags: List of tag IDs to assign to the post
        meta: Custom meta fields for the post
        featured_media: Featured image media ID
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Created post details
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        data = {
            "title": title,
            "status": status
        }
        
        if content:
            data["content"] = content
        if excerpt:
            data["excerpt"] = excerpt
        if categories:
            data["categories"] = categories
        if tags:
            data["tags"] = tags
        if meta:
            data["meta"] = meta
        if featured_media:
            data["featured_media"] = featured_media
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", "/posts", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_update_post(
    post_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
    excerpt: Optional[str] = None,
    categories: Optional[List[int]] = None,
    tags: Optional[List[int]] = None,
    meta: Optional[Dict[str, Any]] = None,
    featured_media: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Update an existing WordPress post.
    
    Args:
        post_id: The ID of the post to update
        title: The new title for the post
        content: The new content for the post, in HTML format
        status: The new status for the post
        excerpt: The new excerpt for the post
        categories: New category IDs to assign to the post
        tags: New tag IDs to assign to the post
        meta: Custom meta fields to update
        featured_media: Featured image media ID
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Updated post details
    """
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        data = {}
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if status is not None:
            data["status"] = status
        if excerpt is not None:
            data["excerpt"] = excerpt
        if categories is not None:
            data["categories"] = categories
        if tags is not None:
            data["tags"] = tags
        if meta is not None:
            data["meta"] = meta
        if featured_media is not None:
            data["featured_media"] = featured_media
            
        if not data:
            raise ValueError("At least one field must be provided to update")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", f"/posts/{post_id}", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_delete_post(
    post_id: int,
    force: bool = False,
    site: Optional[str] = None
) -> str:
    """
    Delete a WordPress post.
    
    Args:
        post_id: The ID of the post to delete
        force: If true, permanently delete. If false, move to trash
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Deletion confirmation
    """
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        params = {"force": force} if force else {}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("DELETE", f"/posts/{post_id}", params=params)
            
            action = "permanently deleted" if force else "moved to trash"
            return format_response({
                "status": "success",
                "message": f"Post {post_id} {action} successfully",
                "post": response
            })
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_post_revisions(
    post_id: int,
    context: str = "view",
    site: Optional[str] = None
) -> str:
    """
    Get revision history for a post.
    
    Args:
        post_id: The ID of the post
        context: Request context ('view', 'embed', 'edit')
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Post revision history
    """
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post_id, "post_id")
        
        params = {"context": context}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", f"/posts/{post_id}/revisions", params=params)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


# ============================================================================
# PAGE TOOLS
# ============================================================================

@mcp.tool()
async def wp_list_pages(
    per_page: int = 10,
    page: int = 1,
    search: Optional[str] = None,
    status: Optional[str] = None,
    author: Optional[int] = None,
    parent: Optional[int] = None,
    order: str = "desc",
    orderby: str = "date",
    site: Optional[str] = None
) -> str:
    """
    List pages from a WordPress site with filtering options.
    
    Args:
        per_page: Number of items to return per page (max 100)
        page: Page number for pagination
        search: Limit results to those matching a search term
        status: Filter by page status ('publish', 'draft', 'pending', 'private')
        author: Author ID to filter by
        parent: Parent page ID to filter by
        order: Sort order ('asc' or 'desc')
        orderby: Sort field ('date', 'title', 'slug', 'author', 'modified')
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        List of pages with metadata
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        params = {
            "per_page": min(per_page, 100),
            "page": page,
            "order": order,
            "orderby": orderby
        }
        
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if author:
            params["author"] = author
        if parent:
            params["parent"] = parent
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", "/pages", params=params)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_page(page_id: int, site: Optional[str] = None) -> str:
    """
    Retrieve detailed information about a single page.
    
    Args:
        page_id: The unique identifier for the page
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Detailed page information
    """
    try:
        site_id = wp_manager.get_site_id(site)
        page_id = validate_positive_int(page_id, "page_id")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", f"/pages/{page_id}")
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_create_page(
    title: str,
    content: Optional[str] = None,
    status: str = "draft",
    parent: Optional[int] = None,
    template: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    featured_media: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Create a new WordPress page.
    
    Args:
        title: The title for the page
        content: The content for the page, in HTML format
        status: The publishing status ('draft', 'publish', 'pending', 'private')
        parent: Parent page ID
        template: Page template to use
        meta: Custom meta fields for the page
        featured_media: Featured image media ID
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Created page details
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        data = {
            "title": title,
            "status": status
        }
        
        if content:
            data["content"] = content
        if parent:
            data["parent"] = parent
        if template:
            data["template"] = template
        if meta:
            data["meta"] = meta
        if featured_media:
            data["featured_media"] = featured_media
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", "/pages", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_update_page(
    page_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
    parent: Optional[int] = None,
    template: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    featured_media: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Update an existing WordPress page.
    
    Args:
        page_id: The ID of the page to update
        title: The new title for the page
        content: The new content for the page, in HTML format
        status: The new status for the page
        parent: New parent page ID
        template: New page template
        meta: Custom meta fields to update
        featured_media: Featured image media ID
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Updated page details
    """
    try:
        site_id = wp_manager.get_site_id(site)
        page_id = validate_positive_int(page_id, "page_id")
        
        data = {}
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if status is not None:
            data["status"] = status
        if parent is not None:
            data["parent"] = parent
        if template is not None:
            data["template"] = template
        if meta is not None:
            data["meta"] = meta
        if featured_media is not None:
            data["featured_media"] = featured_media
            
        if not data:
            raise ValueError("At least one field must be provided to update")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", f"/pages/{page_id}", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_delete_page(
    page_id: int,
    force: bool = False,
    site: Optional[str] = None
) -> str:
    """
    Delete a WordPress page.
    
    Args:
        page_id: The ID of the page to delete
        force: If true, permanently delete. If false, move to trash
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Deletion confirmation
    """
    try:
        site_id = wp_manager.get_site_id(site)
        page_id = validate_positive_int(page_id, "page_id")
        
        params = {"force": force} if force else {}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("DELETE", f"/pages/{page_id}", params=params)
            
            action = "permanently deleted" if force else "moved to trash"
            return format_response({
                "status": "success",
                "message": f"Page {page_id} {action} successfully",
                "page": response
            })
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_page_revisions(
    page_id: int,
    context: str = "view",
    site: Optional[str] = None
) -> str:
    """
    Get revision history for a page.
    
    Args:
        page_id: The ID of the page
        context: Request context ('view', 'embed', 'edit')
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Page revision history
    """
    try:
        site_id = wp_manager.get_site_id(site)
        page_id = validate_positive_int(page_id, "page_id")
        
        params = {"context": context}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", f"/pages/{page_id}/revisions", params=params)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


# ============================================================================
# USER TOOLS
# ============================================================================

@mcp.tool()
async def wp_list_users(
    per_page: int = 10,
    page: int = 1,
    search: Optional[str] = None,
    roles: Optional[List[str]] = None,
    capabilities: Optional[List[str]] = None,
    order: str = "asc",
    orderby: str = "name",
    site: Optional[str] = None
) -> str:
    """
    List users from a WordPress site with filtering options.
    
    Args:
        per_page: Number of items to return per page (max 100)
        page: Page number for pagination
        search: Limit results to those matching a search term
        roles: List of roles to filter by
        capabilities: List of capabilities to filter by
        order: Sort order ('asc' or 'desc')
        orderby: Sort field ('id', 'name', 'registered_date', 'email', 'url')
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        List of users with metadata
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        params = {
            "per_page": min(per_page, 100),
            "page": page,
            "order": order,
            "orderby": orderby
        }
        
        if search:
            params["search"] = search
        if roles:
            params["roles"] = ",".join(roles)
        if capabilities:
            params["capabilities"] = ",".join(capabilities)
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", "/users", params=params)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_user(user_id: int, site: Optional[str] = None) -> str:
    """
    Retrieve detailed information about a single user.
    
    Args:
        user_id: The unique identifier for the user
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Detailed user information
    """
    try:
        site_id = wp_manager.get_site_id(site)
        user_id = validate_positive_int(user_id, "user_id")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", f"/users/{user_id}")
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_current_user(site: Optional[str] = None) -> str:
    """
    Get information about the currently authenticated user.
    
    Args:
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Current user information
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", "/users/me")
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_create_user(
    username: str,
    email: str,
    password: str,
    name: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    nickname: Optional[str] = None,
    description: Optional[str] = None,
    roles: Optional[List[str]] = None,
    site: Optional[str] = None
) -> str:
    """
    Create a new WordPress user.
    
    Args:
        username: Username for the new user
        email: Email address for the new user
        password: Password for the new user
        name: Display name for the user
        first_name: First name
        last_name: Last name
        nickname: Nickname
        description: User description/bio
        roles: List of roles to assign to the user
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Created user details
    """
    try:
        site_id = wp_manager.get_site_id(site)
        
        data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        if name:
            data["name"] = name
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if nickname:
            data["nickname"] = nickname
        if description:
            data["description"] = description
        if roles:
            data["roles"] = roles
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", "/users", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_update_user(
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    name: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    nickname: Optional[str] = None,
    description: Optional[str] = None,
    roles: Optional[List[str]] = None,
    site: Optional[str] = None
) -> str:
    """
    Update an existing WordPress user.
    
    Args:
        user_id: The ID of the user to update
        username: New username
        email: New email address
        password: New password
        name: New display name
        first_name: New first name
        last_name: New last name
        nickname: New nickname
        description: New description/bio
        roles: New roles to assign
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Updated user details
    """
    try:
        site_id = wp_manager.get_site_id(site)
        user_id = validate_positive_int(user_id, "user_id")
        
        data = {}
        if username is not None:
            data["username"] = username
        if email is not None:
            data["email"] = email
        if password is not None:
            data["password"] = password
        if name is not None:
            data["name"] = name
        if first_name is not None:
            data["first_name"] = first_name
        if last_name is not None:
            data["last_name"] = last_name
        if nickname is not None:
            data["nickname"] = nickname
        if description is not None:
            data["description"] = description
        if roles is not None:
            data["roles"] = roles
            
        if not data:
            raise ValueError("At least one field must be provided to update")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", f"/users/{user_id}", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_delete_user(
    user_id: int,
    force: bool = False,
    reassign: Optional[int] = None,
    site: Optional[str] = None
) -> str:
    """
    Delete a WordPress user.
    
    Args:
        user_id: The ID of the user to delete
        force: If true, permanently delete user
        reassign: User ID to reassign posts to
        site: The ID of the WordPress site to target (optional if only one site configured)
    
    Returns:
        Deletion confirmation
    """
    try:
        site_id = wp_manager.get_site_id(site)
        user_id = validate_positive_int(user_id, "user_id")
        
        params = {}
        if force:
            params["force"] = force
        if reassign:
            params["reassign"] = reassign
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("DELETE", f"/users/{user_id}", params=params)
            
            return format_response({
                "status": "success",
                "message": f"User {user_id} deleted successfully",
                "user": response
            })
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


# ============================================================================
# COMMENT TOOLS
# ============================================================================

@mcp.tool()
async def wp_list_comments(
    per_page: int = 10,
    page: int = 1,
    search: Optional[str] = None,
    status: Optional[str] = None,
    post: Optional[int] = None,
    author: Optional[int] = None,
    author_email: Optional[str] = None,
    parent: Optional[int] = None,
    order: str = "desc",
    orderby: str = "date_gmt",
    site: Optional[str] = None
) -> str:
    """List comments from a WordPress site with filtering options."""
    try:
        site_id = wp_manager.get_site_id(site)
        
        params = {
            "per_page": min(per_page, 100),
            "page": page,
            "order": order,
            "orderby": orderby
        }
        
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if post:
            params["post"] = post
        if author:
            params["author"] = author
        if author_email:
            params["author_email"] = author_email
        if parent:
            params["parent"] = parent
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", "/comments", params=params)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_get_comment(comment_id: int, site: Optional[str] = None) -> str:
    """Retrieve detailed information about a single comment."""
    try:
        site_id = wp_manager.get_site_id(site)
        comment_id = validate_positive_int(comment_id, "comment_id")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("GET", f"/comments/{comment_id}")
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_create_comment(
    post: int,
    content: str,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None,
    author_url: Optional[str] = None,
    parent: Optional[int] = None,
    status: str = "approved",
    site: Optional[str] = None
) -> str:
    """Create a new comment on a WordPress post."""
    try:
        site_id = wp_manager.get_site_id(site)
        post_id = validate_positive_int(post, "post")
        
        data = {
            "post": post_id,
            "content": content,
            "status": status
        }
        
        if author_name:
            data["author_name"] = author_name
        if author_email:
            data["author_email"] = author_email
        if author_url:
            data["author_url"] = author_url
        if parent:
            data["parent"] = parent
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", "/comments", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_update_comment(
    comment_id: int,
    content: Optional[str] = None,
    status: Optional[str] = None,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None,
    author_url: Optional[str] = None,
    site: Optional[str] = None
) -> str:
    """Update an existing comment."""
    try:
        site_id = wp_manager.get_site_id(site)
        comment_id = validate_positive_int(comment_id, "comment_id")
        
        data = {}
        if content is not None:
            data["content"] = content
        if status is not None:
            data["status"] = status
        if author_name is not None:
            data["author_name"] = author_name
        if author_email is not None:
            data["author_email"] = author_email
        if author_url is not None:
            data["author_url"] = author_url
            
        if not data:
            raise ValueError("At least one field must be provided to update")
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", f"/comments/{comment_id}", json=data)
            return format_response(response)
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_delete_comment(
    comment_id: int,
    force: bool = False,
    site: Optional[str] = None
) -> str:
    """Delete a WordPress comment."""
    try:
        site_id = wp_manager.get_site_id(site)
        comment_id = validate_positive_int(comment_id, "comment_id")
        
        params = {"force": force} if force else {}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("DELETE", f"/comments/{comment_id}", params=params)
            
            action = "permanently deleted" if force else "moved to trash"
            return format_response({
                "status": "success",
                "message": f"Comment {comment_id} {action} successfully",
                "comment": response
            })
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_approve_comment(comment_id: int, site: Optional[str] = None) -> str:
    """Approve a WordPress comment."""
    try:
        site_id = wp_manager.get_site_id(site)
        comment_id = validate_positive_int(comment_id, "comment_id")
        
        data = {"status": "approved"}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", f"/comments/{comment_id}", json=data)
            return format_response({
                "status": "success",
                "message": f"Comment {comment_id} approved successfully",
                "comment": response
            })
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


@mcp.tool()
async def wp_spam_comment(comment_id: int, site: Optional[str] = None) -> str:
    """Mark a WordPress comment as spam."""
    try:
        site_id = wp_manager.get_site_id(site)
        comment_id = validate_positive_int(comment_id, "comment_id")
        
        data = {"status": "spam"}
        
        async with wp_manager.get_client(site_id) as client:
            response = await client.request("POST", f"/comments/{comment_id}", json=data)
            return format_response({
                "status": "success",
                "message": f"Comment {comment_id} marked as spam successfully",
                "comment": response
            })
            
    except Exception as e:
        return format_response({
            "status": "error",
            "message": str(e)
        })


# ============================================================================
# REGISTER ADDITIONAL TOOLS
# ============================================================================

# Import and register the remaining 25 tools
try:
    from additional_wordpress_tools import register_additional_tools
    register_additional_tools(mcp, wp_manager, validate_positive_int, format_response)
    logger.info("Successfully registered additional WordPress tools")
except Exception as e:
    logger.error(f"Error registering additional tools: {e}")


# Continue with more tools...
if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run())