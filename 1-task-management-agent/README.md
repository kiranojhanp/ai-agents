# Project Manager AI with Asana Integration

## Overview

This is a AI powered project management agent that integrates with Asana to help users break down their projects into actionable tasks, prioritize them effectively, and create well-structured tickets in Asana. The assistant leverages OpenAI's GPT models to understand user inputs and generate task descriptions, assign priority levels, suggest deadlines, and categorize tasks based on the user's requirements and project objectives. The tasks are then automatically created in the specified Asana project.

## Features

- **AI-Driven Task Creation:** Utilizes OpenAI's GPT models to generate detailed and actionable task descriptions.
- **Asana Integration:** Automatically creates tasks in a specified Asana project with due dates and task names.
- **Interactive Chat Interface in CLI:** Provides an interactive chat interface where users can input project details and receive AI-generated task suggestions.
- **Customizable Task Due Dates:** Allows users to specify task due dates or defaults to the current day.

## Prerequisites

Before running the code, ensure you have the following:

- **OpenAI API Key:** Obtain your OpenAI API key by following the instructions here.
- **Asana Access Token:** Get your Asana personal access token through the Asana developer console by following the instructions here.
- **Asana Project ID:** Identify the Asana project ID from the URL when you visit a project in the Asana UI. For example, if your URL is https://app.asana.com/0/123456789/1212121212, then your Asana project ID is 123456789.
