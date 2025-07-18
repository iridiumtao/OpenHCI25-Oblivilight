import json
import os
from pathlib import Path
from typing import Dict, Any
import logging

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from dotenv import load_dotenv

# --- Load Environment and Configuration ---
load_dotenv()
logger = logging.getLogger(__name__)

def load_prompts() -> Dict[str, Any]:
    """Loads the prompts from the JSON file."""
    config_path = Path(__file__).parent.parent / "config" / "prompts.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

PROMPTS = load_prompts()

# --- Initialize LLM ---
# Using a generic name, can be swapped with other models if needed
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-nano"),
    temperature=float(os.getenv("OPENAI_TEMPERATURE", 0.7))
)

# --- Chain Definitions using LCEL (LangChain Expression Language) ---

# 1. Emotion Analysis Chain
emotion_prompt_template = PROMPTS["emotion_analysis"]["system_prompt"]
logger.info(f"Emotion analysis prompt template: {emotion_prompt_template}")
emotion_analysis_prompt = ChatPromptTemplate.from_template(emotion_prompt_template)
emotion_analysis_chain = emotion_analysis_prompt | llm | JsonOutputParser()


# 2. Daily Summary (Full) Chain
daily_summary_full_prompt = ChatPromptTemplate.from_template(
    PROMPTS["daily_summary_full"]["system_prompt"]
)
daily_summary_full_chain = daily_summary_full_prompt | llm | StrOutputParser()


# 3. Daily Summary (Short) Chain
daily_summary_short_prompt = ChatPromptTemplate.from_template(
    PROMPTS["daily_summary_short"]["system_prompt"]
)
daily_summary_short_chain = daily_summary_short_prompt | llm | StrOutputParser()


# 4. Forget Confirmation Chain
forget_confirmation_prompt = ChatPromptTemplate.from_template(
    PROMPTS["forget_confirmation"]["system_prompt"]
)
forget_confirmation_chain = forget_confirmation_prompt | llm | StrOutputParser()


# 5. RAG Conversation Chain
rag_conversation_prompt = ChatPromptTemplate.from_template(
    PROMPTS["rag_conversation"]["system_prompt"]
)
rag_conversation_chain = rag_conversation_prompt | llm | StrOutputParser()


def get_chains():
    """Returns a dictionary of all initialized chains."""
    return {
        "emotion": emotion_analysis_chain,
        "summary_full": daily_summary_full_chain,
        "summary_short": daily_summary_short_chain,
        "forget_confirm": forget_confirmation_chain,
        "rag_conversation": rag_conversation_chain,
    }

print("✅ LangChain chains initialized successfully using LCEL.") 