"""
Text Modification Agent with CAG (Context-Aware Generation) Architecture
"""
from crewai import Agent, Task, Crew, LLM
from typing import List, Dict, Any, Tuple
from tech_europe_hackathon.utils.config import CONFIG


class TextModificationAgent:
    """
    Context-Aware Generation (CAG) Agent for text modification
    Modifies sub-text within a larger source text while maintaining word count (±20%)
    """
    
    def __init__(self):
        # Use CrewAI's LLM wrapper instead of direct OpenAI client
        self.llm = LLM(
            model="openai/gpt-4o-mini",
            api_key=CONFIG.OPENAI_API_KEY
        )
        
        # Context Analyzer Agent
        self.context_analyzer = Agent(
            role='Context Analyzer',
            goal='Analyze the full source text and identify the sub-text to be modified with its surrounding context',
            backstory='You are an expert text analyst who understands context and can precisely locate and analyze text segments within larger documents.',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Text Modifier Agent
        self.text_modifier = Agent(
            role='Context-Aware Text Modifier',
            goal='Modify the identified sub-text while maintaining context coherence and word count (±20%)',
            backstory='You are an expert editor who can modify text segments while preserving the overall document flow and maintaining appropriate word count.',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def modify_text(self, source_text: str, sub_text_query: str, modification_prompt: str, word_count_tolerance: float = 0.2) -> str:
        """
        Modify sub-text within source text using CAG architecture
        
        Args:
            source_text: The full source document text
            sub_text_query: Query to identify the sub-text to modify
            modification_prompt: Instructions for modification
            word_count_tolerance: Allowed word count variation (default 20%)
        
        Returns:
            Only the modified sub-text (not the full integrated document)
        """
        
        # Step 1: Context Analysis Task
        context_analysis_task = Task(
            description=f"""
            Analyze the source text and identify the sub-text to be modified:
            
            SOURCE TEXT:
            {source_text}
            
            SUB-TEXT QUERY: {sub_text_query}
            
            Tasks:
            1. Locate the exact sub-text that matches the query
            2. Identify the surrounding context (2-3 sentences before and after)
            3. Count the words in the identified sub-text
            4. Analyze the tone, style, and purpose of the sub-text
            
            Format your response as:
            IDENTIFIED_SUB_TEXT: [exact text found]
            PRECEDING_CONTEXT: [2-3 sentences before]
            FOLLOWING_CONTEXT: [2-3 sentences after]
            TONE_STYLE: [analysis of tone and style]
            POSITION: [approximate position in source text]
            """,
            agent=self.context_analyzer,
            expected_output="Analysis of sub-text location, context, and characteristics"
        )
        
        # Step 2: Text Modification Task
        modification_task = Task(
            description=f"""
            Based on the context analysis, modify the identified sub-text according to the user's prompt:
            
            MODIFICATION PROMPT: {modification_prompt}
            WORD_COUNT_TOLERANCE: ±{int(word_count_tolerance * 100)}%
            
            Requirements:
            1. Modify ONLY the identified sub-text, not the surrounding context
            2. Maintain the original word count within ±{int(word_count_tolerance * 100)}% tolerance
            3. Preserve the tone and style identified in the analysis
            4. Ensure the modification flows naturally with the surrounding context
            5. Apply the user's modification instructions precisely
            
            Format your response as only the modified text without any labels or formatting.
            """,
            agent=self.text_modifier,
            expected_output="Only the modified sub-text"
        )
        
        # Execute CAG workflow - only need context analysis and modification
        crew = Crew(
            agents=[self.context_analyzer, self.text_modifier],
            tasks=[context_analysis_task, modification_task],
            share_crew=False,
            verbose=True
        )
        
        result = crew.kickoff()
        return str(result).strip()
    
    def close(self):
        """Close resources properly"""
        if hasattr(self.llm, 'close'):
            self.llm.close()
