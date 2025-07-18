import json
import os
from pathlib import Path
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from dotenv import load_dotenv

# --- Load Environment and Configuration ---
load_dotenv()

def load_prompts() -> Dict[str, Any]:
    """Loads the prompts from the JSON file."""
    config_path = Path(__file__).parent.parent / "config" / "prompts.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

PROMPTS = load_prompts()

# --- Initialize LLM ---
# Using a generic name, can be swapped with other models if needed
llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-nano"),
    temperature=os.getenv("OPENAI_TEMPERATURE", 0.7),
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# --- Chain Definitions ---

# 1. Emotion Analysis Chain
emotion_analysis_prompt = ChatPromptTemplate.from_template(
    PROMPTS["emotion_analysis"]["system_prompt"]
)
emotion_analysis_chain = LLMChain(
    llm=llm,
    prompt=emotion_analysis_prompt,
    output_parser=JsonOutputParser(),
    verbose=True,
)

# 2. Daily Summary (Full) Chain
daily_summary_full_prompt = ChatPromptTemplate.from_template(
    PROMPTS["daily_summary_full"]["system_prompt"]
)
daily_summary_full_chain = LLMChain(
    llm=llm,
    prompt=daily_summary_full_prompt,
    output_parser=StrOutputParser(),
    verbose=True,
)

# 3. Daily Summary (Short) Chain
daily_summary_short_prompt = ChatPromptTemplate.from_template(
    PROMPTS["daily_summary_short"]["system_prompt"]
)
daily_summary_short_chain = LLMChain(
    llm=llm,
    prompt=daily_summary_short_prompt,
    output_parser=StrOutputParser(),
    verbose=True,
)

# 4. Forget Confirmation Chain
forget_confirmation_prompt = ChatPromptTemplate.from_template(
    PROMPTS["forget_confirmation"]["system_prompt"]
)
forget_confirmation_chain = LLMChain(
    llm=llm,
    prompt=forget_confirmation_prompt,
    output_parser=StrOutputParser(),
    verbose=True,
)

# 5. RAG Conversation Chain
# This one is slightly different as it needs context injected dynamically.
# We define the prompt here, but the chain might be assembled just-in-time in the agent logic.
rag_conversation_prompt = ChatPromptTemplate.from_template(
    PROMPTS["rag_conversation"]["system_prompt"]
)
rag_conversation_chain = LLMChain(
    llm=llm,
    prompt=rag_conversation_prompt,
    output_parser=StrOutputParser(),
    verbose=True,
)

def get_chains():
    """Returns a dictionary of all initialized chains."""
    return {
        "emotion": emotion_analysis_chain,
        "summary_full": daily_summary_full_chain,
        "summary_short": daily_summary_short_chain,
        "forget_confirm": forget_confirmation_chain,
        "rag_conversation": rag_conversation_chain,
    }

print("✅ LangChain chains initialized successfully.") 