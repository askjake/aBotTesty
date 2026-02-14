import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Dict, List

from langchain_core.tools import BaseTool

from app.config import get_settings
from app.agent.agents.utils import get_mcp_tools
from app.tools.web_search import public_web_search
from app.tools.internal_search import internal_search
from app.tools.netra_search import netra_search, netra_url_builder
from app.tools.dish_internal_tools import dish_internal_tool, dish_internal_tool_url, dish_internal_tools_info
from app.tools.cluster_inspect import cluster_inspect
from app.agent_mode.tools import (
    agent_git_clone,
    agent_create_venv,
    agent_run_python,
    agent_list_artifacts,
    agent_run_shell,
)
from app.tools.log_assist_gateway import (
    logassist_web_search,
    logassist_get_journal_files,
    logassist_append_journal,
    logassist_trigger_workflow,
    logassist_embed_content,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory cache of asynchronously-initialised tool sets (MCP clients, etc.)
_ASYNC_TOOL_CACHE: Dict[str, List[BaseTool]] = {}

# Factories that produce tool lists on demand.
_TOOL_FACTORIES: Dict[str, Callable[[], List[BaseTool]]] = {}

# Factories that may require async initialisation (MCP clients).
_ASYNC_TOOL_FACTORIES: Dict[str, Callable[[], Awaitable[List[BaseTool]] | List[BaseTool]]] = {}

# Only enable MCP tool sets that are configured
if settings.BETAREPORT_MCP_CONFIG:
    _ASYNC_TOOL_FACTORIES["beta_report"] = lambda: get_mcp_tools(
        settings.BETAREPORT_MCP_CONFIG
    )

if getattr(settings, "ENABLE_INTERNAL_TOOLS_MCP", False):
    _ASYNC_TOOL_FACTORIES["internal_tools"] = lambda: get_mcp_tools(
        settings.INTERNAL_TOOLS_MCP_CONFIG
    )

# Pure-Python tools that don't need MCP-style startup.
_TOOL_FACTORIES.update(
    {
        # Web + internal search tools used by the chat agent.
        "search": lambda: [public_web_search, internal_search, netra_search, dish_internal_tool, cluster_inspect],

        # Coverity / Log Assist tools via the Flask gateway (HTTP, not MCP).
        "log_assist": lambda: [
            logassist_web_search,
            logassist_get_journal_files,
            logassist_append_journal,
            logassist_trigger_workflow,
            logassist_embed_content,
        ],

        # Filesystem + process sandbox used in agent mode.
        "agent_mode": lambda: [
            agent_git_clone,
            agent_create_venv,
            agent_run_python,
            agent_list_artifacts,
            agent_run_shell,
        ],
    }
)

async def initialize_mcp_tools() -> None:
    """Initialise all async/MCP-backed tool sets.

    This is called once from FastAPI's lifespan handler so that MCP clients
    are ready before any traffic hits the agents.
    """
    global _ASYNC_TOOL_CACHE, _TOOL_FACTORIES

    if _ASYNC_TOOL_CACHE:
        # Already initialised.
        return

    for name, factory in _ASYNC_TOOL_FACTORIES.items():
        try:
            tools = factory()
            if asyncio.iscoroutine(tools) or isinstance(tools, Awaitable):
                tools = await tools
            _ASYNC_TOOL_CACHE[name] = list(tools)
            logger.info(
                "Loaded MCP tool set '%s' with %d tools",
                name,
                len(_ASYNC_TOOL_CACHE[name]),
            )
        except Exception as exc:  # noqa: BLE001
            # Don't fail the whole app if a single MCP server is unreachable.
            logger.warning(
                "Failed to initialise MCP tool set %s: %s; continuing with it disabled.",
                name,
                exc,
            )
            _ASYNC_TOOL_CACHE[name] = []

    # Wrap the async-initialised sets in simple factories so callers don't have
    # to care whether a given tool family is MCP-backed or not.
    for name in _ASYNC_TOOL_FACTORIES.keys():
        if name not in _TOOL_FACTORIES:
            _TOOL_FACTORIES[name] = lambda n=name: _ASYNC_TOOL_CACHE.get(n, [])


def get_tools_set(tool_type: str) -> List[BaseTool]:
    """Return the configured tool set for a given logical type.

    Known types as of now:
      - "search":         public web search + internal_search + netra_search + cluster_inspect
      - "beta_report":    MCP tools for the beta-report agent
      - "log_assist":     MCP tools for Coverity/Log Assist
      - "internal_tools": Generic internal MCP utilities
      - "agent_mode":     Filesystem + process sandbox tools

    Unknown types return an empty list.
    """
    factory = _TOOL_FACTORIES.get(tool_type)
    if not factory:
        logger.warning("Unknown tool_type %r requested; returning empty tool list.", tool_type)
        return []
    return list(factory())
