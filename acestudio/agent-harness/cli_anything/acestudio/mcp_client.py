"""ACE Studio MCP client."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib import error, request


DEFAULT_MCP_URL = "http://localhost:21572/mcp"
DEFAULT_PROTOCOL_VERSION = "2025-03-26"


class MCPClientError(RuntimeError):
    """Base MCP client error."""


class ServerUnavailableError(MCPClientError):
    """ACE Studio MCP server is unreachable."""


class SessionInitializationError(MCPClientError):
    """Unable to initialize MCP session."""


class ToolCallError(MCPClientError):
    """MCP tool call failed."""


class InvalidContextError(MCPClientError):
    """Command requires ACE Studio state that is not available."""


class ValidationError(MCPClientError):
    """User input or server response is invalid."""


@dataclass
class MCPResponse:
    body: dict[str, Any]
    headers: dict[str, str]
    status: int


class ACEStudioMCPClient:
    """Small MCP client tailored for ACE Studio's local server."""

    def __init__(
        self,
        url: str = DEFAULT_MCP_URL,
        timeout: float = 10.0,
        protocol_version: str = DEFAULT_PROTOCOL_VERSION,
        client_name: str = "cli-anything-acestudio",
        client_version: str = "1.0.0",
    ):
        self.url = url
        self.timeout = timeout
        self.protocol_version = protocol_version
        self.client_name = client_name
        self.client_version = client_version
        self.session_id: str | None = None
        self._rpc_id = 0
        self._initialized = False
        self._initialize_result: dict[str, Any] | None = None

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _headers(self, include_session: bool = True) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if include_session and self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _request(self, payload: dict[str, Any], include_session: bool = True) -> MCPResponse:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.url,
            data=data,
            headers=self._headers(include_session=include_session),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw) if raw else {}
                headers = {k: v for k, v in resp.headers.items()}
                return MCPResponse(body=body, headers=headers, status=resp.status)
        except error.HTTPError as exc:
            try:
                raw = exc.read().decode("utf-8")
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {"error": {"message": str(exc)}}
            raise ToolCallError(self._extract_error_message(parsed) or str(exc)) from exc
        except (error.URLError, socket.timeout, TimeoutError) as exc:
            raise ServerUnavailableError(
                f"ACE Studio MCP server is unavailable at {self.url}. "
                "Make sure ACE Studio is running and MCP Server is enabled."
            ) from exc

    @staticmethod
    def _extract_error_message(body: dict[str, Any]) -> str | None:
        error_obj = body.get("error")
        if isinstance(error_obj, dict):
            message = error_obj.get("message")
            if isinstance(message, str):
                return message
        result_obj = body.get("result")
        if isinstance(result_obj, dict):
            message = result_obj.get("message")
            if isinstance(message, str):
                return message
        return None

    def initialize(self, force: bool = False) -> dict[str, Any]:
        if self._initialized and not force:
            return self._initialize_result or {}

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version,
                },
            },
        }
        response = self._request(payload, include_session=False)
        session_id = response.headers.get("Mcp-Session-Id")
        if not session_id:
            raise SessionInitializationError("MCP initialize response did not include Mcp-Session-Id.")
        self.session_id = session_id
        result = response.body.get("result")
        if not isinstance(result, dict):
            raise SessionInitializationError("MCP initialize response did not include a valid result object.")
        self._notify_initialized()
        self._initialize_result = result
        self._initialized = True
        return result

    def _notify_initialized(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        self._request(payload, include_session=True)

    def ensure_initialized(self) -> dict[str, Any]:
        return self.initialize(force=False)

    def call_method(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.ensure_initialized()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        try:
            response = self._request(payload, include_session=True)
        except ToolCallError as exc:
            message = str(exc)
            if "Session not initialized" in message or "会话" in message:
                self._initialized = False
                self.session_id = None
                self.initialize(force=True)
                response = self._request(payload, include_session=True)
            else:
                raise

        body = response.body
        error_message = self._extract_error_message(body)
        if error_message and "error" in body:
            raise ToolCallError(error_message)
        result = body.get("result")
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        result = self.call_method("tools/list", {})
        tools = result.get("tools", []) if isinstance(result, dict) else []
        if not isinstance(tools, list):
            raise ToolCallError("Invalid tools/list response from ACE Studio MCP server.")
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = self.call_method("tools/call", {"name": name, "arguments": arguments or {}})
        if not isinstance(result, dict):
            return result
        if result.get("isError"):
            raise ToolCallError(self._extract_tool_result_message(result))
        if "structuredContent" in result:
            return result["structuredContent"]
        content = result.get("content", [])
        parsed = self._parse_content(content)
        if parsed is not None:
            return parsed
        return result

    @staticmethod
    def _extract_tool_result_message(result: dict[str, Any]) -> str:
        content = result.get("content", [])
        parsed = ACEStudioMCPClient._parse_content(content)
        if isinstance(parsed, dict) and "error" in parsed:
            return str(parsed["error"])
        if isinstance(parsed, str):
            return parsed
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
            if text_parts:
                return " | ".join(text_parts)
        return "ACE Studio MCP tool call failed."

    @staticmethod
    def _parse_content(content: Any) -> Any:
        if not isinstance(content, list):
            return None
        json_candidate = None
        text_candidate = None
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            text_candidate = text
            try:
                json_candidate = json.loads(text)
            except json.JSONDecodeError:
                continue
        return json_candidate if json_candidate is not None else text_candidate
