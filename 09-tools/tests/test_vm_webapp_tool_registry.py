import pytest
from vm_webapp.tooling.contracts import ToolContract, ToolResult
from vm_webapp.tooling.registry import ToolRegistry

class MockTool(ToolContract):
    @property
    def tool_id(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    def execute(self, params: dict) -> ToolResult:
        return ToolResult(success=True, data={"echo": params.get("input")})

def test_registry_registers_searches_and_lists_tools() -> None:
    registry = ToolRegistry()
    tool = MockTool()
    
    registry.register(tool)
    
    # Check listing
    all_tools = registry.list_tools()
    assert tool.tool_id in [t.tool_id for t in all_tools]
    
    # Check searching
    found = registry.search("mock")
    assert len(found) >= 1
    assert found[0].tool_id == "mock_tool"

    # Check getting by ID
    retrieved = registry.get_tool("mock_tool")
    assert retrieved is not None
    assert retrieved.tool_id == "mock_tool"
