import time

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler


MODEL_NAME = "mlx-community/Qwen3-8B-4bit"


class LocalModel:
    def __init__(self, model_name: str = MODEL_NAME):
        print("Loading local AI model...")

        self.model, self.tokenizer = load(model_name)

        self.system_prompt = (
            "You are MyAI, a local AI assistant running on an Apple M4 Mac. "
            "You are primarily a software engineering assistant. "
            "You specialize in code generation, debugging, troubleshooting, "
            "Linux, databases, system administration, and technical reasoning. "
            "Be precise, practical, and avoid inventing facts."
        )

        print("Model loaded.")

    def ask(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
    ) -> str:

        full_messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        full_messages.extend(messages)

        prompt = self.tokenizer.apply_chat_template(
            full_messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        sampler = make_sampler(
            temp=0.7,
            top_p=0.8,
        )

        print("[MyAI] Thinking...")

        start_time = time.perf_counter()

        response = generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            sampler=sampler,
            verbose=False,
        )

        elapsed = time.perf_counter() - start_time

        print(
            f"[MyAI] Response generated in {elapsed:.2f} seconds"
        )

        return response.strip()
