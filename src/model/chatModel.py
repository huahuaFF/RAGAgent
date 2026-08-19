from langchain_deepseek import ChatDeepSeek

from src.config.configClass import configer


chat_info = configer.getChatModelInfo()

chatModel = ChatDeepSeek(
    model=chat_info.model_name,
    api_key=chat_info.api_key,
    temperature=chat_info.temperature,
    max_tokens=chat_info.max_tokens,
    timeout=chat_info.timeout,
    max_retries=chat_info.max_retries,
)
