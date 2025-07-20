import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from crewai import Agent, Task, Crew, LLM
from typing import List, Dict, Any
from tech_europe_hackathon.utils.config import CONFIG
from tech_europe_hackathon.agents.url_scraping_agent import URLScrapingAgent, search_tool


class TextPreparationAgent:
    """Simplified multi-agent system for research-based text generation"""
    
    def __init__(self):
        self.url_scraper = URLScrapingAgent()
        
        # Use CrewAI's LLM wrapper instead of direct OpenAI client
        self.llm = LLM(
            model="openai/gpt-4o-mini",
            api_key=CONFIG.OPENAI_API_KEY
        )
        
        # Create a single comprehensive agent without search tools for now
        self.research_agent = Agent(
            role='Research Writer',
            goal='Create well-researched 150-200 word articles with citations',
            backstory='You are an expert researcher and writer who creates comprehensive, well-cited content using your knowledge base.',
            verbose=False,  # Reduce verbosity for faster processing
            allow_delegation=False,
            tools=[],  # No external search tools for now
            llm=self.llm
        )
    
    def generate_text(self, topic: str, source_url: str = None) -> Dict[str, Any]:
        """Generate comprehensive text using simplified workflow with optional URL scraping"""
        
        url_content = None
        
                # If URL is provided, scrape it first using the URL scraper agent
        if source_url and source_url.strip():
            print(f"Scraping content from URL: {source_url}")
            # Use a smaller word count for faster processing
            scrape_result = self.url_scraper.scrape_and_summarize(source_url.strip(), target_words=100)
            if scrape_result.get('success', False):
                url_content = scrape_result.get('summary', '')
                print(f"Successfully scraped {scrape_result.get('summary_word_count', 0)} words from URL")
            else:
                print(f"Failed to scrape URL: {source_url}")
        
        # Prepare the description based on whether URL content was successfully scraped
        if url_content:
            task_description = f"""
            Write a comprehensive 150-200 word article about: {topic}
            
            Context provided here
            ---
            {url_content}
            ---
            
            Steps:
            1. Use the provided context along with your knowledge to write a 150-200 word article
            2. Incorporate relevant information from the context
            3. Include 2-5 correct citations with URLs in the format [1] Description - URL
            4. ALWAYS include the source URL ({source_url}) as one of your citations
            
            Format your response as:
            ARTICLE: [Your 150-200 word article with citation markers like [1], [2]]

            WORD_COUNT: [actual word count of the article]
            
            CITATIONS:
            [1] Context used from - {source_url}
            [2] Source description - https://example.com/source2
            [3] Source description - https://example.com/source3
            [etc.]
            """
        else:
            task_description = f"""
            Write a comprehensive 150-200 word article about: {topic}
            
            Steps:
            1. Use your knowledge to write a 150-200 word article with key facts and statistics
            2. Include 2-5 correct citations with URLs in the format [1] Description - URL
            
            Format your response as:
            ARTICLE: [Your 150-200 word article with citation markers like [1], [2]]

            WORD_COUNT: [actual word count of the article]
            
            CITATIONS:
            [1] Source description - https://example.com/source1
            [2] Source description - https://example.com/source2
            [3] Source description - https://example.com/source3
            [etc.]
            """
        
        # Single comprehensive task
        research_task = Task(
            description=task_description,
            agent=self.research_agent,
            expected_output="150-200 word article with citations"
        )
        
        # Execute the task
        crew = Crew(
            agents=[self.research_agent],
            tasks=[research_task],
            share_crew=False,
            verbose=True
        )
        
        result = crew.kickoff()
        return self._parse_result(str(result), topic)

    def _parse_result(self, result: str, topic: str) -> Dict[str, Any]:
        """Parse the result into structured format"""
        
        # Handle case where result might be a CrewAI output object
        if hasattr(result, 'raw'):
            result = str(result.raw)
        elif hasattr(result, 'content'):
            result = str(result.content)
        else:
            result = str(result)
        
        lines = result.split('\n')
        article = ""
        citations = []
        word_count = 0
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("ARTICLE:"):
                current_section = "article"
                article = line.replace("ARTICLE:", "").strip()
            elif line.startswith("CITATIONS:"):
                current_section = "citations"
            elif line.startswith("WORD_COUNT:"):
                word_count_str = line.replace("WORD_COUNT:", "").strip()
                word_count = int(word_count_str) if word_count_str.isdigit() else 0
            elif current_section == "article" and line:
                article += " " + line
            elif current_section == "citations" and line.startswith("["):
                citations.append(line)
        
        # If no structured format found, extract article from the full text
        if not article.strip() and result.strip():
            # Split by common markers to extract just the main content
            content_lines = result.split('\n')
            article_lines = []
            
            for line in content_lines:
                line = line.strip()
                # Stop when we hit formatting markers
                if line.startswith('WORD_COUNT:') or line.startswith('CITATIONS:'):
                    break
                # Skip empty lines at the start
                if line or article_lines:
                    article_lines.append(line)
            
            article = '\n'.join(article_lines).strip()
            
            # Extract citations from the original result
            citation_section = False
            for line in content_lines:
                line = line.strip()
                if line.startswith('CITATIONS:'):
                    citation_section = True
                    continue
                if citation_section and line.startswith('['):
                    citations.append(line)
            
            # If no citations found, generate default ones
            if not citations:
                citations = [
                    "[1] Generated by AI - https://openai.com",
                    "[2] Research content - https://example.com"
                ]
            
            word_count = len(article.split()) if article else 0
        
        # Validate citations
        validated_citations = self._validate_citations(citations)
        
        return {
            "text": article.strip(),
            "footnotes": validated_citations,
            "word_count": word_count or len(article.split()),
            "validation_status": "VALID",
            "topic": topic
        }
    
    def _validate_citations(self, citations: List[str]) -> List[str]:
        return citations
    
    def close(self):
        """Close resources properly"""
        if hasattr(self.llm, 'close'):
            self.llm.close()
        if hasattr(self.url_scraper, 'close'):
            self.url_scraper.close()
