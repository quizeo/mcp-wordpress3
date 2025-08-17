"""
Additional WordPress MCP Tools - Media, Taxonomy, Cache, and Performance
This module contains the remaining 25 tools to complete the 59-tool WordPress MCP implementation.
"""

from typing import Optional, List, Dict, Any
import json
from mcp.server.fastmcp import FastMCP

# This will be imported from the main module
wp_manager = None
mcp = None
validate_positive_int = None
format_response = None

def register_additional_tools(mcp_server, manager, validator, formatter):
    """Register additional tools with the MCP server"""
    global mcp, wp_manager, validate_positive_int, format_response
    mcp = mcp_server
    wp_manager = manager
    validate_positive_int = validator
    format_response = formatter
    
    # Register all additional tools
    register_media_tools()
    register_taxonomy_tools()
    register_cache_tools()
    register_performance_tools()


def register_media_tools():
    """Register media management tools"""
    
    @mcp.tool()
    async def wp_list_media(
        per_page: int = 10,
        page: int = 1,
        search: Optional[str] = None,
        media_type: Optional[str] = None,
        mime_type: Optional[str] = None,
        order: str = "desc",
        orderby: str = "date",
        site: Optional[str] = None
    ) -> str:
        """List media files from a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            params = {
                "per_page": min(per_page, 100),
                "page": page,
                "order": order,
                "orderby": orderby
            }
            if search: params["search"] = search
            if media_type: params["media_type"] = media_type
            if mime_type: params["mime_type"] = mime_type
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("GET", "/media", params=params)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_get_media(media_id: int, site: Optional[str] = None) -> str:
        """Retrieve detailed information about a single media file."""
        try:
            site_id = wp_manager.get_site_id(site)
            media_id = validate_positive_int(media_id, "media_id")
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("GET", f"/media/{media_id}")
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_upload_media(
        title: str,
        file_data: str,
        filename: str,
        alt_text: Optional[str] = None,
        caption: Optional[str] = None,
        description: Optional[str] = None,
        site: Optional[str] = None
    ) -> str:
        """Upload a new media file to WordPress."""
        try:
            site_id = wp_manager.get_site_id(site)
            
            # Note: This is a simplified implementation
            # In a real implementation, you'd handle actual file upload
            data = {
                "title": title,
                "alt_text": alt_text or "",
                "caption": caption or "",
                "description": description or ""
            }
            
            async with wp_manager.get_client(site_id) as client:
                # This would need proper file handling in a real implementation
                return format_response({
                    "status": "info",
                    "message": "Media upload requires binary file handling - not implemented in this demo"
                })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_update_media(
        media_id: int,
        title: Optional[str] = None,
        alt_text: Optional[str] = None,
        caption: Optional[str] = None,
        description: Optional[str] = None,
        site: Optional[str] = None
    ) -> str:
        """Update media file metadata."""
        try:
            site_id = wp_manager.get_site_id(site)
            media_id = validate_positive_int(media_id, "media_id")
            
            data = {}
            if title is not None: data["title"] = title
            if alt_text is not None: data["alt_text"] = alt_text
            if caption is not None: data["caption"] = caption
            if description is not None: data["description"] = description
            
            if not data:
                raise ValueError("At least one field must be provided to update")
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("POST", f"/media/{media_id}", json=data)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_delete_media(
        media_id: int,
        force: bool = False,
        site: Optional[str] = None
    ) -> str:
        """Delete a media file."""
        try:
            site_id = wp_manager.get_site_id(site)
            media_id = validate_positive_int(media_id, "media_id")
            
            params = {"force": force} if force else {}
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("DELETE", f"/media/{media_id}", params=params)
                action = "permanently deleted" if force else "moved to trash"
                return format_response({
                    "status": "success",
                    "message": f"Media {media_id} {action} successfully",
                    "media": response
                })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})


def register_taxonomy_tools():
    """Register taxonomy (categories and tags) tools"""
    
    @mcp.tool()
    async def wp_list_categories(
        per_page: int = 10,
        page: int = 1,
        search: Optional[str] = None,
        exclude: Optional[List[int]] = None,
        include: Optional[List[int]] = None,
        order: str = "asc",
        orderby: str = "name",
        hide_empty: bool = False,
        parent: Optional[int] = None,
        site: Optional[str] = None
    ) -> str:
        """List categories from a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            params = {
                "per_page": min(per_page, 100),
                "page": page,
                "order": order,
                "orderby": orderby,
                "hide_empty": hide_empty
            }
            if search: params["search"] = search
            if exclude: params["exclude"] = ",".join(str(e) for e in exclude)
            if include: params["include"] = ",".join(str(i) for i in include)
            if parent: params["parent"] = parent
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("GET", "/categories", params=params)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_get_category(category_id: int, site: Optional[str] = None) -> str:
        """Retrieve detailed information about a single category."""
        try:
            site_id = wp_manager.get_site_id(site)
            category_id = validate_positive_int(category_id, "category_id")
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("GET", f"/categories/{category_id}")
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_create_category(
        name: str,
        description: Optional[str] = None,
        slug: Optional[str] = None,
        parent: Optional[int] = None,
        site: Optional[str] = None
    ) -> str:
        """Create a new category."""
        try:
            site_id = wp_manager.get_site_id(site)
            data = {"name": name}
            if description: data["description"] = description
            if slug: data["slug"] = slug
            if parent: data["parent"] = parent
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("POST", "/categories", json=data)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_update_category(
        category_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        slug: Optional[str] = None,
        parent: Optional[int] = None,
        site: Optional[str] = None
    ) -> str:
        """Update an existing category."""
        try:
            site_id = wp_manager.get_site_id(site)
            category_id = validate_positive_int(category_id, "category_id")
            
            data = {}
            if name is not None: data["name"] = name
            if description is not None: data["description"] = description
            if slug is not None: data["slug"] = slug
            if parent is not None: data["parent"] = parent
            
            if not data:
                raise ValueError("At least one field must be provided to update")
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("POST", f"/categories/{category_id}", json=data)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_delete_category(
        category_id: int,
        force: bool = False,
        site: Optional[str] = None
    ) -> str:
        """Delete a category."""
        try:
            site_id = wp_manager.get_site_id(site)
            category_id = validate_positive_int(category_id, "category_id")
            
            params = {"force": force} if force else {}
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("DELETE", f"/categories/{category_id}", params=params)
                return format_response({
                    "status": "success",
                    "message": f"Category {category_id} deleted successfully",
                    "category": response
                })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    # Tag tools
    @mcp.tool()
    async def wp_list_tags(
        per_page: int = 10,
        page: int = 1,
        search: Optional[str] = None,
        exclude: Optional[List[int]] = None,
        include: Optional[List[int]] = None,
        order: str = "asc",
        orderby: str = "name",
        hide_empty: bool = False,
        site: Optional[str] = None
    ) -> str:
        """List tags from a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            params = {
                "per_page": min(per_page, 100),
                "page": page,
                "order": order,
                "orderby": orderby,
                "hide_empty": hide_empty
            }
            if search: params["search"] = search
            if exclude: params["exclude"] = ",".join(str(e) for e in exclude)
            if include: params["include"] = ",".join(str(i) for i in include)
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("GET", "/tags", params=params)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_get_tag(tag_id: int, site: Optional[str] = None) -> str:
        """Retrieve detailed information about a single tag."""
        try:
            site_id = wp_manager.get_site_id(site)
            tag_id = validate_positive_int(tag_id, "tag_id")
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("GET", f"/tags/{tag_id}")
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_create_tag(
        name: str,
        description: Optional[str] = None,
        slug: Optional[str] = None,
        site: Optional[str] = None
    ) -> str:
        """Create a new tag."""
        try:
            site_id = wp_manager.get_site_id(site)
            data = {"name": name}
            if description: data["description"] = description
            if slug: data["slug"] = slug
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("POST", "/tags", json=data)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_update_tag(
        tag_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        slug: Optional[str] = None,
        site: Optional[str] = None
    ) -> str:
        """Update an existing tag."""
        try:
            site_id = wp_manager.get_site_id(site)
            tag_id = validate_positive_int(tag_id, "tag_id")
            
            data = {}
            if name is not None: data["name"] = name
            if description is not None: data["description"] = description
            if slug is not None: data["slug"] = slug
            
            if not data:
                raise ValueError("At least one field must be provided to update")
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("POST", f"/tags/{tag_id}", json=data)
                return format_response(response)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_delete_tag(
        tag_id: int,
        force: bool = False,
        site: Optional[str] = None
    ) -> str:
        """Delete a tag."""
        try:
            site_id = wp_manager.get_site_id(site)
            tag_id = validate_positive_int(tag_id, "tag_id")
            
            params = {"force": force} if force else {}
            
            async with wp_manager.get_client(site_id) as client:
                response = await client.request("DELETE", f"/tags/{tag_id}", params=params)
                return format_response({
                    "status": "success",
                    "message": f"Tag {tag_id} deleted successfully",
                    "tag": response
                })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})


def register_cache_tools():
    """Register cache management tools"""
    
    @mcp.tool()
    async def wp_cache_stats(site: Optional[str] = None) -> str:
        """Get cache statistics for a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            # Note: This would require a caching plugin with REST API support
            cache_stats = {
                "status": "simulated",
                "hit_ratio": 85.2,
                "total_requests": 12450,
                "cache_hits": 10607,
                "cache_misses": 1843,
                "cache_size": "245 MB",
                "objects_cached": 3250,
                "note": "This is simulated data - requires caching plugin integration"
            }
            return format_response(cache_stats)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_cache_clear(
        cache_type: str = "all",
        site: Optional[str] = None
    ) -> str:
        """Clear WordPress cache."""
        try:
            site_id = wp_manager.get_site_id(site)
            return format_response({
                "status": "simulated",
                "message": f"Cache clear ({cache_type}) simulated for site {site_id}",
                "note": "This requires caching plugin integration"
            })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_cache_warm(
        urls: Optional[List[str]] = None,
        site: Optional[str] = None
    ) -> str:
        """Warm up WordPress cache."""
        try:
            site_id = wp_manager.get_site_id(site)
            url_count = len(urls) if urls else 0
            return format_response({
                "status": "simulated",
                "message": f"Cache warming simulated for {url_count or 'all'} URLs",
                "note": "This requires caching plugin integration"
            })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_cache_info(site: Optional[str] = None) -> str:
        """Get cache configuration information."""
        try:
            site_id = wp_manager.get_site_id(site)
            cache_info = {
                "status": "simulated",
                "cache_enabled": True,
                "cache_type": "file",
                "cache_location": "/wp-content/cache/",
                "expiration": 3600,
                "note": "This is simulated data - requires caching plugin integration"
            }
            return format_response(cache_info)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})


def register_performance_tools():
    """Register performance monitoring tools"""
    
    @mcp.tool()
    async def wp_performance_stats(site: Optional[str] = None) -> str:
        """Get performance statistics for a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            perf_stats = {
                "status": "simulated",
                "page_load_time": 2.3,
                "time_to_first_byte": 0.8,
                "database_queries": 25,
                "memory_usage": "32 MB",
                "php_execution_time": 1.2,
                "plugin_load_time": 0.5,
                "theme_load_time": 0.3,
                "note": "This is simulated data - requires performance monitoring integration"
            }
            return format_response(perf_stats)
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_performance_history(
        days: int = 7,
        site: Optional[str] = None
    ) -> str:
        """Get performance history for a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            return format_response({
                "status": "simulated",
                "message": f"Performance history for last {days} days simulated",
                "note": "This requires performance monitoring integration"
            })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_performance_benchmark(site: Optional[str] = None) -> str:
        """Run performance benchmark for a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            return format_response({
                "status": "simulated",
                "message": "Performance benchmark simulated",
                "note": "This requires performance monitoring integration"
            })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_performance_alerts(site: Optional[str] = None) -> str:
        """Get performance alerts for a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            return format_response({
                "status": "simulated",
                "alerts": [],
                "message": "No performance alerts (simulated)",
                "note": "This requires performance monitoring integration"
            })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_performance_optimize(site: Optional[str] = None) -> str:
        """Run performance optimization for a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            return format_response({
                "status": "simulated",
                "message": "Performance optimization simulated",
                "note": "This requires performance monitoring integration"
            })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})

    @mcp.tool()
    async def wp_performance_export(
        format: str = "json",
        site: Optional[str] = None
    ) -> str:
        """Export performance data for a WordPress site."""
        try:
            site_id = wp_manager.get_site_id(site)
            return format_response({
                "status": "simulated",
                "message": f"Performance data export ({format}) simulated",
                "note": "This requires performance monitoring integration"
            })
        except Exception as e:
            return format_response({"status": "error", "message": str(e)})
