import discord
from discord.ext import commands, tasks
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from langchain_aws import BedrockLLM, ChatBedrock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Path to the models.json file
MODELS_FILE_PATH = 'models.json'

# Custom logging formatter to handle missing 'user_id' and 'user_name'
class CustomFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'user_id'):
            record.user_id = 'N/A'
        if not hasattr(record, 'user_name'):
            record.user_name = 'N/A'
        return super().format(record)

# Set up logging with custom formatter
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = CustomFormatter('%(asctime)s - %(levelname)s - User %(user_id)s (%(user_name)s) - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Remove default help command
bot.remove_command('help')

# Bedrock model parameters
DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20240620-v1:0"
AWS_REGION = os.getenv("BWB_REGION_NAME")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Global variables to store mood, conversation state, and story
user_moods = defaultdict(lambda: "friendly")
mood_timers = defaultdict(lambda: None)
conversation_state = defaultdict(list)  # Store ongoing conversation per user
story_state = defaultdict(list)  # Store ongoing stories per channel
TOKEN_LIMIT = 4000  # Define a reasonable token limit for conversation context

# LLM Helper Functions
def get_llm(model_id):
    if model_id.startswith("anthropic."):
        return ChatBedrock(
            model_id=model_id,
            region_name=AWS_REGION
        )
    else:
        return BedrockLLM(
            model_id=model_id,
            region_name=AWS_REGION,
            model_kwargs={"max_length": 4096, "temperature": 0.7}
        )

def count_tokens(text):
    """Estimate token count based on word count."""
    return len(text.split())

async def ask_llm(question, model_id=DEFAULT_MODEL, mood="friendly", conversation=[], user_id=None, user_name=None):
    logging.info(f"Querying LLM '{model_id}' with question: {question} and mood: {mood}",
                 extra={'user_id': user_id, 'user_name': user_name})
    
    try:
        llm = get_llm(model_id)
        conversation_text = "\n".join(conversation) + f"\nUser: {question}"
        prompt = f"Respond in a {mood} tone.\n{conversation_text}"
        
        if isinstance(llm, ChatBedrock):
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
            response = llm.invoke(messages)
            return response.content.strip()
        else:
            response = llm.predict(prompt)
            return response.strip()
        
    except Exception as e:
        logging.error(f"Error while querying LLM: {e}", extra={'user_id': user_id, 'user_name': user_name})
        return "Oops, I had trouble thinking. Try asking me again!"

# Load model data from models.json file
def load_models():
    try:
        with open(MODELS_FILE_PATH, 'r') as f:
            models_data = json.load(f)
        return models_data['modelSummaries']
    except Exception as e:
        logging.error(f"Error loading models.json: {e}", extra={'user_id': 'N/A', 'user_name': 'N/A'})
        return []

# Show a few models by default, filter by provider or model on request
@bot.command(name='models')
async def models(ctx, *args):
    user_id = ctx.author.id
    user_name = ctx.author.display_name
    models = load_models()

    if not models:
        await ctx.send("No models available. Please check the models.json file.")
        return

    # If no args are provided, show the first few models
    if not args:
        response = "\n".join([f"**{model['modelName']} ({model['modelId']})** - {model['providerName']}" for model in models[:5]])
        response += "\n\nTo see all models, type `!models all` or filter by provider/model, e.g., `!models anthropic`."
    else:
        # Filter based on the argument (model provider or model name)
        query = " ".join(args).lower()
        filtered_models = [model for model in models if query in model['providerName'].lower() or query in model['modelName'].lower() or query in model['modelId'].lower()]

        if filtered_models:
            response = "\n".join([f"**{model['modelName']} ({model['modelId']})** - {model['providerName']}" for model in filtered_models])
        else:
            response = f"No models found matching `{query}`. Try using a provider or model name."

    await chunked_send(ctx, response)
    logging.info(f"Displayed models for query: {args}", extra={'user_id': user_id, 'user_name': user_name})

# Chunked send function to handle long responses
async def chunked_send(ctx, text, chunk_size=2000):
    for i in range(0, len(text), chunk_size):
        await ctx.send(text[i:i+chunk_size])

# Timer task to reset mood after 60 minutes
@tasks.loop(minutes=1)
async def reset_mood_task():
    for user_id in list(mood_timers):
        if datetime.now() > mood_timers[user_id]:
            user_moods.pop(user_id, None)
            mood_timers.pop(user_id, None)
            logging.info(f"Mood has been reset.", extra={'user_id': user_id, 'user_name': 'N/A'})

@bot.event
async def on_ready():
    logging.info(f"{bot.user.name} has connected to Discord and is ready!", extra={'user_id': 'N/A', 'user_name': 'N/A'})
    await bot.change_presence(activity=discord.Game(name="Ask me anything!"))
    reset_mood_task.start()

# Command to set the bot's mood
@bot.command(name='setmood')
async def set_mood(ctx, *, mood: str):
    user_id = ctx.author.id
    user_name = ctx.author.display_name
    user_moods[user_id] = mood
    mood_timers[user_id] = datetime.now() + timedelta(minutes=60)
    await ctx.send(f"Bot mood for {ctx.author.name} has been set to {mood}. It will last for 60 minutes.")
    logging.info(f"Mood set to '{mood}'.", extra={'user_id': user_id, 'user_name': user_name})

# Command to ask questions with conversation tracking and mood applied
@bot.command(name='ask')
async def ask_with_mood(ctx, *, question: str):
    user_id = ctx.author.id
    user_name = ctx.author.display_name
    mood = user_moods.get(user_id, "friendly")
    
    # Get current conversation history for the user
    conversation = conversation_state[user_id]
    
    # Add the user's question to the conversation
    conversation.append(f"User: {question}")
    
    # Ensure the conversation does not exceed the token limit
    total_tokens = sum(count_tokens(msg) for msg in conversation)
    while total_tokens > TOKEN_LIMIT and conversation:
        removed = conversation.pop(0)
        total_tokens = sum(count_tokens(msg) for msg in conversation)
        logging.info(f"Conversation truncated. Removed message: '{removed}'", extra={'user_id': user_id, 'user_name': user_name})
    
    # Query the LLM with conversation context
    response = await ask_llm(question, mood=mood, conversation=conversation, user_id=user_id, user_name=user_name)
    
    # Add the bot's response to the conversation
    conversation.append(f"Bot: {response}")
    
    # Update the conversation state
    conversation_state[user_id] = conversation
    
    # Send response in chunks
    await chunked_send(ctx, response)
    logging.info(f"Responded to question.", extra={'user_id': user_id, 'user_name': user_name})

# Command for collaborative storytelling
@bot.command(name='story')
async def story(ctx, *, addition: str = None):
    user_id = ctx.author.id
    user_name = ctx.author.display_name
    channel_id = ctx.channel.id
    story = story_state[channel_id]

    if addition:
        story.append(f"{ctx.author.name}: {addition}")
        response = "Story so far:\n" + "\n".join(story)
        logging.info(f"Added to story.", extra={'user_id': user_id, 'user_name': user_name})
    else:
        response = "Here’s the story so far:\n" + "\n".join(story) if story else "No story started yet!"
        logging.info(f"Requested story.", extra={'user_id': user_id, 'user_name': user_name})

    await chunked_send(ctx, response)

# Command for trivia
@bot.command(name='trivia')
async def trivia(ctx):
    user_id = ctx.author.id
    user_name = ctx.author.display_name
    prompt = "Ask me a fun trivia question."
    mood = user_moods.get(user_id, "friendly")
    response = await ask_llm(prompt, mood=mood, user_id=user_id, user_name=user_name)
    await chunked_send(ctx, f"Trivia Time: {response}")
    logging.info(f"Provided trivia.", extra={'user_id': user_id, 'user_name': user_name})

# Command for summarizing long text
@bot.command(name='summarize')
async def summarize(ctx, *, text: str):
    user_id = ctx.author.id
    user_name = ctx.author.display_name
    prompt = f"Summarize this text in a concise manner: {text}"
    mood = user_moods.get(user_id, "friendly")
    response = await ask_llm(prompt, mood=mood, user_id=user_id, user_name=user_name)
    await chunked_send(ctx, f"Summary: {response}")
    logging.info(f"Provided summary.", extra={'user_id': user_id, 'user_name': user_name})

# Custom help command
@bot.command(name='help')
async def custom_help_command(ctx):
    user_id = ctx.author.id
    user_name = ctx.author.display_name
    help_messages = [
        "**!ask [question]**: Ask me anything! I will respond with my knowledge in a conversational tone.",
        "**!setmood [mood]**: Set the bot's mood for 60 minutes (e.g., friendly, sarcastic, formal).",
        "**!story [addition]**: Contribute to a collaborative story. Add your part, and I'll continue the narrative.",
        "**!trivia**: Ask for a random trivia question and test your knowledge!",
        "**!summarize [text]**: Provide a long text, and I will summarize it in a concise manner.",
        "**!models**: Display a list of available models (default: 5). Use `!models all` to see all available models."
    ]
    for message in help_messages:
        await chunked_send(ctx, message)
    logging.info(f"Displayed help.", extra={'user_id': user_id, 'user_name': user_name})

# Error handling
@bot.event
async def on_command_error(ctx, error):
    user_id = ctx.author.id if ctx.author else 'N/A'
    user_name = ctx.author.display_name if ctx.author else 'N/A'
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("I didn't understand that command. Try `!ask [question]`!")
    else:
        await ctx.send(f"An error occurred: {str(error)}")
    logging.error(f"Command error: {error}", extra={'user_id': user_id, 'user_name': user_name})

# Start the bot
if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        logging.error("No Discord bot token found. Please set the DISCORD_BOT_TOKEN environment variable.", extra={'user_id': 'N/A', 'user_name': 'N/A'})
    else:
        bot.run(DISCORD_BOT_TOKEN)
