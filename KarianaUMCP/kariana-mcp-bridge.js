#!/usr/bin/env node

/**
 * KarianaUMCP MCP Bridge for Claude Desktop
 * ==========================================
 * Bridges Claude Desktop to the KarianaUMCP socket server via HTTP.
 *
 * Usage:
 *   Add to Claude Desktop config:
 *   {
 *     "mcpServers": {
 *       "kariana": {
 *         "command": "node",
 *         "args": ["/path/to/kariana-mcp-bridge.js"],
 *         "env": {
 *           "KARIANA_URL": "http://localhost:8765"
 *         }
 *       }
 *     }
 *   }
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

// Configuration
const KARIANA_URL = process.env.KARIANA_URL || 'http://localhost:8765';
const SOCKET_HOST = process.env.SOCKET_HOST || 'localhost';
const SOCKET_PORT = parseInt(process.env.SOCKET_PORT || '9877');
const TIMEOUT = parseInt(process.env.TIMEOUT || '30000');

// Create MCP server
const server = new Server(
  {
    name: 'kariana-umcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Send message directly to socket server
 */
async function sendToSocket(message) {
  const net = await import('net');

  return new Promise((resolve, reject) => {
    const socket = new net.default.Socket();
    let responseData = '';

    socket.setTimeout(TIMEOUT);

    socket.on('timeout', () => {
      socket.destroy();
      reject(new Error('Socket timeout'));
    });

    socket.connect(SOCKET_PORT, SOCKET_HOST, () => {
      socket.write(JSON.stringify(message) + '\n');
    });

    socket.on('data', (data) => {
      responseData += data.toString();

      // Check for complete JSON response
      try {
        const parsed = JSON.parse(responseData.trim());
        socket.destroy();
        resolve(parsed);
      } catch (e) {
        // Wait for more data
      }
    });

    socket.on('error', (err) => {
      reject(err);
    });

    socket.on('close', () => {
      if (responseData) {
        try {
          resolve(JSON.parse(responseData.trim()));
        } catch (e) {
          reject(new Error('Invalid JSON response'));
        }
      }
    });
  });
}

/**
 * Send message via HTTP proxy
 */
async function sendToHttp(message) {
  const response = await fetch(`${KARIANA_URL}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
  });

  if (!response.ok) {
    throw new Error(`HTTP error: ${response.status}`);
  }

  return await response.json();
}

/**
 * Send message to KarianaUMCP (tries socket first, then HTTP)
 */
async function sendMessage(message) {
  try {
    // Try direct socket first
    return await sendToSocket(message);
  } catch (socketErr) {
    // Fallback to HTTP
    try {
      return await sendToHttp(message);
    } catch (httpErr) {
      throw new Error(`Connection failed: Socket(${socketErr.message}), HTTP(${httpErr.message})`);
    }
  }
}

// Handle list tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  try {
    const response = await sendMessage({ type: 'list_functions' });

    if (response.success && response.functions) {
      const tools = response.functions.map((func) => ({
        name: func.name,
        description: func.description || `KarianaUMCP tool: ${func.name}`,
        inputSchema: {
          type: 'object',
          properties: Object.entries(func.parameters || {}).reduce((acc, [key, value]) => {
            acc[key] = {
              type: value.type === 'integer' ? 'number' : value.type || 'string',
              description: value.description || '',
            };
            return acc;
          }, {}),
          required: Object.entries(func.parameters || {})
            .filter(([, v]) => v.required)
            .map(([k]) => k),
        },
      }));

      return { tools };
    }

    // Return minimal tools on error
    return {
      tools: [
        {
          name: 'ping',
          description: 'Test KarianaUMCP connection',
          inputSchema: { type: 'object', properties: {} },
        },
        {
          name: 'list_actors',
          description: 'List all actors in the Unreal level',
          inputSchema: {
            type: 'object',
            properties: {
              class_filter: { type: 'string', description: 'Filter by actor class' },
            },
          },
        },
        {
          name: 'execute_python',
          description: 'Execute Python code in Unreal Engine',
          inputSchema: {
            type: 'object',
            properties: {
              code: { type: 'string', description: 'Python code to execute' },
            },
            required: ['code'],
          },
        },
      ],
    };
  } catch (error) {
    console.error('Failed to list tools:', error.message);
    return { tools: [] };
  }
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const message = { type: name, ...args };
    const response = await sendMessage(message);

    // Format response for MCP
    const content = [];

    if (response.success !== undefined) {
      if (response.success) {
        // Format successful response
        let text = '';

        if (response.output) {
          text += response.output;
        }

        if (response.result) {
          text += (text ? '\n' : '') + `Result: ${JSON.stringify(response.result, null, 2)}`;
        }

        if (response.actors) {
          text += (text ? '\n' : '') + `Actors:\n${response.actors.map(a => `  - ${typeof a === 'string' ? a : a.name}`).join('\n')}`;
        }

        if (response.image) {
          content.push({
            type: 'image',
            data: response.image,
            mimeType: `image/${response.format || 'png'}`,
          });
        }

        if (!text && !response.image) {
          text = JSON.stringify(response, null, 2);
        }

        if (text) {
          content.push({ type: 'text', text });
        }
      } else {
        // Error response
        content.push({
          type: 'text',
          text: `Error: ${response.error || 'Unknown error'}`,
        });
      }
    } else {
      // Raw response
      content.push({
        type: 'text',
        text: JSON.stringify(response, null, 2),
      });
    }

    return { content };
  } catch (error) {
    return {
      content: [{ type: 'text', text: `Failed to call tool ${name}: ${error.message}` }],
      isError: true,
    };
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('KarianaUMCP MCP bridge started');
}

main().catch(console.error);
