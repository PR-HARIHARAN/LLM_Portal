# AI-Powered Student Performance Dashboard

## 📚 **Overview**
The AI-Powered Student Performance Dashboard is a web-based platform designed to simplify the process of analyzing student performance. It provides students with visualizations of their scores and enables staff to extract data effortlessly using natural language queries powered by a Large Language Model (LLM). This system integrates with the LMS Portal, where students engage in competitive programming and practice, storing their progress data for analysis.

---
## 📹 Video Demo

[![Demo](https://img.youtube.com/vi/cT2jXRFSZG4/maxresdefault.jpg)](https://youtu.be/cT2jXRFSZG4)

---

## 🛠️ **Features**
- **Interactive Visualizations**: Students can visualize their scores and performance trends.  
- **Natural Language to SQL Queries**: Staff and admins can query the database using plain English prompts.  
- **Streamlined Data Extraction**: Eliminates the need for manual spreadsheet preparation.  
- **Integration with LMS Portal**: Pulls data from student activities in competitive programming.  
- **Scalable Design**: Built for adaptability with plans to integrate Agentic AI for advanced visualizations.  

---

## 🎯 **Objectives**
- Simplify student performance analysis for staff and students.  
- Provide actionable insights through intuitive dashboards.  
- Enable seamless data retrieval using AI-powered natural language interfaces.  

---

## 🧑‍💻 **Tech Stack**
- **Backend**: Python,  
- **AI Integration**: LangChain, Ollama-Llama 3.2  
- **Database**: MySQL  
- **Frontend**: Chainlit
- **Future Enhancements**: ?

---

## 🚀 **Project Workflow**
1. **Data Collection**: Students' activity data is gathered from the LMS Portal.  
2. **Data Storage**: Information is stored in a MySQL database.  
3. **Natural Language Query Processing**: LangChain and Ollama-Llama 3.2 handle queries in natural language, converting them to SQL commands.  
4. **Visualization**: The dashboard presents performance insights to students and staff.  

---

## 🔄 **Setup Instructions**
Follow these steps to set up the project locally:

1. **Clone the Repository**:  
   ```bash
   git clone https://github.com/PR-HARIHARAN/LLM_Portal

2. **Install Dependencies**:  
   ```bash
   pip install -r requirements.txt
   
3. **Install ollama**:
   ```bash
   ollama pull llama3.2

4. **Run Application**:
   ```bash
   python app.py
   
---

## 📈 **Future Enhancements**
1. **Agentic AI Integration**: Introduce intelligent agents for better adaptability and automation.  
3. **Enhanced Visualizations**: Provide detailed and customizable performance insights.  
4. **Feedback Incorporation:**: Use real-time feedback to improve query accuracy and dashboard design.  

---
