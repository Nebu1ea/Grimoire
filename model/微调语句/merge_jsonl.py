import json

input_files = [
    "cara/long_normal_one.jsonl",
    "cara/FC_to_C_fixed_long.jsonl",
    "./code_to_chinese_sorted.jsonl"
]
output_file = "cara/merged.jsonl"

seen = set()
count = 0

with open(output_file, "w", encoding="utf-8") as outfile:
    for file in input_files:
        with open(file, "r", encoding="utf-8") as infile:
            for line in infile:
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                    key = json.dumps(obj, sort_keys=True)

                    if key in seen:
                        continue
                    seen.add(key)

                    outfile.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    count += 1

                except Exception as e:
                    print(f"跳过错误行 in {file}: {e}")

print(f"完成，共写入 {count} 条数据")