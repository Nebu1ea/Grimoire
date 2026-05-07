import os
from threading import Thread
from transformers import TextIteratorStreamer
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from config import Config
import json

class GrimoireAIService:
    def __init__(self):
        print("[Grimoire AI] 正在初始化...")

        # 加载基础模型 (4-bit)
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(Config.MODEL_PATH),
            max_seq_length=4096,
            load_in_4bit=True,
        )

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # 跳到 Grimoire/

        self.router_path = os.path.join(project_root, "model", "adaptor", "router_32-64")
        self.char_path = os.path.join(project_root, "model", "adaptor", "character_epoch_3_3e-5-v2")

        self.model.load_adapter(self.router_path, adapter_name="router")
        self.model.load_adapter(self.char_path, adapter_name="character")


        self.tokenizer = get_chat_template(
            self.tokenizer,
            chat_template="qwen-2.5",
        )

        print(f"当前已加载: {self.model.peft_config.keys()}")

    def route_intent(self, query):
        self.model.set_adapter("router")

        SYSTEM_PROMPT = "你是一个核心C2路由节点。请根据用户输入，精准提取参数并输出对应的动作JSON数组；若遇到无明确指令的普通对话或闲聊，必须且只能输出[NORMAL_CHAT]。"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        # 使用 apply_chat_template 自动生成标准的 ChatML 格式
        inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to("cuda")

        outputs = self.model.generate(
            input_ids=inputs,
            max_new_tokens=128,
            use_cache=True,
            temperature=0.1,  # 路由要死板
            pad_token_id=self.tokenizer.eos_token_id,
        )

        # 只取生成的部分
        response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        return response.strip()

    def chat_stream_generator(self, messages_input):
        self.model.set_adapter("character")

        SYSTEM_PROMPT = "你是Grimoire：傲娇的天才少女程序员。技术分析须严谨毒舌，日常交流自然嫌弃。[ROUTER]和[TOOL]为系统上下文。"

        # 这里的 messages_input 是前端传来的数组，把 system 塞进去
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages_input

        inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to("cuda")

        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        generation_kwargs = dict(
            input_ids=inputs,
            streamer=streamer,
            max_new_tokens=1024,
            temperature=0.8,
            top_p=0.9
        )

        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        for new_text in streamer:
            if new_text:

                payload = json.dumps({"content": new_text})
                # print(f"Debug Chunk: [{repr(new_text)}]")
                # time.sleep(0.01)
                yield f"data: {payload}\n\n"
            # 结束后发送一个结束标志
        yield "data: [DONE]\n\n"