import json
import argparse
import os
import subprocess


def BPE_model_convert_to_merge_vocab_file(model_path, output_dir):
    """
    从指定的SentencePiece模型中提取词汇表和合并规则，并将它们保存到指定的文件中。

    参数:
    - model_path: SentencePiece模型的路径。
    - output_dir: 输出目录。
    """

    vocab_output_dir = os.path.join(output_dir, 'vocab.json')

    merges_output_dir = os.path.join(output_dir, 'merges.txt')

    command = f"python sentencepiece_extractor.py --provider sentencepiece --model {model_path} --vocab-output-path {vocab_output_dir} --merges-output-path {merges_output_dir}"

    # 使用subprocess运行命令
    try:
        subprocess.run(command, shell=True, check=True)
        print("merge and vocab files have been successfully extracted.")
    except subprocess.CalledProcessError as e:
        print(f"Failed: {e}")
    

def update_tokenizer_files(special_token_file, example_config_file, example_tokenizer_file, output_dir):

    vocab_file = os.path.join(output_dir, 'vocab.json')

    merge_file = os.path.join(output_dir, 'merges.txt')

    # 加载vocab文件
    with open(vocab_file, 'r', encoding='utf-8') as f:
        vocab = json.load(f)

    # 读取并处理merges文件
    merge_list = []
    with open(merge_file, 'r', encoding='utf-8') as f:
        for line in f:
            merge_list.append(line.strip())

    # 加载特殊标记文件，如果不存在则使用默认的特殊标记
    if os.path.exists(special_token_file):
        with open(special_token_file, 'r', encoding='utf-8') as f:
            special_token = json.load(f)
    else:
        special_token = {
            '<|endoftext|>': 0,
            '<|padding|>': 1,
        }

    # 加载示例配置和分词器文件
    with open(example_config_file, 'r', encoding='utf-8') as f:
        example_config = json.load(f)

    with open(example_tokenizer_file, 'r', encoding='utf-8') as f:
        example_tokenizer = json.load(f)

    # 修改配置文件的added_tokens_decoder属性
    added_tokens_decoder = {}
    for i, v in enumerate(special_token):
        added_tokens_decoder[str(i)] = {
            'content': v,
            'lstrip': False,
            'rstrip': False,
            'single_word': False,
            'special': True
        }
    example_config['added_tokens_decoder'] = added_tokens_decoder

    # 将分词器文件的merges属性替换为新的merges
    example_tokenizer['model']['merges'] = merge_list

    # 修改分词器文件的added_tokens属性
    added_tokens = []
    for v in special_token:
        added_tokens.append({
            'id': special_token[v],
            'content': v,
            'single_word': False,
            'lstrip': False,
            'rstrip': False,
            'normalized': False,
            'special': True
        })
    example_tokenizer['added_tokens'] = added_tokens

    # 将分词器文件的vocab属性替换为新的vocab，并将 special_token 添加到 vocab 中最后
    # vocab_info = {}
    # for i, v in enumerate(special_token):
    #     vocab_info[v] = i

    # i = 0
    # for v in vocab:
    #     if v.startswith("<"):
    #         continue
    #     vocab_info[v] = i + len(special_token)
    #     i += 1
    # example_tokenizer['model']['vocab'] = vocab_info

    vocab_info = {}

    index = 0
    for v in vocab:
        if v.startswith("<"):
            continue
        vocab_info[v] = index
        index += 1

    for i, v in enumerate(special_token):
        vocab_info[v] = i + index

    example_tokenizer['model']['vocab'] = vocab_info


    # 设置输出文件的路径
    output_config_file = os.path.join(output_dir, 'tokenizer_config.json')
    output_tokenizer_file = os.path.join(output_dir, 'tokenizer.json')

    # 写入修改后的配置和分词器文件
    with open(output_config_file, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, ensure_ascii=False, indent=4)

    with open(output_tokenizer_file, 'w', encoding='utf-8') as f:
        json.dump(example_tokenizer, f, ensure_ascii=False, indent=4)

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='extract merges and vocab file from BPE model, Update tokenizer files with special tokens and vocab.')

    # 添加命令行参数
    parser.add_argument('--model', type=str, required=True, help='Path to the BPE model.')
    parser.add_argument('--special_token_file', type=str, default='json.file',required=False, help='Path to the special token file, JSON file')
    parser.add_argument('--example_config_file', type=str, required=True, help='Path to the example tokenizer config file.')
    parser.add_argument('--example_tokenizer_file', type=str, required=True, help='Path to the example tokenizer file.')
    parser.add_argument('--output_dir', type=str, default='.', help='Path to the output dir.')

    args = parser.parse_args()

    # BPE_model_convert_to_merge_vocab_file
    BPE_model_convert_to_merge_vocab_file(args.model, args.output_dir)

    # 调用update_tokenizer_files函数
    update_tokenizer_files(args.special_token_file, args.example_config_file, args.example_tokenizer_file, args.output_dir)

if __name__ == "__main__":
    main()