from typing import Optional, List
from .contracts import ToolContract

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolContract] = {}

    def register(self, tool: ToolContract) -> None:
        self._tools[tool.tool_id] = tool

    def get_tool(self, tool_id: str) -> Optional[ToolContract]:
        return self._tools.get(tool_id)

    def list_tools(self) -> List[ToolContract]:
        return list(self._tools.values())

    def search(self, query: str) -> List[ToolContract]:
        query = query.lower()
        return [
            tool for tool in self._tools.values()
            if query in tool.tool_id.lower() or query in tool.description.lower()
        ]
