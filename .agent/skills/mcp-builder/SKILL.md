---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).
license: Complete terms in LICENSE.txt
---

# MCP Server Development Guide

## Overview

Create MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. The quality of an MCP server is measured by how well it enables LLMs to accomplish real-world tasks.

## Process

### Phase 1: Deep Research and Planning

#### 1.1 Understand Modern MCP Design

**API Coverage vs. Workflow Tools:**
Balance comprehensive API endpoint coverage with specialized workflow tools.

**Tool Naming and Discoverability:**
Clear, descriptive tool names help agents find the right tools quickly. Use consistent prefixes (e.g., `github_create_issue`, `github_list_repos`).

**Context Management:**
Agents benefit from concise tool descriptions and the ability to filter/paginate results. Design tools that return focused, relevant data.

**Actionable Error Messages:**
Error messages should guide agents toward solutions with specific suggestions and next steps.

#### 1.2 Study MCP Protocol Documentation

Start with the sitemap: `https://modelcontextprotocol.io/sitemap.xml`

Key pages to review:

- Specification overview and architecture
- Transport mechanisms (streamable HTTP, stdio)
- Tool, resource, and prompt definitions

#### 1.3 Study Framework Documentation

**Recommended stack:**

- **Language**: TypeScript (high-quality SDK support)
- **Transport**: Streamable HTTP for remote servers, stdio for local servers.

### Phase 2: Implementation

#### 2.1 Set Up Project Structure

See language-specific guides for project setup.

#### 2.2 Implement Core Infrastructure

Create shared utilities:

- API client with authentication
- Error handling helpers
- Response formatting (JSON/Markdown)
- Pagination support

#### 2.3 Implement Tools

For each tool:

- **Input Schema**: Use Zod (TypeScript) or Pydantic (Python)
- **Output Schema**: Define `outputSchema` where possible
- **Tool Description**: Concise summary of functionality
- **Annotations**: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

### Phase 3: Review and Test

#### 3.1 Code Quality

- No duplicated code (DRY principle)
- Consistent error handling
- Full type coverage
- Clear tool descriptions

#### 3.2 Build and Test

**TypeScript:** Run `npm run build` to verify compilation
**Python:** Verify syntax: `python -m py_compile your_server.py`

### Phase 4: Create Evaluations

Create 10 complex, realistic evaluation questions that test whether LLMs can effectively use your MCP server.

## Reference Files

- **MCP Protocol**: `https://modelcontextprotocol.io/sitemap.xml`
- **Python SDK**: `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- **TypeScript SDK**: `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
