import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
from typing import List

class LocalLLM:
    def __init__(self, model_name="trillionlabs/Trillion-7B-preview", device="gpu"):
        self.device = device

        # 모델 로컬 경로 확인 및 분기 처리
        local_model_path = os.path.join("data", "models", model_name)
        if os.path.isdir(local_model_path):
            model_path = local_model_path
            local_files_only = True
        else:
            model_path = model_name
            local_files_only = False

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True,
            padding_side='left',
            local_files_only=local_files_only
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
            trust_remote_code=True,
            local_files_only=local_files_only
        ).to(self.device)

        self.model.eval()

    def generate(self, prompt, streaming=False):
        messages = [{"role": "user", "content": prompt}]
        input_ids = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt"
        )
        input_ids = input_ids.to(self.device)

        if streaming:
            streamer = TextIteratorStreamer(self.tokenizer)
            thread = Thread(target=self.model.generate, kwargs=dict(
                input_ids=input_ids,
                eos_token_id=self.tokenizer.eos_token_id,
                max_new_tokens=4096,
                do_sample=True,
                temperature=0.6,
                top_p=0.95,
                streamer=streamer
            ))
            thread.start()

            collected = ""
            for text in streamer:
                print(text, end="", flush=True)
                collected += text
            return collected

        else:
            output = self.model.generate(
                input_ids,
                eos_token_id=self.tokenizer.eos_token_id,
                max_new_tokens=4096,
                do_sample=True,
                temperature=0.6,
                top_p=0.95,
            )
            return self.tokenizer.decode(output[0], skip_special_tokens=True)

    def batch_generate(self, prompts: List[str]) -> List[str]:
        messages_batch = [
            [{"role": "user", "content": prompt}] for prompt in prompts
        ]
        inputs = self.tokenizer.apply_chat_template(
            messages_batch,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            padding=True
        )
        input_ids = inputs.to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                eos_token_id=self.tokenizer.eos_token_id,
                max_new_tokens=4096,
                do_sample=True,
                temperature=0.6,
                top_p=0.95,
                pad_token_id=self.tokenizer.pad_token_id
            )
        decoded = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
        return decoded

local_llm = None

def get_local_llm():
    global local_llm
    if local_llm is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        local_llm = LocalLLM(model_name="trillionlabs/Trillion-7B-preview", device=device)
    return local_llm