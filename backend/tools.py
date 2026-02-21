import os


def search(query: str) -> str:
    """
    Search for information about a topic.
    Priority: Tavily (if API key set) -> DuckDuckGo -> Mock data fallback.
    """
    tavily_key = os.getenv("TAVILY_API_KEY")

    # 1. Try Tavily first
    if tavily_key:
        try:
            from langchain_tavily import TavilySearch

            tool = TavilySearch(max_results=5)
            results = tool.invoke(query)
            if isinstance(results, list):
                formatted = "\n\n".join(
                    [
                        f"Source: {r.get('url', 'N/A')}\n{r.get('content', '')}"
                        for r in results
                    ]
                )
                return formatted
            return str(results)
        except Exception as e:
            print(f"[Tools] Tavily search failed: {e}")

    # 2. Try DuckDuckGo
    try:
        from langchain_community.tools import DuckDuckGoSearchRun

        tool = DuckDuckGoSearchRun()
        return tool.invoke(query)
    except Exception as e:
        print(f"[Tools] DuckDuckGo search failed: {e}")

    # 3. Mock data fallback — prevents crashing when no tool is available
    print(f"[Tools] Using mock data for: {query}")
    return f"""Mock research data for '{query}':

Key Facts:
- {query} is a significant topic with wide-ranging implications across multiple industries.
- Experts have identified it as one of the most discussed subjects in recent years.
- Historical context traces its roots back several decades with modern acceleration.

Statistics:
- Global market size: estimated $50–100 billion (growing at ~15% CAGR).
- Adoption rate: 40% year-over-year increase across major sectors.
- Investment in this area reached record highs in the past two years.

Current Trends:
1. Digital transformation is accelerating the pace of change.
2. Sustainability and ethical considerations are reshaping strategies.
3. AI and automation are creating new opportunities and challenges.
4. Regulatory frameworks are evolving to keep pace with innovation.

Key Stakeholders:
- Businesses and startups driving innovation.
- Government bodies setting policy and regulation.
- Consumers whose behaviors are shifting rapidly.
- Researchers and academics providing evidence-based insights.

Potential Content Angles:
- Historical evolution and where we are today.
- Benefits and challenges for different stakeholders.
- Future outlook and predictions for the next 5–10 years.
- Practical takeaways for everyday readers.

NOTE: This is mock/placeholder data. To get real search results, set
TAVILY_API_KEY in your .env file, or ensure duckduckgo-search is installed."""
