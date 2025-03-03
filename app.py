import chainlit as cl
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import pandas as pd
from my_agent.DatabaseManager import DatabaseManager
from my_agent.LLMHandler import LLMHandler
from my_agent.VisualizationHandler import VisualizationHandler
import base64
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    columns: List[str]
    data: List[Tuple]
    error: Optional[str] = None
    summary: Optional[str] = None

class DatabaseQueryHandler:
    def __init__(self):
        try:
            self.db_manager = DatabaseManager()
            self.llm_handler = LLMHandler()
            self.visualization_handler = VisualizationHandler()
        except Exception as e:
            logger.error(f"Failed to initialize handlers: {str(e)}")
            raise

    async def fetch_schema(self) -> Optional[Dict]:
        try:
            schema = self.db_manager.get_database_schema()
            if not schema:
                raise ValueError("Empty schema returned")
            return schema
        except Exception as e:
            logger.error(f"Error fetching schema: {str(e)}")
            return None

    async def execute_and_validate_query(self, sql_query: str, schema: str, question: str) -> QueryResult:
        try:
            # First try to execute the query
            try:
                columns, data = self.db_manager.execute_read_query(sql_query)
                return QueryResult(columns=columns, data=data)
            except Exception as exec_error:
                # If execution fails, try to correct the query
                logger.info(f"Query execution failed: {exec_error}")
                corrected_query = self.llm_handler.correct_query(
                    schema, question, sql_query, str(exec_error)
                )
                
                if not corrected_query:
                    return QueryResult(
                        columns=[],
                        data=[],
                        error=f"Failed to execute query: {str(exec_error)}"
                    )

                # Try executing the corrected query
                try:
                    columns, data = self.db_manager.execute_read_query(corrected_query)
                    return QueryResult(columns=columns, data=data)
                except Exception as corr_error:
                    # If corrected query also fails, then validate
                    validation = self.llm_handler.validate_generated_sql(corrected_query)
                    return QueryResult(
                        columns=[],
                        data=[],
                        error=f"Query validation issues: {', '.join(validation['issues'])}"
                    )

        except Exception as e:
            logger.error(f"Query handling error: {e}")
            return QueryResult(columns=[], data=[], error=str(e))

    async def format_results(self, results: QueryResult, question: str):
        if results.error:
            await cl.Message(content=f"❌ Error: {results.error}").send()
            return

        try:
            df = pd.DataFrame(results.data, columns=results.columns)
            elements = [cl.Dataframe(data=df, display="inline", name="Query Results")]
            
            # Generate visualizations if appropriate
            vis_elements = await self.generate_visualizations(df, question)
            if vis_elements:
                elements.extend(vis_elements)
                
            await cl.Message(content="📊 Results:", elements=elements).send()

            if len(results.data) > 0:
                summary = self.llm_handler.generate_summary(
                    question,
                    [dict(zip(results.columns, row)) for row in results.data]
                )
                await cl.Message(content=f"📝 Summary:\n{summary}").send()

        except Exception as e:
            logger.error(f"Error formatting results: {str(e)}")
            await cl.Message(content="Error formatting data.").send()
            
    async def generate_visualizations(self, df, question):
        """Generate visualizations based on the query results dataframe"""
        try:
            # Check if visualization is appropriate for this query/data
            visualization_intent = self.llm_handler.check_visualization_intent(question)
            
            if not visualization_intent:
                logger.info("Query does not appear to need visualization")
                return []
                
            # Check if dataframe is visualizable
            is_visual, reason = self.visualization_handler.is_visualizable(df)
            if not is_visual:
                logger.info(f"Data not suitable for visualization: {reason}")
                return []
                
            # Generate visualizations
            logger.info("Generating visualizations for query results")
            vis_results = self.visualization_handler.analyze_student_data(df)
            
            if "error" in vis_results or not vis_results.get("visualizable", False):
                logger.warning(f"Visualization generation failed: {vis_results.get('error', 'Unknown error')}")
                return []
                
            # Save temp files and create elements for display
            elements = []
            temp_dir = os.path.join(os.getcwd(), "temp_vis")
            os.makedirs(temp_dir, exist_ok=True)
            
            for i, viz in enumerate(vis_results["visualizations"]):
                if "error" in viz:
                    continue
                
                # Create image element
                img_data = viz["image"]
                elements.append(
                    cl.Image(
                        name=f"visualization_{i+1}",
                        display="inline",
                        content=base64.b64decode(img_data),
                        mime="image/png"
                    )
                )
                
                # Add text card with description
                elements.append(
                    cl.Text(
                        name=f"viz_description_{i+1}",
                        content=f"**{viz['title']}**: {viz['description']}"
                    )
                )
                
            return elements
                
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            return []

query_handler = DatabaseQueryHandler()

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="👋 Welcome! How can I help you?").send()

@cl.on_message
async def on_message(message: cl.Message):
    try:
        async with cl.Step("Processing...") as step:
            intent = query_handler.llm_handler.analyze_intent(message.content)
            
            if intent == "chat":
                chat_response = query_handler.llm_handler.generate_chat_response(message.content)
                await cl.Message(content=chat_response).send()
                return

            schema = await query_handler.fetch_schema()
            if not schema:
                await cl.Message(content="❌ Database access error. Please try again.").send()
                return

            sql_query = query_handler.llm_handler.get_query_from_llm(schema, message.content)
            if not sql_query:
                await cl.Message(content="❌ Could not generate query. Please rephrase.").send()
                return

            await cl.Message(content=f"🔍 Generated SQL:\n```sql\n{sql_query}\n```").send()

            results = await query_handler.execute_and_validate_query(
                sql_query, schema, message.content
            )
            await query_handler.format_results(results=results, question=message.content)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await cl.Message(content="❌ An error occurred. Please try again.").send()

if __name__ == "__main__":
    cl.run()