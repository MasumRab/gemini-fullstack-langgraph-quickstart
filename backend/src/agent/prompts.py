from datetime import datetime


# Get current date in a readable format
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


plan_writer_instructions = """Your goal is to generate a comprehensive research plan consisting of a series of tasks (Todos). These tasks are intended for an advanced automated web research tool capable of executing them.

Instructions:
- Analyze the user's request and break it down into logical research steps.
- Each task should focus on one specific aspect of the original question.
- Don't produce more than {number_queries} tasks.
- Tasks should be diverse covering different angles.
- Ensure tasks targets the most current information. The current date is {current_date}.

Format: 
- Format your response as a JSON object with ALL two of these exact keys:
   - "rationale": Brief explanation of the research strategy.
   - "plan": A list of tasks. Each task must be an object with:
        - "title": A concise title for the task (acting as the search query).
        - "description": A brief description of what to look for.
        - "status": Set to "pending".

Example:

Topic: Compare Apple's revenue growth vs iPhone sales growth last year.
```json
{{
    "rationale": "To answer this comparative growth question accurately, we need specific data points on Apple's stock performance and iPhone sales metrics.",
    "plan": [
        {{
            "title": "Apple total revenue growth fiscal year 2024",
            "description": "Find official financial reports stating total revenue growth.",
            "status": "pending"
        }},
        {{
            "title": "iPhone unit sales growth fiscal year 2024",
            "description": "Find sales figures for iPhones in FY2024.",
            "status": "pending"
        }},
        {{
            "title": "Apple stock price growth fiscal year 2024",
            "description": "Find stock performance data for AAPL in 2024.",
            "status": "pending"
        }}
    ]
}}
```

Context: {research_topic}"""


web_searcher_instructions = """Conduct targeted Google Searches to gather the most recent, credible information on "{research_topic}" and synthesize it into a verifiable text artifact.

Instructions:
- Query should ensure that the most current information is gathered. The current date is {current_date}.
- Conduct multiple, diverse searches to gather comprehensive information.
- Consolidate key findings while meticulously tracking the source(s) for each specific piece of information.
- The output should be a well-written summary or report based on your search findings. 
- Only include the information found in the search results, don't make up any information.

Research Topic:
{research_topic}
"""

reflection_instructions = """You are an expert research assistant analyzing summaries about "{research_topic}".

Instructions:
- Identify knowledge gaps or areas that need deeper exploration and generate a follow-up query. (1 or multiple).
- If provided summaries are sufficient to answer the user's question, don't generate a follow-up query.
- If there is a knowledge gap, generate a follow-up query that would help expand your understanding.
- Focus on technical details, implementation specifics, or emerging trends that weren't fully covered.

Requirements:
- Ensure the follow-up query is self-contained and includes necessary context for web search.

Output Format:
- Format your response as a JSON object with these exact keys:
   - "is_sufficient": true or false
   - "knowledge_gap": Describe what information is missing or needs clarification
   - "follow_up_queries": Write a specific question to address this gap

Example:
```json
{{
    "is_sufficient": true, // or false
    "knowledge_gap": "The summary lacks information about performance metrics and benchmarks", // "" if is_sufficient is true
    "follow_up_queries": ["What are typical performance benchmarks and metrics used to evaluate [specific technology]?"] // [] if is_sufficient is true
}}
```

Reflect carefully on the Summaries to identify knowledge gaps and produce a follow-up query. Then, produce your output following this JSON format:

Summaries:
{summaries}
"""

answer_instructions = """Generate a high-quality answer to the user's question based on the provided summaries.

Instructions:
- The current date is {current_date}.
- You are the final step of a multi-step research process, don't mention that you are the final step. 
- You have access to all the information gathered from the previous steps.
- You have access to the user's question.
- Generate a high-quality answer to the user's question based on the provided summaries and the user's question.
- Include the sources you used from the Summaries in the answer correctly, use markdown format (e.g. [apnews](https://vertexaisearch.cloud.google.com/id/1-0)). THIS IS A MUST.

User Context:
- {research_topic}

Summaries:
{summaries}"""

summarize_webpage_prompt = """You are an expert research assistant tasked with summarizing webpage content.

Instructions:
- Today's date is {date}.
- Extract the most important and relevant information from the webpage.
- Focus on facts, data, and key insights.
- Ignore navigation, ads, and irrelevant content.
- Preserve important quotes or statistics with their sources.

Webpage Content:
{webpage_content}

Provide a structured summary with:
1. A concise summary of the main points (2-3 paragraphs)
2. Key excerpts or quotes that are particularly important

Format your response clearly with sections for summary and key excerpts."""


report_generation_with_draft_insight_prompt = """You are an expert research report writer.

Today's date is {date}.

## Research Brief
{research_brief}

## Research Findings
{findings}

## Current Draft Report
{draft_report}

## Instructions
Refine and improve this research report by:
1. Ensuring all key findings are accurately incorporated
2. Improving clarity, structure, and flow
3. Adding proper citations from the findings
4. Fixing any factual inconsistencies
5. Making the report more comprehensive and professional
6. Ensuring the report directly addresses the research brief

Provide the refined report:"""
