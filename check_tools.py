import httpx
import json
import asyncio

async def check_server_status():
    """Check server status and connection"""
    base_url = "https://mcp-wordpress3.onrender.com"
    
    try:
        print("🔍 Checking deployed Render server status...")
        print(f"📍 Base URL: {base_url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try health check endpoint
            try:
                health_response = await client.get(f"{base_url}/mcp")
                print(f"📊 Health Check Status: {health_response.status_code}")
                if health_response.status_code == 200:
                    print("✅ Server is online and responding!")
                elif health_response.status_code == 406:
                    print("✅ Server is online! (406 means MCP protocol is active)")
                else:
                    print(f"📝 Health Response: {health_response.text[:200]}")
            except Exception as e:
                print(f"❌ Health check failed: {e}")
            
            # Try to get server info
            try:
                print("\n🔧 Testing MCP protocol...")
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # Try a simple ping
                ping_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "ping"
                }
                
                ping_response = await client.post(f"{base_url}/mcp", headers=headers, json=ping_payload)
                print(f"📊 MCP Ping Status: {ping_response.status_code}")
                print(f"📝 Response: {ping_response.text[:300]}")
                
                if "tools" in ping_response.text or "WordPress" in ping_response.text:
                    print("✅ WordPress MCP server is responding!")
                    
            except Exception as e:
                print(f"❌ MCP test failed: {e}")
                
    except Exception as e:
        print(f"❌ Server check failed: {e}")

async def estimate_tools_from_claude():
    """Provide guidance on checking tools from Claude Desktop"""
    print("\n" + "="*60)
    print("🎯 HOW TO CHECK TOOLS COUNT IN CLAUDE DESKTOP:")
    print("="*60)
    print("1. Open Claude Desktop")
    print("2. Go to Settings → Custom Connectors")
    print("3. Find your 'WordPress MCP Server' connector")
    print("4. Look at the number next to the connector name")
    print("5. If you see '40' - disconnect and reconnect")
    print("6. After the fix, you should see 36+ tools")
    print("\n📊 Expected Results:")
    print("   • Before fix: ~40 tools (incorrect)")
    print("   • After fix: 36+ tools (all WordPress tools)")
    print("\n🔧 If still showing 40:")
    print("   • Disconnect the connector")
    print("   • Wait 30 seconds")
    print("   • Reconnect using same URL")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(check_server_status())
    asyncio.run(estimate_tools_from_claude())
