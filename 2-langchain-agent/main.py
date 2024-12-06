import asana
from asana.rest import ApiException
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import json
import os

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

# Set system prompt for agent
system_prompt = f"You are an experienced project manager at Fewa, a dynamic startup. Your role is to assist users in breaking down their projects into actionable tasks, prioritizing them effectively, and creating well-structured tickets in Asana. Provide clear task descriptions, assign priority levels using the MoSCoW method, suggest aggressive yet realistic deadlines with buffer times, and categorize tasks based on user requirements and project objectives. Ensure tasks are concise, actionable, and aligned with the user's overall goals. Embody the 'move fast and break nothing' philosophy by incorporating feature flags for direct production deployment, including clear communication details, automating repetitive steps, ensuring quality assurance through code reviews, managing dependencies, efficiently tracking time, documenting changes, and utilizing predefined templates for quick task creation. The current date is: {datetime.now().date()}"


# --------------------------------------------------------------
# Handle env variables
# --------------------------------------------------------------

# Load environment variables
load_dotenv()

# Validate and retrieve environment variables
llm_model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
openai_api_key = os.getenv('OPENAI_API_KEY', '')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
asana_access_token = os.getenv('ASANA_ACCESS_TOKEN', '')
asana_project_id = os.getenv('ASANA_PROJECT_ID', '')


# --------------------------------------------------------------
# Configuration setup for Asana
# --------------------------------------------------------------
configuration = asana.Configuration()
configuration.access_token = asana_access_token
api_client = asana.ApiClient(configuration)
tasks_api_instance = asana.TasksApi(api_client)


# --------------------------------------------------------------
# Business logic for AI agent
# --------------------------------------------------------------

@tool
def create_asana_task(task_name, due_on="today"):
    """
    Creates a task in Asana given the name of the task and when it is due

    Example call:

    create_asana_task("Test Task", "2024-06-24")
    Args:
        task_name (str): The name of the task in Asana
        due_on (str): The date the task is due in the format YYYY-MM-DD. If not given, the current day is used
    Returns:
        str: The API response of adding the task to Asana or an error message if the API call threw an error
    """
    if due_on == "today":
        due_on = str(datetime.now().date())

    task_body = {
        "data": {
            "name": task_name,
            "due_on": due_on,
            "projects": [asana_project_id]
        }
    }

    try:
        api_response = tasks_api_instance.create_task(task_body, {})
        return json.dumps(api_response, indent=2)
    except ApiException as e:
        return f"Exception when calling TasksApi->create_task: {e}"  


def prompt_ai(messages, nested_calls=0):
    if nested_calls > 5:
        raise "AI is tool calling too much!"

    # First, prompt the AI with the latest user message
    tools = [create_asana_task]
    asana_chatbot = ChatOpenAI(model=llm_model) if "gpt" in llm_model.lower() else ChatAnthropic(model=llm_model)
    asana_chatbot_with_tools = asana_chatbot.bind_tools(tools)

    ai_response = asana_chatbot_with_tools.invoke(messages)
    print(ai_response)
    print(type(ai_response))
    tool_calls = len(ai_response.tool_calls) > 0

    # Second, see if the AI decided it needs to invoke a tool
    if tool_calls:
        # If the AI decided to invoke a tool, invoke it
        available_functions = {
            "create_asana_task": create_asana_task
        }

        # Add the tool request to the list of messages so the AI knows later it invoked the tool
        messages.append(ai_response)


        # Next, for each tool the AI wanted to call, call it and add the tool result to the list of messages
        for tool_call in ai_response.tool_calls:
            tool_name = tool_call["name"].lower()
            selected_tool = available_functions[tool_name]
            tool_output = selected_tool.invoke(tool_call["args"])
            messages.append(ToolMessage(tool_output, tool_call_id=tool_call["id"]))                

        # Call the AI again so it can produce a response with the result of calling the tool(s)
        ai_response = prompt_ai(messages, nested_calls + 1)

    return ai_response


def main():
    messages = [
        SystemMessage(content=system_prompt)
    ]

    while True:
        user_input = input("Chat with AI (q to quit): ").strip()
        
        if user_input == 'q':
            break  

        messages.append(HumanMessage(content=user_input))
        ai_response = prompt_ai(messages)

        print(ai_response.content)
        messages.append(ai_response)


if __name__ == "__main__":
    main()