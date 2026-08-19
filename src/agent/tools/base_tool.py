from langchain_core.tools import tool

@tool(description="a tool for weather searching")
def search_weather(loaction : str) -> str :

    return "sunny"