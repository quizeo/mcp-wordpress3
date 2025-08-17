#!/usr/bin/env node

import { ExpressMCPServer, HTTPSServerConfig } from "./server/express-server.js";
import { SimpleLoggerFactory } from "./utils/simple-logger.js";
import { getErrorMessage } from "./utils/error.js";

const logger = SimpleLoggerFactory.server();

/**
 * HTTP/HTTPS MCP Server for WordPress
 * Provides HTTP and WebSocket endpoints for MCP communication
 */
async function startHTTPServer() {
  try {
    // Configuration for the Express server
    const config: Partial<HTTPSServerConfig> = {
      port: parseInt(process.env.PORT || process.env.HTTP_PORT || "3000", 10),
      httpsPort: parseInt(process.env.HTTPS_PORT || "3443", 10),
      enableHttps: process.env.HTTPS_ENABLED === "true" || process.env.ENABLE_HTTPS === "true",
      ...(process.env.SSL_CERT_PATH && { sslCertPath: process.env.SSL_CERT_PATH }),
      ...(process.env.SSL_KEY_PATH && { sslKeyPath: process.env.SSL_KEY_PATH }),
      corsOrigins: [
        "https://claude.ai",
        "https://api.anthropic.com",
        "http://localhost:3000",
        "https://localhost:3443",
        ...(process.env.CORS_ORIGIN && process.env.CORS_ORIGIN !== "*" ? [process.env.CORS_ORIGIN] : []),
      ],
      rateLimit: {
        windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || "900000", 10), // 15 minutes
        max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || process.env.RATE_LIMIT_MAX || "100", 10), // limit each IP
      },
    };

    logger.info("Starting Express MCP Server...", {
      httpPort: config.port,
      httpsPort: config.httpsPort,
      httpsEnabled: config.enableHttps,
    });

    // Create and start the server
    const server = new ExpressMCPServer(config);
    await server.start();

    // Handle graceful shutdown
    const shutdown = async () => {
      logger.info("Received shutdown signal, stopping server...");
      try {
        await server.stop();
        process.exit(0);
      } catch (error) {
        logger.error("Error during shutdown", { error: getErrorMessage(error) });
        process.exit(1);
      }
    };

    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);
    process.on("SIGQUIT", shutdown);

    // Handle uncaught exceptions
    process.on("uncaughtException", (error) => {
      logger.fatal("Uncaught exception", { error: getErrorMessage(error) });
      process.exit(1);
    });

    process.on("unhandledRejection", (reason, promise) => {
      logger.fatal("Unhandled rejection", {
        reason: getErrorMessage(reason as Error),
        promise,
      });
      process.exit(1);
    });

    logger.info("Express MCP Server is running and ready to accept connections");
  } catch (error) {
    logger.fatal("Failed to start Express MCP Server", {
      error: getErrorMessage(error),
    });
    process.exit(1);
  }
}

// Check if this is the main module
const isMainModule = process.argv[1]?.endsWith("http-server.js") || process.argv[1]?.includes("http-server");

if (isMainModule) {
  startHTTPServer();
}

export { startHTTPServer };
