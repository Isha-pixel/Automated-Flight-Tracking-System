import os
import json
import time
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import google.generativeai as genai

# Load environment variables from a .env file
load_dotenv()

# --- Jira Configuration ---
JIRA_API_ENDPOINT = os.getenv("JIRA_BASE_URL")
JIRA_USER_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_SECRET = os.getenv("JIRA_API_TOKEN") # https://id.atlassian.com/manage-profile/security/api-tokens
TARGET_PROJECT = "CPG"

# Set up authentication and headers for Jira requests
jira_auth_credentials = HTTPBasicAuth(JIRA_USER_EMAIL, JIRA_API_SECRET)
request_headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# --- Gemini API Configuration ---
gemini_api_keys = [os.getenv('GEMINI_API_KEY1'), os.getenv('GEMINI_API_KEY2')]
active_gemini_key_index = 0

def initialize_gemini_model():
    """Configures and returns a Gemini generative model instance."""
    global active_gemini_key_index
    key = gemini_api_keys[active_gemini_key_index]
    genai.configure(api_key=key)
    return genai.GenerativeModel('gemini-1.5-pro-latest')

def generate_with_gemini_resilience(prompt_text):
    """
    Generates content using the Gemini API, with logic to cycle through
    API keys if one fails due to rate limits or other errors.
    """
    global active_gemini_key_index
    start_index = active_gemini_key_index
    num_attempts = 0

    while num_attempts < len(gemini_api_keys):
        try:
            generative_model = initialize_gemini_model()
            api_response = generative_model.generate_content(prompt_text)
            return api_response.text
        except Exception as error:
            print(f"Gemini key {gemini_api_keys[active_gemini_key_index]} encountered an error: {error}")
            
            # Pause if the error is related to rate limiting or quotas
            error_string = str(error)
            if '429' in error_string or 'quota' in error_string:
                time.sleep(1)
            
            # Cycle to the next available key
            active_gemini_key_index = (active_gemini_key_index + 1) % len(gemini_api_keys)
            num_attempts += 1

            # If all keys have been tried in this cycle, wait longer
            if active_gemini_key_index == start_index:
                time.sleep(2)
    
    raise ConnectionError("All Gemini API keys failed after multiple attempts")

# --- Jira API Functions ---
def create_jira_issue(title, issue_description):
    """Posts a new issue to a Jira project."""
    api_url = f"{JIRA_API_ENDPOINT}/rest/api/3/issue"
    request_body = {
        "fields": {
            "project": {"key": TARGET_PROJECT},
            "summary": title,
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": issue_description}]}]
            },
            "issuetype": {"name": "Task"},
            "assignee": {"id": "712020:f1dccbef-1286-406d-979d-e8adfe4cb987"} # NOTE: Update with your accountId
        }
    }
    
    response = requests.post(api_url, headers=request_headers, json=request_body, auth=jira_auth_credentials)
    
    if response.status_code == 201:
        created_issue = response.json()
        print(f"Successfully created Jira issue: {created_issue['key']}")
        return created_issue['key']
    else:
        print(f"Error creating Jira issue: {response.status_code} - {response.text}")
        return None

def create_jira_child_issue(parent_issue_key, title, issue_description):
    """Posts a new subtask under a parent issue in Jira."""
    api_url = f"{JIRA_API_ENDPOINT}/rest/api/3/issue"
    request_body = {
        "fields": {
            "project": {"key": TARGET_PROJECT},
            "parent": {"key": parent_issue_key},
            "summary": title,
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": issue_description}]}]
            },
            "issuetype": {"name": "Subtask"},
            "assignee": {"id": "712020:f1dccbef-1286-406d-979d-e8adfe4cb987"} # NOTE: Update with your accountId
        }
    }
    
    response = requests.post(api_url, headers=request_headers, json=request_body, auth=jira_auth_credentials)

    if response.status_code == 201:
        created_issue = response.json()
        print(f"Created subtask {created_issue['key']} for parent {parent_issue_key}")
        return created_issue['key']
    else:
        print(f"Error creating subtask for {parent_issue_key}: {response.status_code} - {response.text}")
        return None

def get_project_issues():
    """Fetches all issues from the project, excluding specific sample keys."""
    api_url = f"{JIRA_API_ENDPOINT}/rest/api/3/search"
    query_params = {
        "jql": f"project={TARGET_PROJECT} AND key NOT IN (CPG-1, CPG-2)",
        "maxResults": 50,
        "fields": "summary,status,assignee"
    }
    
    response = requests.get(api_url, headers=request_headers, params=query_params, auth=jira_auth_credentials)
    
    if response.status_code == 200:
        issues_data = response.json().get("issues", [])
        print(f"\nFound {len(issues_data)} visible issues in project {TARGET_PROJECT}:\n")
        for issue in issues_data:
            fields = issue.get("fields", {})
            assignee_info = fields.get("assignee")
            assignee_name = assignee_info["displayName"] if assignee_info else "Unassigned"
            print(f"- {issue['key']}: {fields['summary']} "
                  f"[Status: {fields['status']['name']}] (Assignee: {assignee_name})")
        return issues_data
    else:
        print(f"Failed to fetch issues: {response.status_code} - {response.text}")
        return []

def get_jira_issue_link_types():
    """Retrieves all available issue link types from Jira."""
    api_url = f"{JIRA_API_ENDPOINT}/rest/api/3/issueLinkType"
    response = requests.get(api_url, headers=request_headers, auth=jira_auth_credentials)
    
    if response.status_code == 200:
        link_types_data = response.json().get("issueLinkTypes", [])
        print("\nAvailable Jira issue link types:")
        for link_type in link_types_data:
            print(f"  - {link_type['name']} (Inward: '{link_type['inward']}', Outward: '{link_type['outward']}')")
        return link_types_data
    else:
        print(f"Failed to get link types: {response.status_code} - {response.text}")
        return []

def link_jira_issues(source_issue, target_issue, relationship_type="Relates"):
    """Creates a link between two Jira issues."""
    api_url = f"{JIRA_API_ENDPOINT}/rest/api/3/issueLink"
    request_body = {
        "outwardIssue": {"key": source_issue},
        "inwardIssue": {"key": target_issue},
        "type": {"name": relationship_type}
    }
    
    print(f"Attempting to link {source_issue} to {target_issue} as '{relationship_type}'...")
    response = requests.post(api_url, headers=request_headers, json=request_body, auth=jira_auth_credentials)
    
    if response.status_code == 201:
        print(f"Successfully linked {source_issue} and {target_issue}.")
        return True
    else:
        print(f"Failed to link issues. Status: {response.status_code}, Response: {response.text}")
        return False

# --- AI-Powered Task Generation Functions ---
def parse_json_from_text(raw_text):
    """Extracts a JSON object or array from a raw string."""
    try:
        json_start_index = raw_text.find('[')
        json_end_index = raw_text.rfind(']') + 1
        if json_start_index != -1 and json_end_index > json_start_index:
            json_string = raw_text[json_start_index:json_end_index]
            return json.loads(json_string)
        else:
            return json.loads(raw_text) # Fallback to parsing the whole string
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}\nRaw text received: {raw_text}")
        return None

def generate_subtasks_from_requirement(main_requirement):
    """Uses Gemini to break down a high-level requirement into actionable subtasks."""
    prompt = f"""
    Based on the software requirement below, generate 3 to 5 distinct, high-level subtasks.
    Requirement: "{main_requirement}"

    Guidelines:
    - Produce between 3 and 5 unique subtasks.
    - Each subtask must be a major development phase (e.g., Backend, Frontend, Testing).
    - Avoid overlapping responsibilities between subtasks.
    - Suggest a relevant category and component name for each.
    - Summaries should be concise (under 100 words).

    Provide the output in this exact JSON format:
    [
      {{
        "summary": "A comprehensive summary of the subtask.",
        "category": "Backend | Frontend | API | DevOps | Testing",
        "component": "A suggested component/module name",
        "title": "A short, descriptive title for the subtask"
      }}
    ]
    Ensure the final output is a valid JSON array of 3 to 5 items.
    """
    raw_response = generate_with_gemini_resilience(prompt)
    return parse_json_from_text(raw_response)

def generate_test_cases_for_task(task_summary, parent_key):
    """Uses Gemini to generate test cases for a specific task."""
    prompt = f"""
    For the development task detailed below, create 3 to 5 comprehensive test cases.
    Task: "{task_summary}" (Parent Ticket: {parent_key})

    Guidelines:
    - Generate between 3 and 5 unique test cases.
    - Each should cover a critical function or edge case.
    - Include specific steps, expected results, and a priority level.
    - Ensure test cases are actionable and not trivial.

    Provide the output in this exact JSON format:
    [
      {{
        "test_id": "TC-1",
        "test_name": "A short, descriptive test case name",
        "description": "A detailed description of the test case",
        "steps": ["Step 1", "Step 2", "Step 3"],
        "expected_result": "The expected outcome after executing the steps",
        "priority": "High | Medium | Low"
      }}
    ]
    Ensure the final output is a valid JSON array of 3 to 5 items.
    """
    print(f"\nGenerating test cases for task {parent_key}...")
    raw_response = generate_with_gemini_resilience(prompt)
    return parse_json_from_text(raw_response)

# --- Main Workflow Functions ---
def create_and_link_tasks(parent_ticket_key, task_definitions):
    """Creates multiple Jira tickets and links them to a parent issue."""
    created_issue_keys = []
    issue_data_mapping = {}
    
    available_link_types = get_jira_issue_link_types()
    preferred_link_types = ["Relates", "Relates to", "Dependency", "Blocks"]
    link_type_to_use = next((t for t in preferred_link_types if t in [lt["name"] for lt in available_link_types]), None)

    if not link_type_to_use and available_link_types:
        link_type_to_use = available_link_types[0]["name"]
    
    if link_type_to_use:
        print(f"Using link type: '{link_type_to_use}'")
    else:
        print("Warning: No suitable issue link types found. Tasks will not be linked.")

    for task in task_definitions:
        full_description = (f"{task['summary']}\n\n"
                            f"Category: {task['category']}\n"
                            f"Component: {task['component']}\n"
                            f"Parent Requirement: {parent_ticket_key}")
        
        new_issue_key = create_jira_issue(task["title"], full_description)
        if new_issue_key:
            created_issue_keys.append(new_issue_key)
            issue_data_mapping[new_issue_key] = task
            
            if link_type_to_use:
                time.sleep(1) # Delay to prevent rate-limiting issues
                link_jira_issues(parent_ticket_key, new_issue_key, link_type_to_use)
    
    return created_issue_keys, issue_data_mapping

def process_and_create_test_cases(task_key, task_data):
    """Generates and creates Jira subtasks for test cases."""
    test_case_definitions = generate_test_cases_for_task(task_data['summary'], task_key)
    created_test_keys = []
    
    if test_case_definitions:
        print(f"\nGenerated {len(test_case_definitions)} test cases for {task_key}:")
        for test_case in test_case_definitions:
            print(f"\n--- {test_case['test_id']}: {test_case['test_name']} (Priority: {test_case['priority']}) ---")
            print(f"Description: {test_case['description']}")
            print("Steps:", ", ".join(test_case['steps']))
            print(f"Expected Result: {test_case['expected_result']}")
            
            steps_string = "\n".join([f"{i}. {step}" for i, step in enumerate(test_case['steps'], 1)])
            subtask_desc = f"""
            Test Case: {test_case['test_name']}
            Description: {test_case['description']}
            
            Steps:
            {steps_string}
            
            Expected Result: {test_case['expected_result']}
            Priority: {test_case['priority']}
            """
            
            subtask_title = f"Test: {test_case['test_name']} [{test_case['priority']}]"
            new_subtask_key = create_jira_child_issue(task_key, subtask_title, subtask_desc.strip())
            
            if new_subtask_key:
                created_test_keys.append(new_subtask_key)
                print(f"Created test case subtask: {new_subtask_key}")
                time.sleep(1) # Delay to prevent rate-limiting
    
    return created_test_keys

# --- Main Execution Block ---
def main():
    """Main function to run the script."""
    # Step 1: Get user input for the main task
    main_requirement = input("Enter the high-level requirement or user story: ")
    
    # Step 2: Create a parent Jira ticket for the requirement
    print("\nCreating a parent ticket for the main requirement...")
    parent_ticket_key = create_jira_issue(
        f"Epic: {main_requirement}",
        f"This is the main parent ticket for the requirement: {main_requirement}"
    )
    
    if not parent_ticket_key:
        print("Could not create a parent ticket. Aborting.")
        return

    # Step 3: Generate development subtasks
    print("\nGenerating development tasks with Gemini...")
    subtask_definitions = generate_subtasks_from_requirement(main_requirement)
    
    # Step 4: Create Jira tickets for the generated subtasks
    if subtask_definitions:
        print("\nGemini generated the following tasks:")
        for i, task in enumerate(subtask_definitions, 1):
            print(f"{i}. {task['title']}")
        
        print("\nCreating and linking Jira tickets for these tasks...")
        created_task_keys, task_data_map = create_and_link_tasks(parent_ticket_key, subtask_definitions)
        
        # Step 5: Generate and create test case subtasks for each created task
        if created_task_keys:
            print(f"\n== Generating Test Cases for {len(created_task_keys)} Tasks ==")
            for task_key in created_task_keys:
                task_data = task_data_map.get(task_key)
                if task_data:
                    print(f"\n--- Processing task {task_key}: {task_data['title']} ---")
                    test_keys = process_and_create_test_cases(task_key, task_data)
                    print(f"Created {len(test_keys)} test case subtasks for {task_key}")
                    time.sleep(2) # Delay between processing each main task
                else:
                    print(f"Warning: Could not find data for task {task_key}. Skipping test case generation.")
    else:
        print("Gemini did not generate any subtasks.")
    
    # Step 6: Display the final state of the project board
    get_project_issues()

if __name__ == "__main__":
    main()
