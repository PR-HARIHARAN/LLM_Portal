import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from io import BytesIO
import os
import json
import base64
import logging
from my_agent.LLMHandler import LLMHandler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisualizationHandler:
    """Handles data visualization using LLM suggestions and Seaborn."""

    def __init__(self):
        """Initialize LLM handler."""
        try:
            self.llm_handler = LLMHandler()
        except Exception as e:
            logger.error(f"Failed to initialize LLM handler: {str(e)}")
            raise

    def is_visualizable(self, df):
        """
        Check if the dataframe is suitable for visualization.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Dataframe to check
            
        Returns:
        --------
        tuple
            (bool, str) - (is_visualizable, reason)
        """
        # Check if dataframe is empty
        if df.empty:
            return False, "Dataframe is empty"
            
        # Check if dataframe has at least one numeric column
        numeric_columns = df.select_dtypes(include=['number']).columns
        if len(numeric_columns) == 0:
            return False, "No numeric columns found for visualization"
            
        # Check if dataframe has sufficient rows
        if len(df) < 2:
            return False, "Not enough data points for visualization (minimum 2 required)"
            
        # Check if all values in numeric columns are the same (no variance)
        for col in numeric_columns:
            if df[col].nunique() <= 1:
                logger.warning(f"Column '{col}' has no variance")
                
        # If we have at least some numeric data with multiple rows, we can visualize
        return True, "Dataframe is suitable for visualization"

    def analyze_student_data(self, df, model_name="llama3"):
        """
        Analyzes a dataframe and returns appropriate visualizations.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Dataframe containing data to visualize
        model_name : str, optional
            LLM model to use for analysis, default is 'llama3'
            
        Returns:
        --------
        dict
            A dictionary containing visualization outputs and analysis
        """
        # First check if dataframe is visualizable
        is_visual, reason = self.is_visualizable(df)
        if not is_visual:
            return {"error": reason, "visualizable": False}
            
        # Get dataframe information
        df_info = {
            "columns": list(df.columns),
            "shape": df.shape,
            "dtypes": {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
            "sample": df.head(3).to_dict(orient='records'),
            "numeric_columns": list(df.select_dtypes(include=['number']).columns),
            "categorical_columns": list(df.select_dtypes(include=['object', 'category']).columns),
            "summary": df.describe().to_dict()
        }
        
        # Define visualization templates for common plot types
        templates = {
            "bar_chart": """
# Bar chart
plt.figure(figsize=(10, 6))
sns.barplot(x=df['{x_col}'], y=df['{y_col}'])
plt.xlabel('{x_col}')
plt.ylabel('{y_col}')
if len(df) > 10:
    plt.xticks(rotation=45)
plt.tight_layout()
""",
            "line_chart": """
# Line chart
plt.figure(figsize=(10, 6))
sns.lineplot(x=df['{x_col}'], y=df['{y_col}'])
plt.xlabel('{x_col}')
plt.ylabel('{y_col}')
if len(df) > 10:
    plt.xticks(rotation=45)
plt.tight_layout()
""",
            "scatter_plot": """
# Scatter plot
plt.figure(figsize=(10, 6))
sns.scatterplot(x=df['{x_col}'], y=df['{y_col}'])
plt.xlabel('{x_col}')
plt.ylabel('{y_col}')
plt.tight_layout()
""",
            "histogram": """
# Histogram
plt.figure(figsize=(10, 6))
sns.histplot(df['{x_col}'])
plt.xlabel('{x_col}')
plt.ylabel('Count')
plt.tight_layout()
""",
            "boxplot": """
# Box plot
plt.figure(figsize=(10, 6))
sns.boxplot(x=df['{x_col}'], y=df['{y_col}'])
plt.xlabel('{x_col}')
plt.ylabel('{y_col}')
if len(df) > 10:
    plt.xticks(rotation=45)
plt.tight_layout()
"""
        }
        
        # Create a prompt for visualization recommendation
        visualization_prompt = f"""
        You are an expert data visualization advisor. Based on the following dataframe information,
        recommend up to 3 appropriate visualization types that would provide valuable insights.
        
        Dataframe Information:
        - Columns: {df_info['columns']}
        - Shape: {df_info['shape']}
        - Numeric columns: {df_info['numeric_columns']}
        - Categorical columns: {df_info['categorical_columns']}
        - Sample data: {json.dumps(df_info['sample'][:2], indent=2)}
        
        IMPORTANT: DO NOT write actual visualization code. Instead, for each visualization, specify:
        1. The type (choose from: bar_chart, line_chart, scatter_plot, histogram, boxplot)
        2. Which column to use for x-axis
        3. Which column to use for y-axis (except for histogram)
        4. A title and description
        
        Respond in the following JSON format only:
        {{
            "visualizations": [
                {{
                    "type": "visualization_type",
                    "title": "Title for the visualization",
                    "x_axis": "column_name",
                    "y_axis": "column_name", 
                    "description": "What this visualization will show"
                }}
            ]
        }}
        """
        
        # Get visualization recommendations from LLM
        try:
            response = self.llm_handler.generate_chat_response(visualization_prompt)
            
            # Extract JSON from response (handles cases where LLM adds extra text)
            import re
            json_match = re.search(r'({.*})', response.replace('\n', ' '), re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                recommendations = json.loads(json_str)
            else:
                try:
                    recommendations = json.loads(response)
                except json.JSONDecodeError:
                    # Handle case where response isn't valid JSON
                    logger.error(f"Failed to parse LLM response as JSON: {response[:100]}...")
                    return {
                        "error": "Failed to generate valid visualization recommendations",
                        "visualizable": True
                    }
            
            # Generate visualizations
            results = {"analysis": recommendations, "visualizations": [], "visualizable": True}
            
            for viz in recommendations.get("visualizations", []):
                try:
                    viz_type = viz.get("type", "").lower()
                    x_col = viz.get("x_axis")
                    y_col = viz.get("y_axis")
                    title = viz.get("title", "Visualization")
                    
                    # Skip if required fields are missing
                    if not viz_type or not x_col:
                        logger.warning(f"Skipping visualization due to missing parameters: {viz}")
                        continue
                        
                    # Check if columns exist in dataframe
                    if x_col not in df.columns:
                        logger.warning(f"Column '{x_col}' not found in dataframe")
                        continue
                        
                    if y_col and y_col not in df.columns:
                        logger.warning(f"Column '{y_col}' not found in dataframe")
                        continue
                    
                    # Apply template based on visualization type
                    if viz_type in templates:
                        if viz_type == "histogram":
                            code = templates[viz_type].format(x_col=x_col)
                        else:
                            if not y_col:
                                logger.warning(f"Y-axis required for {viz_type}")
                                continue
                            code = templates[viz_type].format(x_col=x_col, y_col=y_col)
                    else:
                        logger.warning(f"Unsupported visualization type: {viz_type}")
                        continue
                    
                    # Execute the visualization code with proper context
                    plt.figure(figsize=(10, 6))
                    local_vars = {"df": df, "plt": plt, "sns": sns}
                    exec(code, globals(), local_vars)
                    
                    # Add title
                    plt.title(title)
                    
                    # Capture the plot
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png')
                    buffer.seek(0)
                    
                    # Convert to base64 for embedding
                    img_str = base64.b64encode(buffer.read()).decode('utf-8')
                    results["visualizations"].append({
                        "title": title,
                        "description": viz.get("description", ""),
                        "image": img_str,
                        "type": viz_type
                    })
                    
                    plt.close()
                except Exception as e:
                    logger.error(f"Error generating visualization: {str(e)}")
                    plt.close()
            
            return results
        
        except Exception as e:
            logger.error(f"Error in visualization analysis: {str(e)}")
            return {"error": str(e), "visualizable": is_visual}

    def save_visualizations(self, results, output_dir="visualizations"):
        """
        Save generated visualizations to files.
        
        Parameters:
        -----------
        results : dict
            Dictionary containing visualization results
        output_dir : str, optional
            Directory to save visualizations, default is 'visualizations'
            
        Returns:
        --------
        list
            List of saved file paths
        """
        if "error" in results or not results.get("visualizable", False):
            logger.error(f"Cannot save visualizations: {results.get('error', 'Unknown error')}")
            return []
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = []
        for i, viz in enumerate(results["visualizations"]):
            if "error" in viz:
                continue
                
            # Create safe filename from title
            safe_title = "".join([c if c.isalnum() else "_" for c in viz["title"]])
            filename = f"{i+1}_{safe_title}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Decode and save image
            try:
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(viz["image"]))
                saved_files.append(filepath)
                logger.info(f"Saved visualization to {filepath}")
            except Exception as e:
                logger.error(f"Error saving visualization: {str(e)}")
                
        return saved_files