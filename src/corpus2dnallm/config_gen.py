"""
分词器配置生成模块

这个模块提供了从SentencePiece模型生成HuggingFace Transformers兼容配置文件的功能。
"""

import json
import sentencepiece as spm
import os


def extract_vocab_and_merges(model_path, output_dir):
    """
    从SentencePiece模型中提取词汇表和合并规则

    Args:
        model_path (str): SentencePiece模型文件路径
        output_dir (str): 输出目录

    Returns:
        bool: 是否成功
    """
    try:
        # 加载SentencePiece模型
        sp = spm.SentencePieceProcessor()
        sp.load(model_path)

        # 提取词汇表
        vocab = {}
        merges = []
        for i in range(sp.get_piece_size()):
            piece = sp.id_to_piece(i)
            score = sp.get_score(i)

            # 跳过特殊token的合并规则
            if piece not in ['<unk>', '<s>', '</s>', '<pad>']:
                vocab[piece] = i
                # 对于BPE，分数表示合并的优先级
                if '▁' not in piece and len(piece) > 1:
                    merges.append(f"{piece} {score:.6f}")

        # 写入词汇表文件
        vocab_file = os.path.join(output_dir, 'vocab.json')
        with open(vocab_file, 'w', encoding='utf-8') as f:
            json.dump(vocab, f, ensure_ascii=False, indent=2)

        # 写入合并规则文件
        merges_file = os.path.join(output_dir, 'merges.txt')
        with open(merges_file, 'w', encoding='utf-8') as f:
            f.write("#version: 0.2\n")
            for merge in merges:
                f.write(f"{merge}\n")

        print(f"词汇表文件已生成: {vocab_file}")
        print(f"合并规则文件已生成: {merges_file}")
        return True

    except Exception as e:
        print(f"提取词汇表和合并规则失败: {e}")
        return False


def generate_tokenizer_config(model_path, example_config_file, output_dir,
                             special_token_file=None):
    """
    生成tokenizer配置文件

    Args:
        model_path (str): SentencePiece模型文件路径
        example_config_file (str): 示例配置文件路径
        output_dir (str): 输出目录
        special_token_file (str): 特殊token文件路径(可选)

    Returns:
        bool: 是否成功
    """
    try:
        # 加载示例配置文件
        if os.path.exists(example_config_file):
            with open(example_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # 创建默认配置
            config = create_default_config()

        # 加载SentencePiece模型获取信息
        sp = spm.SentencePieceProcessor()
        sp.load(model_path)

        # 更新配置
        config.update({
            "vocab_size": sp.get_piece_size(),
            "model_max_length": 4096,  # 默认最大长度
            "tokenizer_class": "PreTrainedTokenizerFast",
            "auto_map": {
                "AutoTokenizer": ["tokenization_corpus2dnallm.Corpus2DNALLMTokenizer", "Corpus2DNALLMTokenizer"]
            }
        })

        # 处理特殊token
        special_tokens = {
            "unk_token": "<unk>",
            "bos_token": "<s>",
            "eos_token": "</s>",
            "pad_token": None,
            "mask_token": None,
            "sep_token": None,
            "cls_token": None
        }

        # 如果提供了特殊token文件，使用文件中的定义
        if special_token_file and os.path.exists(special_token_file):
            with open(special_token_file, 'r', encoding='utf-8') as f:
                file_special_tokens = json.load(f)
                special_tokens.update(file_special_tokens)

        # 更新配置中的特殊token
        config["unk_token"] = special_tokens["unk_token"]
        config["bos_token"] = special_tokens["bos_token"]
        config["eos_token"] = special_tokens["eos_token"]
        if special_tokens["pad_token"]:
            config["pad_token"] = special_tokens["pad_token"]

        # 写入配置文件
        config_file = os.path.join(output_dir, 'tokenizer_config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"Tokenizer配置文件已生成: {config_file}")
        return True

    except Exception as e:
        print(f"生成tokenizer配置文件失败: {e}")
        return False


def generate_tokenizer_json(model_path, example_tokenizer_file, output_dir,
                           special_token_file=None):
    """
    生成tokenizer.json文件

    Args:
        model_path (str): SentencePiece模型文件路径
        example_tokenizer_file (str): 示例tokenizer文件路径
        output_dir (str): 输出目录
        special_token_file (str): 特殊token文件路径(可选)

    Returns:
        bool: 是否成功
    """
    try:
        # 加载示例tokenizer文件
        if os.path.exists(example_tokenizer_file):
            with open(example_tokenizer_file, 'r', encoding='utf-8') as f:
                tokenizer_data = json.load(f)
        else:
            # 创建默认tokenizer结构
            tokenizer_data = create_default_tokenizer_data()

        # 更新模型配置
        model_path = os.path.abspath(model_path)
        tokenizer_data["model"]["model_path"] = model_path

        # 处理特殊token
        if special_token_file and os.path.exists(special_token_file):
            with open(special_token_file, 'r', encoding='utf-8') as f:
                special_tokens = json.load(f)
            update_special_tokens_in_tokenizer(tokenizer_data, special_tokens)

        # 写入tokenizer.json文件
        tokenizer_file = os.path.join(output_dir, 'tokenizer.json')
        with open(tokenizer_file, 'w', encoding='utf-8') as f:
            json.dump(tokenizer_data, f, ensure_ascii=False, indent=2)

        print(f"Tokenizer文件已生成: {tokenizer_file}")
        return True

    except Exception as e:
        print(f"生成tokenizer.json文件失败: {e}")
        return False


def create_default_config():
    """
    创建默认的tokenizer配置

    Returns:
        dict: 默认配置
    """
    return {
        "clean_up_tokenization_spaces": True,
        "model_max_length": 4096,
        "padding_side": "right",
        "truncation_side": "right",
        "use_fast": True,
        "tokenizer_class": "PreTrainedTokenizerFast"
    }


def create_default_tokenizer_data():
    """
    创建默认的tokenizer数据结构

    Returns:
        dict: 默认tokenizer数据
    """
    return {
        "version": "1.0",
        "model": {
            "type": "SentencePieceBPE",
            "vocab": {},
            "merges": [],
            "unk_token": "<unk>",
            "continuing_subword_prefix": "▁",
            "max_input_chars_per_word": 100,
            "vocab_size": 8192
        },
        "pre_tokenizer": {
            "type": "Sequence",
            "pretokenizers": [
                {"type": "Metaspace", "replacement": "▁", "add_prefix_space": False}
            ]
        },
        "post_processor": {
            "type": "TemplateProcessing",
            "single": [
                {"SpecialToken": {"id": "<s>", "type_id": 0}},
                {"Sequence": {"id": "A", "type_id": 0}},
                {"SpecialToken": {"id": "</s>", "type_id": 0}}
            ],
            "pair": [
                {"SpecialToken": {"id": "<s>", "type_id": 0}},
                {"Sequence": {"id": "A", "type_id": 0}},
                {"SpecialToken": {"id": "</s>", "type_id": 0}},
                {"SpecialToken": {"id": "<s>", "type_id": 1}},
                {"Sequence": {"id": "B", "type_id": 1}},
                {"SpecialToken": {"id": "</s>", "type_id": 1}}
            ],
            "special_tokens": {
                "<s>": {"id": 1, "ids": [1], "tokens": ["<s>"]},
                "</s>": {"id": 2, "ids": [2], "tokens": ["</s>"]},
                "<unk>": {"id": 0, "ids": [0], "tokens": ["<unk>"]}
            }
        },
        "decoder": {
            "type": "Sequence",
            "decoders": [
                {"type": "Metaspace", "replacement": "▁", "add_prefix_space": False}
            ]
        },
        "added_tokens": []
    }


def update_special_tokens_in_tokenizer(tokenizer_data, special_tokens):
    """
    在tokenizer数据中更新特殊token

    Args:
        tokenizer_data (dict): tokenizer数据
        special_tokens (dict): 特殊token定义
    """
    # 更新模型中的特殊token
    if "unk_token" in special_tokens:
        tokenizer_data["model"]["unk_token"] = special_tokens["unk_token"]

    # 更新后处理器中的特殊token
    special_tokens_map = {
        "<s>": {"id": 1, "ids": [1], "tokens": ["<s>"]},
        "</s>": {"id": 2, "ids": [2], "tokens": ["</s>"]},
        "<unk>": {"id": 0, "ids": [0], "tokens": ["<unk>"]}
    }

    for token_name, token_info in special_tokens_map.items():
        if token_name in special_tokens or tokenizer_data["model"].get("unk_token") == token_name:
            tokenizer_data["post_processor"]["special_tokens"][token_name] = token_info

    # 更新added_tokens
    added_tokens = []
    for token_name in ["<s>", "</s>", "<unk>"]:
        if token_name in special_tokens or tokenizer_data["model"].get("unk_token") == token_name:
            added_tokens.append({
                "id": special_tokens_map[token_name]["id"],
                "content": token_name,
                "single_word": False,
                "lstrip": False,
                "rstrip": False,
                "normalized": False,
                "special": True
            })

    tokenizer_data["added_tokens"] = added_tokens


def generate_all_config_files(model_path, example_config_file, example_tokenizer_file,
                             output_dir, special_token_file=None):
    """
    生成所有配置文件

    Args:
        model_path (str): SentencePiece模型文件路径
        example_config_file (str): 示例配置文件路径
        example_tokenizer_file (str): 示例tokenizer文件路径
        output_dir (str): 输出目录
        special_token_file (str): 特殊token文件路径(可选)

    Returns:
        bool: 是否全部成功
    """
    success = True

    # 生成词汇表和合并规则
    success &= extract_vocab_and_merges(model_path, output_dir)

    # 生成tokenizer配置文件
    success &= generate_tokenizer_config(
        model_path, example_config_file, output_dir, special_token_file
    )

    # 生成tokenizer.json文件
    success &= generate_tokenizer_json(
        model_path, example_tokenizer_file, output_dir, special_token_file
    )

    return success