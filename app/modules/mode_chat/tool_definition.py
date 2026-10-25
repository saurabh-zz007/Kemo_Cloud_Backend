WEB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web for real-time information, documentation, package names (winget), news, or accurate facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_extract",
            "description": "Extract clean, raw text content from a specific URL. Use this when you already have a link and need to read the full page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The specific URL to extract content from."
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional. A query to focus the extraction on specific information, returning relevant chunks instead of the full page."
                    },
                    "extract_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "description": "Optional. 'basic' is faster, 'advanced' bypasses more complex site protections. Defaults to 'basic'."
                    },
                    "chunks": {
                        "type": "integer",
                        "description": "Optional. The maximum number of relevant snippets to return per source. Only used if 'query' is provided. Defaults to 3."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_crawl",
            "description": "Crawl a website starting from a specific URL to discover and extract information across multiple pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The root URL to begin the crawl."
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Optional. Natural language instructions to guide the crawler (e.g., 'Find all pricing pages'). Required if using chunks_per_source."
                    },
                    "chunks_per_source": {
                        "type": "integer",
                        "description": "Optional. Max snippets to extract per page. Requires 'instructions' to be set. Defaults to 3."
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Optional. How many levels deep to click from the starting URL. Defaults to 1."
                    },
                    "max_breadth": {
                        "type": "integer",
                        "description": "Optional. Maximum links to follow per page level. Defaults to 10."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional. The hard limit on total pages to crawl and process. Defaults to 1."
                    }
                },
                "required": ["url"]
            }
        }
    }       
]

MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
        "name": "add_memory",
        "description": "Save important new facts, user preferences, or project details to long-term memory. Use this when the user shares information that should be remembered for future conversations.",
        "parameters": {
            "type": "object",
            "properties": {
                "fact_data": {
                    "type": "array",
                    "items": {
                    "type": "string"
                    },
                    "description": "A list of clean, standalone factual statements to save. E.g., ['User prefers C++ for backends.', 'User is building a desktop app.']"
                }
            },
            "required": ["fact_data"]
        }
        }
    },
    {
        "type": "function",
        "function": {
        "name": "search_memory",
        "description": "Search long-term memory for past context, user preferences, or specific past conversations using semantic search.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "The search query to find relevant memories. E.g., 'What framework are we using?'"
                },
                "limit": {
                    "type": "integer",
                    "description": "The maximum number of results to return. Allowed values: 1 to 20. If you do not pass this parameter, it will automatically default to 5.",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5
                },
                "score_threshold": {
                    "type": "number",
                    "description": "The minimum similarity score a memory must have to be included. Allowed values: 0.0 to 1.0. If you do not pass this parameter, it will automatically default to 0.5.",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5
                }
            },
            "required": ["query_text"]
        }
        }
    },
    {
        "type": "function",
        "function": {
        "name": "update_memory",
        "description": "Update an existing memory with new information. Use this when the user changes their mind or a previously saved fact becomes outdated.",
        "parameters": {
            "type": "object",
            "properties": {
                "point_id": {
                    "type": "string",
                    "description": "The exact UUID of the memory to update, retrieved from a previous search_memory call."
                },
                "update_fact_data": {
                    "type": "string",
                    "description": "The completely new fact text that will replace the old memory."
                }
            },
            "required": ["point_id", "update_fact_data"]
        }
        }
    },
    {
        "type": "function",
        "function": {
        "name": "delete_memory",
        "description": "Permanently delete a memory that is incorrect, hallucinated, or no longer relevant.",
        "parameters": {
            "type": "object",
            "properties": {
                "point_id": {
                    "type": "string",
                    "description": "The exact UUID of the memory to delete, retrieved from a previous search_memory call."
                }
            },
            "required": ["point_id"]
        }
        }
    }
]