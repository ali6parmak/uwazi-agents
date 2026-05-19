import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
UWAZI_TEMPLATE_ID = os.getenv("UWAZI_TEMPLATE_ID", "")
UWAZI_URL = os.getenv("UWAZI_URL", "http://localhost:3000")
UWAZI_USER = os.getenv("UWAZI_USER", "admin")
UWAZI_PASSWORD = os.getenv("UWAZI_PASSWORD", "change this password now")
PROMPT = os.getenv("PROMPT", "Reply with one sentence describing what a software agent is.")
MODEL = os.getenv("MODEL", "gemma4:e2b")

# The two Ollama models we want to compare across frameworks.
# Both expose `tools` capability in their Modelfile, which is what the
# agent loops below rely on.
MODEL_LOCAL = os.getenv("MODEL_LOCAL", "gemma4:e2b")
MODEL_CLOUD = os.getenv("MODEL_CLOUD", "nemotron-3-super:cloud")
MODELS = [MODEL_LOCAL, MODEL_CLOUD]


RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

if __name__ == "__main__":
    print(f"OLLAMA_BASE_URL: {OLLAMA_BASE_URL}")
    print(f"UWAZI_TEMPLATE_ID: {UWAZI_TEMPLATE_ID}")
    print(f"UWAZI_URL: {UWAZI_URL}")
    print(f"UWAZI_USER: {UWAZI_USER}")
    print(f"UWAZI_PASSWORD: {UWAZI_PASSWORD}")
    print(f"PROMPT: {PROMPT}")
    print(f"MODELS: {MODELS}")
