"""
Test script for WordPress MCP HTTPS Server

This script validates that the HTTPS WordPress MCP server is working correctly
and can be connected to by Claude Desktop.
"""

import asyncio
import json
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test_http_endpoint(url: str, api_key: str = None):
    """Test the basic HTTP endpoint"""
    print(f"🔍 Testing HTTP endpoint: {url}")
    
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            print(f"✅ HTTP Response: {response.status_code}")
            if response.status_code != 406:  # 406 is expected for non-MCP requests
                print(f"❌ Unexpected status code: {response.status_code}")
                return False
            return True
    except Exception as e:
        print(f"❌ HTTP endpoint test failed: {e}")
        return False


async def test_mcp_connection(url: str):
    """Test MCP protocol connection"""
    print(f"🔍 Testing MCP connection: {url}")
    
    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                print("✅ MCP connection established")
                
                # List tools
                tools = await session.list_tools()
                print(f"✅ Found {len(tools.tools)} tools")
                
                # List first few tools
                for tool in tools.tools[:5]:
                    print(f"   📧 {tool.name}: {tool.description[:60]}...")
                
                return True
                
    except Exception as e:
        print(f"❌ MCP connection test failed: {e}")
        return False


async def test_wordpress_tools(url: str):
    """Test specific WordPress tools"""
    print(f"🔍 Testing WordPress tools: {url}")
    
    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test authentication status
                print("🔍 Testing wp_get_auth_status...")
                result = await session.call_tool("wp_get_auth_status", {})
                auth_response = json.loads(result.content[0].text)
                
                if auth_response.get("status") == "error":
                    print(f"⚠️  Authentication test (expected): {auth_response.get('message')}")
                else:
                    print("✅ WordPress authentication working")
                
                # Test a simple tool
                print("🔍 Testing wp_cache_stats...")
                result = await session.call_tool("wp_cache_stats", {})
                cache_response = json.loads(result.content[0].text)
                
                if cache_response.get("status") == "success":
                    print("✅ WordPress cache tools working")
                elif "simulated" in str(cache_response):
                    print("✅ WordPress cache tools working (simulated)")
                else:
                    print(f"⚠️  Cache test: {cache_response}")
                
                return True
                
    except Exception as e:
        print(f"❌ WordPress tools test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting WordPress MCP HTTPS Server Tests")
    print("=" * 60)
    
    # Test configuration
    base_url = "http://localhost:8002"
    mcp_endpoint = f"{base_url}/mcp"
    
    print(f"🎯 Target Server: {base_url}")
    print(f"🎯 MCP Endpoint: {mcp_endpoint}")
    print()
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Basic HTTP endpoint
    if await test_http_endpoint(mcp_endpoint):
        tests_passed += 1
    print()
    
    # Test 2: MCP connection
    if await test_mcp_connection(mcp_endpoint):
        tests_passed += 1
    print()
    
    # Test 3: WordPress tools
    if await test_wordpress_tools(mcp_endpoint):
        tests_passed += 1
    print()
    
    # Results
    print("=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Server is ready for Claude Desktop integration.")
        print()
        print("📋 Claude Desktop Setup:")
        print("1. Open Claude Desktop")
        print("2. Go to Settings → Custom Connectors")
        print("3. Add new connector:")
        print(f"   URL: {mcp_endpoint}")
        print("   (API key optional - check server output for key)")
    else:
        print("❌ Some tests failed. Check server status and configuration.")
        print()
        print("🔧 Troubleshooting:")
        print("1. Ensure the server is running:")
        print("   uv run python wordpress_mcp_https.py --transport http")
        print("2. Check the server is accessible on the expected port")
        print("3. Verify WordPress configuration in mcp-wordpress.config.json")


def main():
    """Main entry point"""
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")


if __name__ == "__main__":
    main()
