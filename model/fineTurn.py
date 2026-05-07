import torch
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import is_bfloat16_supported


model_name = "./Qwen2.5-14B-Instruct-abliterated-v2"
data_path = "./微调语句/function calling/functionCalling.jsonl"
output_dir = "./adaptor/router_32-64"

max_seq_length = 2048
load_in_4bit = True


print("以 4bit 加载 qwen2.5")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    dtype=None,
    load_in_4bit=load_in_4bit,
)

# 强制应用 Qwen 的对话模板
tokenizer = get_chat_template(
    tokenizer,
    chat_template="qwen-2.5",  # Qwen 的标准 chat template
)

model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=64,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)


SYSTEM_PROMPT = "你是一个核心C2路由节点。请根据用户输入，精准提取参数并输出对应的动作JSON数组；若遇到无明确指令的普通对话或闲聊，必须且只能输出[NORMAL_CHAT]。"


def format_messages_func(examples):
    convos = examples["messages"]
    texts = []

    for convo in convos:
        if convo[0]["role"] != "system":
            convo.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

        # 使用 Qwen 分词器自动将 messages 转成带 <|im_start|> 的原生字符串
        text = tokenizer.apply_chat_template(
            convo,
            tokenize=False,
            add_generation_prompt=False
        )
        texts.append(text)

    return {"text": texts}


print("正在解析 messages 格式数据...")
dataset = load_dataset("json", data_files=data_path, split="train")
dataset = dataset.map(format_messages_func, batched=True)


trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    dataset_num_proc=2,
    packing=False,
    response_only_loss=True,
    args=TrainingArguments(
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        num_train_epochs=4,
        learning_rate=1e-4,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",
        report_to="tensorboard",
    ),
)


trainer_stats = trainer.train()

model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"Router 适配器已安全落地在：{output_dir}")