from src.config.configClass import configer
from src.log.logger import logger
from src.utils.path_tool import get_abs_path


def _load_prompt(path: str, name: str) -> str:
    prompt_path = get_abs_path(path)
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        logger.error("[%s] failed to load prompt %s: %s", name, prompt_path, exc)
        raise


def load_system_prompts() -> str:
    return _load_prompt(configer.getPromptInfo().main_prompt_path, "load_system_prompts")


def load_rag_prompts() -> str:
    return _load_prompt(configer.getPromptInfo().rag_prompt_path, "load_rag_prompts")


if __name__ == "__main__":
    print(load_system_prompts())
