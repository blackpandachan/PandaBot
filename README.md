# Discord Bot with AWS Bedrock Integration

A Discord bot that integrates with AWS Bedrock's Large Language Models (LLMs) to provide conversational responses, trivia, storytelling, and more. The bot supports custom moods, maintains separate conversations per user, and offers a variety of interactive commands.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Commands](#commands)
- [Dockerization](#dockerization)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Contact](#contact)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Conversational Responses**: Interacts with users using AWS Bedrock LLMs.
- **Custom Moods**: Users can set the bot's mood (e.g., friendly, sarcastic) for personalized interactions.
- **Per-User Conversations**: Maintains individual conversation history for each user.
- **Trivia and Storytelling**: Offers trivia questions and supports collaborative storytelling.
- **Text Summarization**: Summarizes long texts provided by users.
- **Model Listing**: Displays available LLM models upon request.
- **Robust Logging**: Logs user interactions with user IDs and display names, ensuring privacy and traceability.

---

## Prerequisites

- **Python 3.10 or higher**
- **Discord Account and Server**: To add and interact with your bot.
- **AWS Account**: With access to AWS Bedrock LLMs.
- **AWS Credentials**: AWS Access Key ID and Secret Access Key with appropriate permissions.
- **Docker** (Optional): For containerization and easier deployment.

---

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/BlackPandaChan/PandaBot.git
   cd PandaBot
2. **Create a Virtual Environment (Recommended)**
   ```python3 -m venv venv
   source venv/bin/activate   # On macOS/Linux
   venv\Scripts\activate      # On Windows
   ```
3. **Install Dependencies**
   ```pip install -r requirements.txt```
4. **Set Up Environment Variables**
   ```touch .env```
5. **Add the following to your .env**
   ```DISCORD_BOT_TOKEN=your_discord_bot_token
      AWS_ACCESS_KEY_ID=your_aws_access_key_id
      AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
      BWB_REGION_NAME=your_aws_region
   ```

## Commands

1. **Commands**
   ```Here are some of the commands the bot supports:
   !ask [question]: Ask the bot anything, and it will respond with information from the LLM.
   !setmood [mood]: Set the bot's mood for 60 minutes (e.g., friendly, sarcastic, formal).
   !story [addition]: Contribute to a collaborative story.
   !trivia: Ask for a random trivia question.
   !summarize [text]: Provide a long text, and the bot will summarize it.
   !models: Display a list of available models from the models.json file.
   ```

### What's Next?

NO IDEA!

