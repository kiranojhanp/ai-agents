import asana
from asana.rest import ApiException
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import json
import os
import logging

# Set system prompt for agent
system_prompt = f"You are an experienced project manager at Fewa, a dynamic startup. Your role is to assist users in breaking down their projects into actionable tasks, prioritizing them effectively, and creating well-structured tickets in Asana. Provide clear task descriptions, assign priority levels using the MoSCoW method, suggest aggressive yet realistic deadlines with buffer times, and categorize tasks based on user requirements and project objectives. Ensure tasks are concise, actionable, and aligned with the user's overall goals. Embody the 'move fast and break nothing' philosophy by incorporating feature flags for direct production deployment, including clear communication details, automating repetitive steps, ensuring quality assurance through code reviews, managing dependencies, efficiently tracking time, documenting changes, and utilizing predefined templates for quick task creation. The current date is: {datetime.now().date()}"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
# Handle env variables
# --------------------------------------------------------------

# Load environment variables
load_dotenv()

# Validate and retrieve environment variables
openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
openai_api_key = os.getenv('OPENAI_API_KEY', '')
asana_access_token = os.getenv('ASANA_ACCESS_TOKEN', '')
asana_project_id = os.getenv('ASANA_PROJECT_ID', '')

if not openai_api_key:
    logger.error("OPENAI_API_KEY is not set.")
    exit(1)
if not asana_access_token:
    logger.error("ASANA_ACCESS_TOKEN is not set.")
    exit(1)
if not asana_project_id:
    logger.error("ASANA_PROJECT_ID is not set.")
    exit(1)

# --------------------------------------------------------------
# Configuration setup for OpenAI and Asana
# --------------------------------------------------------------

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# Initialize Asana client
configuration = asana.Configuration()
configuration.access_token = asana_access_token
api_client = asana.ApiClient(configuration)
tasks_api_instance = asana.TasksApi(api_client)

# --------------------------------------------------------------
# Business logics for AI agent
# --------------------------------------------------------------
def create_asana_task(task_name, due_on="today"):
    """
    Creates a task in Asana with the given name and due date.

    Args:
        task_name (str): The name of the task.
        due_on (str, optional): The due date in YYYY-MM-DD format or "today". Defaults to "today".

    Returns:
        str: JSON response from Asana API or an error message.
    """

    if due_on == "today":
        due_on = str(datetime.now().date())
    else:
        try:
            datetime.strptime(due_on, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format for due_on: {due_on}")
            return "Invalid date format for due_on."

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
        logger.error(f"An api exception occurred while creating the task: {e}")
    except Exception as e:
        logger.error(f"Unknown error occured while creating the task: {e}")

def get_tools():
    """
    Defines the tools available for the AI to use.

    Returns:
        list: List of tool descriptions.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_asana_task",
                "description": "Creates a task in Asana given the name of the task and when it is due",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_name": {
                            "type": "string",
                            "description": "The name of the task in Asana"
                        },
                        "due_on": {
                            "type": "string",
                            "description": "The date the task is due in the format YYYY-MM-DD. If not given, the current day is used"
                        },
                    },
                    "required": ["task_name"]
                },
            },
        }
    ]

    return tools   


def prompt_ai(messages):
    """
    Prompts the AI with the conversation messages and handles tool calls if necessary.

    Args:
        messages (list): List of conversation messages.

    Returns:
        str: AI's response content.
    """

    try:
        # First, prompt the AI with the latest user message
        completion = client.chat.completions.create(
            model=openai_model,
            messages=messages,
            tools=get_tools()
        )

        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls

        # Second, see if the AI decided it needs to invoke a tool
        if tool_calls:
            # If the AI decided to invoke a tool, invoke it
            available_functions = {
                "create_asana_task": create_asana_task
            }

            # Add the tool request to the list of messages so the AI knows later it invoked the tool
            messages.append(response_message)

            # Next, for each tool the AI wanted to call, call it and add the tool result to the list of messages
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                if not function_to_call:
                    logger.warning(f"Function {function_name} not available.")
                    continue

                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(**function_args)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response
                })

            # Call the AI again so it can produce a response with the result of calling the tool(s)
            second_response = client.chat.completions.create(
                model=openai_model,
                messages=messages,
            )
            return second_response.choices[0].message.content

        else:
            return response_message.content

    except openai.APIConnectionError as e:
        logger.error(f"The server could not be reached: {e.__cause__}")
    except openai.RateLimitError as e:
        logger.error(f"A 429 status code was received; we should back off a bit.: {e}")
    except openai.APIStatusError as e:
        logger.error(f"Another non-200-range status code was received: {e}")
    except Exception as e:
        logger.error(f"Unknown error occured: {e}")


def main():
    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    try:
        while True:
            user_input = input("Chat with AI (q to quit): ").strip()
            
            if user_input == 'q':
                break  

            messages.append({"role": "user", "content": user_input})
            ai_response = prompt_ai(messages)

            print(ai_response)
            messages.append({"role": "assistant", "content": ai_response})

    except KeyboardInterrupt:
        logger.info("User requested exit.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()