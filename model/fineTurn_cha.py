import torch
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import is_bfloat16_supported


model_name = "./Qwen2.5-14B-Instruct-abliterated-v2"
data_path = "./微调语句/cara/merged_inlong.jsonl"
output_dir = "./adaptor/character_epoch_3_3e-5-v2"

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
    r=64,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=128,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)


# 处理Messages 格式数据
SYSTEM_PROMPT = "你是Grimoire：傲娇的天才少女程序员。技术分析须严谨毒舌，日常交流自然嫌弃。[ROUTER]和[TOOL]为系统上下文。"


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
        print(text)
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
    packing=True,
    response_only_loss=True,
    args=TrainingArguments(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        warmup_steps=10,
        num_train_epochs=3,
        learning_rate=3e-5,
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
print(f"character 适配器已安全落地在：{output_dir}")