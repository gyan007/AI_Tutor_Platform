from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from ai_tutor_platform.config.configuration import Config

lobj_config = Config()

def get_mistral_llm():
    return ChatOpenAI(
        base_url=lobj_config.get_api_base(),
        api_key=lobj_config.get_api_key(),
        model=lobj_config.get_llm_model(),
        temperature=lobj_config.get_temperature()
    )

def generate_response(prompt: str) -> str:
    """
    Generates a raw string response from the LLM without formatting (no markdown or code blocks).
    """
    llm = get_mistral_llm()

    messages = [
        HumanMessage(content=f"{prompt}")
    ]

    try:
        response = llm.invoke(messages)
        cleaned = response.content.strip()

        if cleaned.startswith("```"):
            # Remove triple backticks and optional 'json'
            cleaned = cleaned.lstrip("`").lstrip("json").strip()
            cleaned = cleaned.rstrip("`").strip()

        return cleaned
    except Exception as e:
        return f"[ERROR] {str(e)}"
