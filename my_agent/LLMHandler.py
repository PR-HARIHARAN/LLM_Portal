import json
import requests
from typing import Dict, Any, Optional, List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import pandas as pd
import logging
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def clean_llm_sql(raw_sql: str) -> str:
    raw_sql = raw_sql.lower()
    if not raw_sql:
        return ""
    cleaned = raw_sql.strip()
    if cleaned.startswith("```sql"):
        cleaned = cleaned[6:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()
    elif cleaned.startswith("sql"):
        cleaned = cleaned[3:].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    return cleaned.replace("`", "").strip()

class LLMHandler:
    def __init__(self, 
                 model_name: Optional[str] = None,
                 api_url: Optional[str] = None, 
                 temperature: float = 0.7, 
                 max_tokens: int = 512, 
                 timeout: int = 10):
        
        # Load from env if not explicitly passed
        self.model_name = model_name or os.getenv("MODEL_NAME")
        self.api_url = api_url or os.getenv("GROQ_API_KEY")

        if not self.model_name or not self.api_url:
            raise ValueError("Model name or GROQ API key is not set")

        # Set required env variable for LangChain Groq wrapper
        os.environ["GROQ_API_KEY"] = self.api_url
        
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.session = requests.Session()

        self.llm = ChatGroq(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

    def analyze_intent(self, question: str) -> str:
        try:
            prompt = ChatPromptTemplate.from_template("""
            You are a helpful assistant. Determine the intent of the following user question.
                - SQL: Structured banking data (e.g., customers, transactions, loans, account types, cities) top k or bottom k values.
                - CHAT: Casual greetings only, don't try to answer any other thing look fo vector or sql can be capable or not.

            Briefly identify the intent. Respond with one word: SQL, CHAT

            Question: {question}
            """)
            
            response = (prompt | self.llm).invoke({"question": question})
            return str(response.content).strip().upper()
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return "CHAT"

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
            result =str(response.content).strip()
            return clean_llm_sql(result)
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