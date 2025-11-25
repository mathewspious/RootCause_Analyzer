from typing import Optional


def say_hello(name: Optional[str] = None) -> str:
    """
    Provide a simple greeting. If a name is provided it will be used

    Args:
        name (str, optional): The name of the person to greet. Defaults to a generic greeting

    Returns:
        str: A friendly greeting message.
    """

    if name:
        greeting = f"Hello {name}"
        print(f"Tool: say_hello called with name: {name}")
    else:
        greeting = "Hello there!"
        print(f"Tool: say_hello called without a specific name")

    return greeting
