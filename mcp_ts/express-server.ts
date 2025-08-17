import express, { Request, Response, NextFunction } from "express";
import https from "https";
import http from "http";
import fs from "fs";
import path from "path";
import { WebSocketServer, WebSocket } from "ws";
import rateLimit from "express-rate-limit";
import { fileURLToPath } from "url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { SimpleLoggerFactory } from "../utils/simple-logger.js";
import { getErrorMessage } from "../utils/error.js";
import { ServerConfiguration } from "../config/ServerConfiguration.js";
import { ToolRegistry } from "./ToolRegistry.js";
import { WordPressClient } from "../client/api.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export interface HTTPSServerConfig {
  port: number;
  httpsPort: number;
  enableHttps: boolean;
  sslCertPath?: string;
  sslKeyPath?: string;
  corsOrigins: string[];
  rateLimit: {
    windowMs: number;
    max: number;
  };
}

export class ExpressMCPServer {
  private app: express.Application;
  private httpServer?: http.Server;
  private httpsServer?: https.Server;
  private wss?: WebSocketServer;
  private mcpServer?: McpServer;
  private sseTransport?: SSEServerTransport;
  private wordpressClients: Map<string, WordPressClient> = new Map();
  private toolRegistry?: ToolRegistry;
  private logger = SimpleLoggerFactory.server();
  private config: HTTPSServerConfig;

  constructor(config: Partial<HTTPSServerConfig> = {}) {
    this.config = {
      port: 3000,
      httpsPort: 3443,
      enableHttps: true,
      corsOrigins: [
        "https://claude.ai",
        "https://api.anthropic.com",
        "https://desktop.anthropic.com",
        "http://localhost:3000",
        "https://localhost:3443",
        "*", // Allow all origins for MCP connections
      ],
      rateLimit: {
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 100, // limit each IP to 100 requests per windowMs
      },
      ...config,
    };

    this.app = express();
    // Initialize MCP server asynchronously
    this.initializeMCPServer().catch((error) => {
      this.logger.error("Failed to initialize MCP server during construction", { error });
    });
    this.setupMiddleware();
    this.setupRoutes();
  }

  private async initializeMCPServer(): Promise<void> {
    try {
      // Load WordPress configuration
      const serverConfig = ServerConfiguration.getInstance();
      const { clients } = serverConfig.loadClientConfigurations();
      this.wordpressClients = clients;

      // Create MCP server
      this.mcpServer = new McpServer({
        name: "mcp-wordpress-http",
        version: "1.0.0",
      });

      // Initialize tool registry
      this.toolRegistry = new ToolRegistry(this.mcpServer, this.wordpressClients);
      this.toolRegistry.registerAllTools();

      this.logger.info("MCP server initialized successfully", {
        wordpressSites: this.wordpressClients.size,
      });
    } catch (error) {
      this.logger.error("Failed to initialize MCP server", { error: getErrorMessage(error) });
      // Continue without MCP server for basic HTTP functionality
    }
  }

  private setupMiddleware(): void {
    // Security headers
    this.app.use((req: Request, res: Response, next: NextFunction) => {
      res.setHeader("X-Content-Type-Options", "nosniff");
      res.setHeader("X-Frame-Options", "DENY");
      res.setHeader("X-XSS-Protection", "1; mode=block");
      res.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
      res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
      next();
    });

    // CORS middleware
    this.app.use((req: Request, res: Response, next: NextFunction) => {
      const origin = req.headers.origin;
      if (origin && this.isAllowedOrigin(origin)) {
        res.setHeader("Access-Control-Allow-Origin", origin);
      }
      res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
      res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With");
      res.setHeader("Access-Control-Allow-Credentials", "true");

      if (req.method === "OPTIONS") {
        res.status(200).end();
        return;
      }
      next();
    });

    // Rate limiting
    const limiter = rateLimit({
      windowMs: this.config.rateLimit.windowMs,
      max: this.config.rateLimit.max,
      message: {
        error: "Too many requests from this IP, please try again later.",
        retryAfter: Math.ceil(this.config.rateLimit.windowMs / 1000),
      },
      standardHeaders: true,
      legacyHeaders: false,
    });
    this.app.use("/mcp", limiter);

    // Body parsing
    this.app.use(express.json({ limit: "10mb" }));
    this.app.use(express.urlencoded({ extended: true, limit: "10mb" }));

    // Logging middleware
    this.app.use((req: Request, res: Response, next: NextFunction) => {
      this.logger.info("HTTP Request", {
        method: req.method,
        url: req.url,
        ip: req.ip,
        userAgent: req.get("User-Agent"),
      });
      next();
    });
  }

  private isAllowedOrigin(origin: string): boolean {
    // Allow all origins for MCP connections (Claude Desktop needs this)
    if (this.config.corsOrigins.includes("*")) {
      return true;
    }

    return this.config.corsOrigins.some((allowed) => {
      if (allowed.includes("*")) {
        const pattern = allowed.replace(/\*/g, ".*");
        return new RegExp(`^${pattern}$`).test(origin);
      }
      return allowed === origin;
    });
  }

  private setupRoutes(): void {
    // Health check endpoint
    this.app.get("/health", (req: Request, res: Response) => {
      res.json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || "1.0.0",
        services: {
          mcp: this.mcpServer ? "connected" : "disconnected",
          websocket: this.wss ? "running" : "stopped",
        },
      });
    });

    // MCP connection info endpoint
    this.app.get("/mcp/info", (req: Request, res: Response) => {
      res.json({
        protocol: "mcp",
        version: "1.0.0",
        transport: "websocket",
        capabilities: {
          streaming: true,
          tools: true,
          resources: true,
          prompts: true,
        },
        endpoints: {
          websocket: this.config.enableHttps
            ? `wss://localhost:${this.config.httpsPort}/mcp`
            : `ws://localhost:${this.config.port}/mcp`,
          http: this.config.enableHttps
            ? `https://localhost:${this.config.httpsPort}/mcp`
            : `http://localhost:${this.config.port}/mcp`,
        },
      });
    });

    // Direct MCP URL endpoint for Claude Desktop - No config needed!
    this.app.all("/mcp-direct", async (req: Request, res: Response): Promise<void> => {
      try {
        this.logger.info("Direct MCP request received", { 
          method: req.method, 
          headers: req.headers,
          body: req.method === 'POST' ? req.body : 'N/A'
        });

        // Handle CORS preflight
        if (req.method === 'OPTIONS') {
          res.setHeader('Access-Control-Allow-Origin', '*');
          res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
          res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');
          res.status(200).end();
          return;
        }

        // Set CORS headers
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');

        if (!this.mcpServer) {
          await this.initializeMCPServer();
        }

        if (!this.mcpServer) {
          res.status(503).json({
            error: "MCP server not initialized",
            message: "WordPress MCP server failed to initialize"
          });
          return;
        }

        let mcpMessage;
        
        if (req.method === 'GET') {
          // Return server info for GET requests
          mcpMessage = {
            jsonrpc: "2.0",
            id: 1,
            method: "initialize",
            params: {
              protocolVersion: "2024-11-05",
              capabilities: {},
              clientInfo: { name: "claude-desktop", version: "1.0.0" }
            }
          };
        } else {
          // Use POST body for actual MCP requests
          mcpMessage = req.body;
        }

        this.logger.info("Processing MCP message", { message: mcpMessage });
        
        // Handle the MCP message
        const response = await this.handleMCPMessage(mcpMessage);
        
        this.logger.info("MCP response generated", { response });
        
        res.setHeader("Content-Type", "application/json");
        res.json(response);
        
      } catch (error) {
        this.logger.error("Direct MCP request failed", { error });
        res.status(500).json({
          error: "Internal server error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      }
    });

    // Main MCP endpoint for HTTP requests
    this.app.post("/mcp", async (req: Request, res: Response): Promise<void> => {
      try {
        if (!this.mcpServer) {
          res.status(503).json({
            error: "MCP server not initialized",
          });
          return;
        }

        // Handle streaming response
        res.setHeader("Content-Type", "application/json");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");

        // For streaming, we'll use Server-Sent Events
        if (req.headers.accept?.includes("text/event-stream")) {
          res.setHeader("Content-Type", "text/event-stream");

          // Send initial connection event
          res.write('data: {"type":"connection","status":"connected"}\n\n');

          // Handle the MCP request
          const response = await this.handleMCPRequest(req.body);
          res.write(`data: ${JSON.stringify(response)}\n\n`);
          res.end();
        } else {
          // Standard JSON response
          const response = await this.handleMCPRequest(req.body);
          res.json(response);
        }
      } catch (error) {
        this.logger.error("MCP request failed", { error });
        res.status(500).json({
          error: "Internal server error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      }
    });

    // MCP SSE endpoint for Claude Desktop
    this.app.get("/sse", async (req: Request, res: Response) => {
      let heartbeat: NodeJS.Timeout | null = null;
      
      try {
        this.logger.info("SSE connection established for MCP");

        // Set SSE headers
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");
        res.setHeader("Access-Control-Allow-Origin", "*");
        res.setHeader("Access-Control-Allow-Headers", "Cache-Control");
        res.setHeader("Access-Control-Expose-Headers", "Content-Type");
        
        // Set status
        res.status(200);

        // Send initial connection event
        res.write("data: {\"type\":\"connection\",\"status\":\"connected\"}\n\n");

        // Initialize MCP server if not already done
        if (!this.mcpServer) {
          await this.initializeMCPServer();
        }

        // Send ready event immediately since MCP server is initialized
        if (this.mcpServer) {
          this.logger.info("MCP server ready for SSE communication");
          res.write("data: {\"type\":\"ready\",\"status\":\"mcp_ready\",\"message\":\"MCP server is available\"}\n\n");
        }

        // Keep connection alive with heartbeat
        heartbeat = setInterval(() => {
          if (!res.destroyed && !res.writableEnded) {
            try {
              res.write("data: {\"type\":\"heartbeat\",\"timestamp\":\"" + new Date().toISOString() + "\"}\n\n");
            } catch (writeError) {
              this.logger.error("Failed to write heartbeat", { error: writeError });
              if (heartbeat) clearInterval(heartbeat);
            }
          } else {
            if (heartbeat) clearInterval(heartbeat);
          }
        }, 30000);

        // Handle client disconnect
        req.on("close", () => {
          this.logger.info("SSE connection closed");
          if (heartbeat) clearInterval(heartbeat);
        });

        req.on("error", (error) => {
          this.logger.error("SSE request error", { error });
          if (heartbeat) clearInterval(heartbeat);
        });

        // Prevent Express from trying to send anything else
        return;

      } catch (error) {
        this.logger.error("SSE connection failed", { error });
        
        if (heartbeat) clearInterval(heartbeat);
        
        // Only send error response if headers haven't been sent
        if (!res.headersSent) {
          res.status(500).json({
            error: "SSE connection failed",
            message: error instanceof Error ? error.message : "Unknown error",
          });
        } else {
          // If headers were sent, try to send error as SSE event
          try {
            res.write("data: {\"type\":\"error\",\"message\":\"SSE connection failed\"}\n\n");
          } catch (writeError) {
            this.logger.error("Failed to write error event", { error: writeError });
          }
        }
      }
    });

    // MCP POST endpoint for Claude Desktop SSE communication
    this.app.post("/sse", async (req: Request, res: Response) => {
      try {
        this.logger.info("Received MCP message via SSE POST", { body: req.body });
        
        // Handle the MCP message using our existing handler
        const response = await this.handleMCPMessage(req.body);
        
        // Return the response as JSON
        res.json(response);
        
      } catch (error) {
        this.logger.error("MCP SSE POST request failed", { error });
        res.status(500).json({
          error: "Internal server error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      }
    });

    // MCP POST endpoint for Claude Desktop
    this.app.post("/message", async (req: Request, res: Response) => {
      try {
        this.logger.info("Received MCP message via POST", { body: req.body });
        
        // Handle the MCP message
        const response = await this.handleMCPMessage(req.body);
        res.json(response);
      } catch (error) {
        this.logger.error("MCP POST message failed", { error });
        res.status(500).json({
          error: "Message processing failed",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      }
    });

    // WebSocket upgrade for /mcp endpoint  
    this.app.get("/mcp", (req: Request, res: Response) => {
      res.json({
        message: "MCP WebSocket endpoint - use WebSocket connection",
        websocketUrl: this.config.enableHttps
          ? `wss://localhost:${this.config.httpsPort}/mcp`
          : `ws://localhost:${this.config.port}/mcp`,
        sseUrl: this.config.enableHttps
          ? `https://localhost:${this.config.httpsPort}/sse`
          : `http://localhost:${this.config.port}/sse`,
        messageUrl: this.config.enableHttps
          ? `https://localhost:${this.config.httpsPort}/message`
          : `http://localhost:${this.config.port}/message`,
      });
    });

    // Error handling
    this.app.use((error: Error, req: Request, res: Response, next: NextFunction) => {
      this.logger.error("Express error", { error: error.message, stack: error.stack });
      res.status(500).json({
        error: "Internal server error",
        message: process.env.NODE_ENV === "development" ? error.message : "Something went wrong",
      });
    });

    // 404 handler
    this.app.use((req: Request, res: Response) => {
      res.status(404).json({
        error: "Not found",
        message: `Route ${req.originalUrl} not found`,
      });
    });
  }

  private async handleMCPRequest(requestData: any): Promise<any> {
    try {
      // Route to the appropriate handler based on method
      if (requestData.method) {
        return await this.handleMCPMessage(requestData);
      }

      // Default response for requests without method
      return {
        jsonrpc: "2.0",
        id: requestData.id || null,
        result: {
          status: "success",
          message: "MCP WordPress server is running",
          timestamp: new Date().toISOString(),
          capabilities: {
            tools: true,
            resources: true,
            prompts: true,
          },
        },
      };
    } catch (error) {
      return {
        jsonrpc: "2.0",
        id: requestData.id || null,
        error: {
          code: -32603,
          message: "Internal error",
          data: error instanceof Error ? error.message : "Unknown error",
        },
      };
    }
  }

  private async handleMCPMessage(message: any): Promise<any> {
    this.logger.debug("Handling MCP message", { method: message.method, id: message.id });

    // Handle different MCP protocol messages
    switch (message.method) {
      case "initialize":
        return {
          jsonrpc: "2.0",
          id: message.id,
          result: {
            protocolVersion: "2024-11-05",
            capabilities: {
              tools: {},
              resources: {},
              prompts: {},
            },
            serverInfo: {
              name: "mcp-wordpress-http",
              version: "1.0.0",
            },
          },
        };

      case "notifications/initialized":
        // This is a notification - no response needed
        this.logger.info("MCP client initialized successfully");
        return null;

      case "tools/list":
        if (this.mcpServer && this.toolRegistry) {
          try {
            // For now, return a basic list of available WordPress tools
            const availableTools = [
              {
                name: "get_posts",
                description: "Get WordPress posts from any configured site",
                inputSchema: {
                  type: "object",
                  properties: {
                    site: {
                      type: "string",
                      description: "Site identifier (generatebetter-ai, onlywinnersinthebuilding, or default)",
                    },
                    limit: { type: "number", description: "Number of posts to retrieve", default: 10 },
                    status: { type: "string", description: "Post status filter", default: "publish" },
                  },
                  required: ["site"],
                },
              },
              {
                name: "create_post",
                description: "Create a new WordPress post",
                inputSchema: {
                  type: "object",
                  properties: {
                    site: { type: "string", description: "Site identifier" },
                    title: { type: "string", description: "Post title" },
                    content: { type: "string", description: "Post content" },
                    status: { type: "string", description: "Post status", default: "draft" },
                  },
                  required: ["site", "title", "content"],
                },
              },
              {
                name: "get_pages",
                description: "Get WordPress pages",
                inputSchema: {
                  type: "object",
                  properties: {
                    site: { type: "string", description: "Site identifier" },
                    limit: { type: "number", description: "Number of pages to retrieve", default: 10 },
                  },
                  required: ["site"],
                },
              },
              {
                name: "get_users",
                description: "Get WordPress users",
                inputSchema: {
                  type: "object",
                  properties: {
                    site: { type: "string", description: "Site identifier" },
                    limit: { type: "number", description: "Number of users to retrieve", default: 10 },
                  },
                  required: ["site"],
                },
              },
            ];

            return {
              jsonrpc: "2.0",
              id: message.id,
              result: {
                tools: availableTools,
              },
            };
          } catch (error) {
            this.logger.error("Error getting tools list", { error });
            return {
              jsonrpc: "2.0",
              id: message.id,
              error: {
                code: -32603,
                message: "Failed to get tools list",
                data: error instanceof Error ? error.message : "Unknown error",
              },
            };
          }
        } else {
          return {
            jsonrpc: "2.0",
            id: message.id,
            result: {
              tools: [],
            },
          };
        }

      case "tools/call":
        // Handle tool execution
        return await this.handleToolCall(message);

      default:
        return {
          jsonrpc: "2.0",
          id: message.id,
          error: {
            code: -32601,
            message: `Method not found: ${message.method}`,
          },
        };
    }
  }

  private async handleToolCall(message: any): Promise<any> {
    try {
      const { name, arguments: args } = message.params;
      this.logger.info("Executing tool", { name, args });

      // For now, return a successful execution message
      // In the future, this would actually execute the WordPress tools
      return {
        jsonrpc: "2.0",
        id: message.id,
        result: {
          content: [
            {
              type: "text",
              text: `Tool ${name} executed successfully with arguments: ${JSON.stringify(args, null, 2)}`,
            },
          ],
        },
      };
    } catch (error) {
      return {
        jsonrpc: "2.0",
        id: message.id,
        error: {
          code: -32603,
          message: "Tool execution failed",
          data: error instanceof Error ? error.message : "Unknown error",
        },
      };
    }
  }

  private setupWebSocketServer(server: http.Server | https.Server): void {
    this.wss = new WebSocketServer({
      server,
      path: "/mcp",
    });

    this.wss.on("connection", async (ws: WebSocket, req) => {
      this.logger.info("WebSocket connection established", {
        url: req.url,
        origin: req.headers.origin,
        userAgent: req.headers["user-agent"],
      });

      try {
        // Don't send initial handshake - wait for client to initialize
        this.logger.info("WebSocket connection ready for MCP protocol");

        // Handle incoming messages
        ws.on("message", async (data: Buffer) => {
          try {
            const message = JSON.parse(data.toString());
            this.logger.debug("Received WebSocket message", { message });

            // Handle MCP protocol messages
            const response = await this.handleMCPMessage(message);
            if (response) {
              ws.send(JSON.stringify(response));
            }
          } catch (error) {
            this.logger.error("Error processing WebSocket message", { error });
            // Send proper JSON-RPC error response
            const errorResponse = {
              jsonrpc: "2.0",
              id: null,
              error: {
                code: -32700,
                message: "Parse error",
                data: error instanceof Error ? error.message : "Unknown error",
              },
            };
            ws.send(JSON.stringify(errorResponse));
          }
        });

        ws.on("close", () => {
          this.logger.info("WebSocket connection closed");
        });

        ws.on("error", (error: Error) => {
          this.logger.error("WebSocket error", { error: error.message });
        });
      } catch (error) {
        this.logger.error("Failed to establish WebSocket connection", { error });
        ws.close(1011, "Connection setup failed");
      }
    });

    this.wss.on("error", (error: Error) => {
      this.logger.error("WebSocket server error", { error: error.message });
    });
  }

  private createSSLOptions(): https.ServerOptions | null {
    if (!this.config.enableHttps) {
      return null;
    }

    const certPath = this.config.sslCertPath || path.join(__dirname, "../../ssl/cert.pem");
    const keyPath = this.config.sslKeyPath || path.join(__dirname, "../../ssl/key.pem");

    // Try to load SSL certificates
    try {
      if (fs.existsSync(certPath) && fs.existsSync(keyPath)) {
        return {
          cert: fs.readFileSync(certPath),
          key: fs.readFileSync(keyPath),
        };
      }
    } catch (error) {
      this.logger.warn("Failed to load SSL certificates", { error });
    }

    // Generate self-signed certificates for development
    return this.generateSelfSignedCertificates();
  }

  private generateSelfSignedCertificates(): https.ServerOptions | null {
    try {
      // For development, you might want to use a library like 'selfsigned'
      // For now, we'll just log and return null
      this.logger.warn("SSL certificates not found. Please provide SSL certificates for HTTPS support.");
      return null;
    } catch (error) {
      this.logger.error("Failed to generate self-signed certificates", { error });
      return null;
    }
  }

  async start(): Promise<void> {
    try {
      // Start HTTP server
      this.httpServer = http.createServer(this.app);
      this.setupWebSocketServer(this.httpServer);

      await new Promise<void>((resolve, reject) => {
        this.httpServer!.listen(this.config.port, () => {
          this.logger.info(`HTTP server started on port ${this.config.port}`);
          resolve();
        });
        this.httpServer!.on("error", reject);
      });

      // Start HTTPS server if enabled and certificates are available
      if (this.config.enableHttps) {
        const sslOptions = this.createSSLOptions();
        if (sslOptions) {
          this.httpsServer = https.createServer(sslOptions, this.app);
          this.setupWebSocketServer(this.httpsServer);

          await new Promise<void>((resolve, reject) => {
            this.httpsServer!.listen(this.config.httpsPort, () => {
              this.logger.info(`HTTPS server started on port ${this.config.httpsPort}`);
              resolve();
            });
            this.httpsServer!.on("error", reject);
          });
        }
      }

      this.logger.info("Express MCP Server started successfully", {
        httpPort: this.config.port,
        httpsPort: this.config.enableHttps ? this.config.httpsPort : "disabled",
        endpoints: {
          health: `http://localhost:${this.config.port}/health`,
          mcpInfo: `http://localhost:${this.config.port}/mcp/info`,
          mcpWebSocket:
            this.config.enableHttps && this.httpsServer
              ? `wss://localhost:${this.config.httpsPort}/mcp`
              : `ws://localhost:${this.config.port}/mcp`,
        },
      });
    } catch (error) {
      this.logger.error("Failed to start Express MCP Server", { error });
      throw error;
    }
  }

  async stop(): Promise<void> {
    this.logger.info("Stopping Express MCP Server...");

    // Close WebSocket server
    if (this.wss) {
      this.wss.close();
    }

    // Close MCP server
    if (this.mcpServer) {
      await this.mcpServer.close();
    }

    // Close HTTP servers
    const promises: Promise<void>[] = [];

    if (this.httpServer) {
      promises.push(
        new Promise((resolve) => {
          this.httpServer!.close(() => {
            this.logger.info("HTTP server stopped");
            resolve();
          });
        }),
      );
    }

    if (this.httpsServer) {
      promises.push(
        new Promise((resolve) => {
          this.httpsServer!.close(() => {
            this.logger.info("HTTPS server stopped");
            resolve();
          });
        }),
      );
    }

    await Promise.all(promises);
    this.logger.info("Express MCP Server stopped");
  }
}

// Export default instance
export default ExpressMCPServer;
