# Flight Tracking System - Automated Task Management

A sophisticated Python-based automation tool that revolutionizes the software development workflow by intelligently decomposing high-level requirements into actionable tasks, creating structured Jira tickets, and generating comprehensive test cases using Google's Gemini AI.

## Overview

This system addresses the common challenge of breaking down complex software development tasks into manageable components. It leverages the power of Google's Gemini AI to analyze requirements, generate appropriate subtasks, and create corresponding Jira tickets automatically. Additionally, it produces detailed test cases for each subtask, streamlining the entire development process from initial requirement to testing phase.

## Key Features

- **Intelligent Task Decomposition**: Analyzes high-level requirements and automatically decomposes them into 3-5 distinct, non-overlapping subtasks
- **Comprehensive Jira Integration**: Creates parent tasks, subtasks, and establishes appropriate linking relationships
- **Automated Test Case Generation**: Produces 3-5 detailed test cases for each subtask with steps and expected outcomes
- **Resilient API Handling**: Implements key rotation and fallback mechanisms to manage rate limitations
- **Rich Metadata Inclusion**: Categorizes tasks (Backend, Frontend, API, etc.) and suggests component names
- **Robust Error Handling**: Gracefully handles API failures and provides meaningful error messages.
- **Proper Task Relationships**: Establishes and verifies parent-child relationships between tickets.

## How It Works

1. **Input Collection**: The user enters a high-level task requirement (e.g., "Implement user authentication system")
2. **Parent Ticket Creation**: The system creates a parent Jira ticket for the main requirement
3. **AI Analysis**: Gemini API analyzes the requirement to identify logical subtasks
4. **Subtask Generation**: 3-5 distinct subtasks are generated, each with:
   - A clear title
   - Comprehensive description
   - Category assignment (Backend, Frontend, etc.)
   - Component suggestion
5. **Jira Ticket Creation**: Creates properly formatted Jira tickets for each subtask
6. **Ticket Linking**: Establishes appropriate relationships between parent and subtasks
7. **Test Case Generation**: For each subtask:
   - Generates 3-5 comprehensive test cases
   - Includes test steps, expected results, and priority levels
   - Creates test cases as linked subtasks in Jira
8. **Verification**: Displays all created tickets to confirm successful creation

## Code Architecture

The system is structured into several functional modules:

### Configuration Section
```python
# Jira Credentials & Constants
EMAIL = "example@domain.com"
API_TOKEN = "your-api-token"
JIRA_BASE_URL = "https://your-domain.atlassian.net"
PROJECT_KEY = "PRJ"

# Gemini API Configuration
gemini_keys = ['key1', 'key2', 'key3', 'key4', 'key5']
```

### Gemini API Functions
- `get_gemini_instance()`: Initializes the Gemini API with the current key
- `generate_content_with_fallback(prompt)`: Sends prompts to Gemini API with intelligent key rotation and error handling

### Jira API Functions
- `create_jira_ticket(summary, description)`: Creates a new Jira task
- `create_jira_subtask(parent_key, summary, description)`: Creates a subtask linked to a parent
- `fetch_visible_tickets()`: Retrieves and displays all tickets in the project

### Task Generation Functions
- `generate_development_tasks(requirement)`: Uses Gemini to analyze requirements and generate structured subtasks

### Jira Linking Functions
- `get_link_types()`: Retrieves available issue link types from Jira
- `link_issues(outward_issue, inward_issue, link_type)`: Creates relationships between issues
- `create_linked_subtasks(parent_key, subtasks)`: Creates and links subtasks to parent

### Test Case Generation
- `generate_and_create_test_cases(task_description, task_key)`: Generates test cases for a task and creates them as subtasks

## Example Output

### Example Requirement
```
Implement a flight tracking system with real-time updates and user notifications
```

### Generated Subtasks
```json
[
  {
    "summary": "Develop backend service for flight data acquisition and processing. Implement APIs to fetch real-time flight data from external sources, process and store this data in a structured format, and provide endpoints for querying flight information.",
    "category": "Backend",
    "component": "DataProcessingService",
    "title": "Backend Flight Data Processing Service"
  },
  {
    "summary": "Create frontend dashboard for flight visualization. Implement interactive map display showing flight paths, airport information, and flight status with color-coded indicators for delays, on-time, and canceled flights.",
    "category": "Frontend",
    "component": "FlightDashboard",
    "title": "Flight Tracking Dashboard UI"
  },
  {
    "summary": "Implement notification system for flight status updates. Develop service to monitor flight status changes and send real-time notifications via email, SMS, and push notifications based on user preferences.",
    "category": "Backend",
    "component": "NotificationService",
    "title": "Flight Status Notification System"
  },
  {
    "summary": "Create RESTful API for third-party integrations. Design and implement comprehensive API endpoints allowing external systems to access flight data, status updates, and subscribe to notifications.",
    "category": "API",
    "component": "ExternalAPI",
    "title": "Flight Data API for External Systems"
  }
]
```

### Generated Test Case Example
```json
{
  "test_id": "TC-1",
  "test_name": "Verify Real-time Flight Status Updates",
  "description": "Test that the system correctly updates flight status in real-time when external data sources report changes",
  "steps": [
    "Configure system to monitor test flight XYZ123",
    "Simulate status change from 'On Time' to 'Delayed'",
    "Verify dashboard reflects new status within 30 seconds",
    "Check system logs for processing of status change"
  ],
  "expected_result": "Flight status should update to 'Delayed' within 30 seconds of the change being reported by external sources",
  "priority": "High"
}
```

## Technical Implementation

### Prompt Engineering
The system uses carefully crafted prompts to get high-quality results from the Gemini API:

```python
prompt = f"""Analyze the following software development task and generate EXACTLY 3 to 5 high-level, non-overlapping subtasks:
Task: {requirement}

Instructions:
1. Generate EXACTLY 3 to 5 distinct subtasks - no more, no less.
2. Each subtask should represent a major component or phase of development.
...
```

### API Resilience
The system implements a sophisticated key rotation and fallback mechanism:

```python
def generate_content_with_fallback(prompt):
    global current_gemini_index
    initial_index = current_gemini_index  # Remember starting key index
    attempts = 0

    while attempts < len(gemini_keys):
        try:
            model = get_gemini_instance()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini key {gemini_keys[current_gemini_index]} failed: {e}")
            if '429' in str(e) or 'quota' in str(e):
                time.sleep(1)  # Wait 1 second on rate limit errors
            current_gemini_index = (current_gemini_index + 1) % len(gemini_keys)
            attempts += 1
            if current_gemini_index == initial_index:
                time.sleep(2)  # Additional delay if we've cycled through all keys

    raise Exception("All Gemini API keys failed after multiple attempts")
```

### Jira Integration
The system utilizes Jira's REST API for ticket creation and management:

```python
def create_jira_ticket(summary: str, description: str):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": description}
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Task"},
            "assignee": {"id": "712020:5f0ba63e-f2a3-40da-bbea-cb1c75c04953"}
        }
    }
    # ... [implementation details]
```

## Setup Instructions

Before using this tool, you'll need to configure your Jira credentials and settings.

### 1. Replace with Your Email ID

In the code, update the constant EMAIL with your own email address associated with your Atlassian (Jira) account:

```python
EMAIL = "your-email@example.com"  # Replace with your own email
```

### 2. Generate Jira API Token

Generate an API token for Jira authentication:
1. Visit [Atlassian API Token Generator](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Name your token and copy it
4. Replace the constant API_TOKEN in the code with your token:

```python
API_TOKEN = "your-generated-api-token"  # Replace with your generated API token
```

### 3. Set Up Your Jira Base URL

Create a project on Jira and navigate to your Jira board. Identify your Jira domain (workspace) and update the JIRA_BASE_URL constant:

```python
JIRA_BASE_URL = "https://your-domain.atlassian.net"  # Replace with your actual Jira workspace
```

For example, if your workspace name is exampleworkspace, it should be: 
`JIRA_BASE_URL = "https://exampleworkspace.atlassian.net"`

### 4. Verify and Update Your Project Key

On your Jira board, create a test ticket to verify your project key. The project key is the prefix in your issue keys (e.g., CPG, FTS, FT). Update the PROJECT_KEY constant accordingly:

```python
PROJECT_KEY = "YOUR_PROJECT_KEY"  # Replace with your actual project key (e.g., CPG, FTS, FT)
```

### 5. (Optional) Update Gemini API Keys

The code includes default Gemini API keys in the gemini_keys list. They should work as provided, but you can generate new keys if needed from [Google's Gemini API](https://makersuite.google.com/app/apikey).

If you generate your own, update the list accordingly:

```python
gemini_keys = ['your-first-gemini-api-key', 'your-second-gemini-api-key']
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/jira-automation-tool.git
cd jira-automation-tool

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage
Run the script and follow the prompts:
```
python flight_tracking_system.py
```

When prompted, enter your main task requirement. For example:
```
Enter the main task requirement: Implement a flight tracking system with real-time updates and user notifications
```

The system will:
1. Create a parent Jira ticket
2. Generate subtasks using Gemini AI
3. Create Jira tickets for each subtask
4. Generate test cases for each subtask
5. Create test case subtasks in Jira
6. Display all created tickets
