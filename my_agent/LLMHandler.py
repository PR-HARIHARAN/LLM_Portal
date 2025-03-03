import json
import requests
from typing import Dict, Any, Optional, List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class LLMHandler:
    def __init__(self, model_name: str = "mistral-nemo:latest", api_url: str = "http://localhost:11434", 
                 temperature: float = 0.7, max_tokens: int = 512, timeout: int = 10):
        self.model_name = model_name
        self.api_url = api_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.session = requests.Session()
        self.llm = ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

    def analyze_intent(self, question: str) -> str:
        try:
            prompt = ChatPromptTemplate.from_template("""
            Analyze if this question relates to database queries or general chat.
            Return exactly "database" for questions about:
            - Retrieving table information
            - Counting records
            - Student performance
            - Grades
            - Filtering student data
            Return exactly "chat" for general conversation.

            Question: {question}
            """)
            
            response = (prompt | self.llm).invoke({"question": question})
            return str(response.content).strip().lower()
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return "chat"

    def get_query_from_llm(self, schema: str, question: str) -> str:
        try:
            template = """Given this MySQL database schema:

            {schema}

            Don't use the 

            Generate a safe, efficient SQL query to answer this question:
            {question}

            Return only the SQL query without any explanation or comments.
            """

            prompt = ChatPromptTemplate.from_template(template)
            response = (prompt | self.llm).invoke({"schema": schema, "question": question})
            return str(response.content).strip()
        except Exception as e:
            logger.error(f"Error generating query: {e}")
            return ""

    def correct_query(self, schema: str, question: str, original_query: str, error: str) -> str:
        try:
            template = """
            The following SQL query generated an error:
            
            Schema: {schema}
            Question: {question}
            Original Query: {original_query}
            Error: {error}
            
            Please provide a corrected SQL query that resolves this error.
            Return only the corrected SQL query without any explanation.
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            response = (prompt | self.llm).invoke({
                "schema": schema,
                "question": question,
                "original_query": original_query,
                "error": error
            })
            return str(response.content).strip()
        except Exception as e:
            logger.error(f"Error correcting query: {e}")
            return ""

    def validate_generated_sql(self, sql_query: str) -> Dict[str, Any]:
        try:
            template = """
            Analyze this SQL query for safety and correctness:
            
            {sql}
            
            Return a JSON object with this exact structure:
            {{
                "is_valid": boolean,
                "issues": [list of strings describing any problems],
                "risk_level": "low"|"medium"|"high"
            }}
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            response = (prompt | self.llm).invoke({"sql": sql_query})
            validation_result = json.loads(str(response.content).strip())
            return validation_result
        except Exception as e:
            logger.error(f"Error validating SQL: {e}")
            return {
                'is_valid': False,
                'issues': [str(e)],
                'risk_level': 'high'
            }

    def generate_chat_response(self, question: str) -> str:
        try:
            prompt = ChatPromptTemplate.from_template("""
            You are a helpful educational assistant. Respond professionally and engagingly to:
            
            {question}
            """)
            
            response = (prompt | self.llm).invoke({"question": question})
            return str(response.content).strip()
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return "I apologize, but I'm having trouble processing your request. Could you please try again?"

    def generate_summary(self, question: str, result: List[Dict[str, Any]]) -> str:
        try:
            template = """
            Create a clear, concise summary of these database results:
            
            Original Question: {question}
            Data: {data}
            
            Focus on key insights and patterns.
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            response = (prompt | self.llm).invoke({
                "question": question,
                "data": json.dumps(result, indent=2)
            })
            return str(response.content).strip()
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Unable to generate summary due to an error."
    
    def check_visualization_intent(self, question):
        """
        Check if the user's question would benefit from visualization.
        
        Parameters:
        -----------
        question : str
            The user's question or query
            
        Returns:
        --------
        bool
            True if visualization would be helpful, False otherwise
        """
        prompt = f"""
        Determine if the following user question would benefit from data visualization.
        Answer with 'yes' if visualization would add value, or 'no' if not.
        
        User question: "{question}"
        
        Consider visualization appropriate for:
        - Queries about trends over time
        - Requests to compare multiple values
        - Questions about distribution of data
        - Requests for patterns or correlations
        - Analysis of performance or metrics
        
        Answer (yes/no):
        """
        
        try:
            # Looking at your code, you likely use one of these methods to get responses
            # Using generate_chat_response as it seems to be the general response generator
            response = self.generate_chat_response(prompt)
            return response.lower().strip().startswith('yes')
        except Exception as e:
            # Default to not visualizing on error
            logger.warning(f"Error determining visualization intent: {str(e)}")
            return False