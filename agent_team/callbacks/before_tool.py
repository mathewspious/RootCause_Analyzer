from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from typing import Optional, Dict, Any


## Code to block the call to check sensor-C
def block_tool_guardrail(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Check if the tool call is for sensor-C
    if so, block the call
    """
    tool_name = tool.name

    target_tool = "list_transaction_ids_by_device"
    target_device = "sensor-c"

    print(f"calling {tool_name}")

    if tool_name == target_tool:
        device_arg = args.get("device_name", "")
        if device_arg and device_arg.lower() == target_device:
            tool_context.state["guardrail_tool_block_triggered"] = True
            return {
                "status": "error",
                "error_message": f"transaction status check is not allowed for {target_device}",
            }
    else:
        return None
