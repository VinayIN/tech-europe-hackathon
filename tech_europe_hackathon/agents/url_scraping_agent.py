"""
URL Scraping AI Agent with ACI.dev integration
"""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import json
from typing import Dict, Any
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool
from tech_europe_hackathon.utils.config import CONFIG
from aci import ACI


@tool
def search_tool(query: str) -> str:
    """Search the web using ACI.dev BRAVE_SEARCH"""
    aci = ACI(api_key=CONFIG.ACI_API_KEY)
    
    # Execute BRAVE_SEARCH__WEB_SEARCH
    result = aci.functions.execute(
        function_name="BRAVE_SEARCH__WEB_SEARCH",
        function_arguments={"query": {"q": query}},
        linked_account_owner_id=CONFIG.LINKED_ACCOUNT_OWNER_ID
    )
    
    if result.success:
        return json.dumps(result.data, indent=2)
    else:
        return f"Search error: {result.error}"


@tool
def scrape_url(url: str) -> str:
    """Scrape URL content using ACI.dev tools"""
    aci = ACI(api_key=CONFIG.ACI_API_KEY)
    
    # Use ACI.dev web scraping function with correct parameter structure
    result = aci.functions.execute(
        function_name="FIRECRAWL__EXTRACT",
        function_arguments={
            'body': {
                "urls": [url],
                "prompt": f"Extract the content from this URL and summarize it under {CONFIG.MAX_SCRAPING_WORDS + 500}.",
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                    "blockAds": True
                }
            }
        },
        linked_account_owner_id=CONFIG.LINKED_ACCOUNT_OWNER_ID
    )
    
    if result.success:
        return json.dumps(result.data, indent=2)
    else:
        return f"Scraping error: {result.error}"


class URLScrapingAgent:
    """URL Scraping Agent using only ACI.dev tools"""
    
    def __init__(self):
        # Use CrewAI's LLM wrapper instead of direct OpenAI client
        self.llm = LLM(
            model="openai/gpt-4o-mini",
            api_key=CONFIG.OPENAI_API_KEY
        )
        
        self.scraper = Agent(
            role='Web Content Scraper',
            goal='Extract and summarize web content efficiently',
            backstory='You are an expert at quickly extracting key information from web pages and creating concise summaries.',
            verbose=True,
            allow_delegation=False,
            tools=[scrape_url],  # Only use scrape_url, remove search_tool for faster processing
            llm=self.llm
        )
    
    def scrape_and_summarize(self, url: str, target_words: int = None) -> Dict[str, Any]:
        """Scrape URL and create a summary using ACI.dev tools"""
        if target_words is None:
            target_words = min(CONFIG.MAX_SCRAPING_WORDS, 150)
        
        # Create a more efficient scraping and summarization task
        scraping_task = Task(
            description=f"""
            Scrape and summarize content from: {url}
            
            Instructions:
            1. Use scrape_url tool to get content
            2. Create a concise {target_words}-word summary focusing on key points only
            3. If content is too long, focus on the introduction and main concepts
            4. Keep it factual and informative
            
            Return ONLY the summary text, no tool outputs or extra formatting.
            Maximum {target_words} words.
            """,
            agent=self.scraper,
            expected_output=f"Clean {target_words}-word summary text"
        )
        
        # Execute scraping and summarization with reduced verbosity
        crew = Crew(
            agents=[self.scraper],
            tasks=[scraping_task],
            share_crew=False,
            verbose=False  # Reduce verbosity for faster processing
        )
        
        summary = crew.kickoff()
        return {
            "url": url,
            "title": f"Content from {url.split('/')[2] if '/' in url else url}",
            "summary": str(summary).strip(),
            "success": True,
            "method": "aci_tools",
            "summary_word_count": len(str(summary).split())
        }
    
    def close(self):
        """Close resources properly"""
        if hasattr(self.llm, 'close'):
            self.llm.close()
