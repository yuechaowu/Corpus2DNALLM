"""
BPE分词器训练模块

这个模块提供了使用SentencePiece训练BPE分词器的功能。
"""

import sentencepiece as spm
import logging


def train_sentencepiece_model(input_file, model_prefix, vocab_size=8192,
                             model_type='bpe', num_threads=4):
    """
    训练SentencePiece模型的函数。

    Args:
        input_file (str): 训练数据文件路径
        model_prefix (str): 输出模型文件的前缀
        vocab_size (int): 词汇表大小，默认8192
        model_type (str): 模型类型，默认'bpe'
        num_threads (int): 训练线程数，默认4

    Returns:
        bool: 训练是否成功
    """
    try:
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # 使用SentencePieceTrainer的train方法训练模型
        spm.SentencePieceTrainer.train(
            input=input_file,             # 指定输入文件
            model_prefix=model_prefix,    # 指定输出模型文件的前缀
            vocab_size=vocab_size,        # 指定词汇表大小
            model_type=model_type,        # 指定模型类型
            num_threads=num_threads,      # 指定训练时使用的线程数
            input_format="text",          # 指定输入文件格式为文本
            add_dummy_prefix=False,       # 指定是否添加空格前缀
            # 其他可选参数
            shuffle_input_sentence=True,  # 随机打乱输入句子
            max_sentence_length=4192,     # 最大句子长度
            # 字符覆盖
            character_coverage=0.9995,
            # 训练参数
            num_sub_iterations=2,
            max_sentencepiece_length=16,
            split_by_unicode_script=True,
            split_by_number=True,
            split_by_whitespace=False,
            treat_whitespace_as_suffix=False,
            allow_whitespace_only_pieces=True,
            # 控制特殊token
            unk_id=0,
            bos_id=1,
            eos_id=2,
            pad_id=-1,  # 不使用padding token
            # 其他设置
            hard_vocab_limit=True,
            use_all_vocab=False,
        )

        # 训练成功后记录日志
        logger.info(f"模型训练成功完成。模型前缀: {model_prefix}")
        logger.info(f"词汇表大小: {vocab_size}")
        logger.info(f"模型类型: {model_type}")

        return True

    except Exception as e:
        # 捕获并记录训练模型时发生的任何异常
        logger.error(f"模型训练失败: {e}")
        return False


def validate_model(model_path, test_sequences=None):
    """
    验证训练好的模型

    Args:
        model_path (str): 模型文件路径
        test_sequences (list): 测试序列列表

    Returns:
        bool: 验证是否成功
    """
    try:
        # 加载模型
        sp = spm.SentencePieceProcessor()
        sp.load(model_path)

        print(f"模型验证成功:")
        print(f"- 词汇表大小: {sp.get_piece_size()}")
        print(f"- 未知token ID: {sp.unk_id()}")
        print(f"- 开始token ID: {sp.bos_id()}")
        print(f"- 结束token ID: {sp.eos_id()}")

        # 如果提供了测试序列，进行编码解码测试
        if test_sequences:
            print("\n测试编码/解码:")
            for i, seq in enumerate(test_sequences[:3]):  # 只测试前3个
                try:
                    encoded = sp.encode(seq, out_type=int)
                    decoded = sp.decode(encoded)
                    print(f"原始: {seq[:50]}...")
                    print(f"编码: {encoded[:10]}...")  # 只显示前10个token
                    print(f"解码: {decoded[:50]}...")
                    print(f"匹配: {seq == decoded}")
                    print("-" * 40)
                except Exception as e:
                    print(f"序列 {i} 测试失败: {e}")

        return True

    except Exception as e:
        print(f"模型验证失败: {e}")
        return False


def get_vocab_info(model_path):
    """
    获取词汇表信息

    Args:
        model_path (str): 模型文件路径

    Returns:
        dict: 词汇表信息
    """
    try:
        sp = spm.SentencePieceProcessor()
        sp.load(model_path)

        vocab_info = {
            'vocab_size': sp.get_piece_size(),
            'unk_id': sp.unk_id(),
            'bos_id': sp.bos_id(),
            'eos_id': sp.eos_id(),
            'pad_id': sp.pad_id() if sp.pad_id() >= 0 else None
        }

        # 获取前几个词汇表示例子
        sample_vocab = []
        for i in range(min(20, sp.get_piece_size())):
            piece = sp.id_to_piece(i)
            score = sp.get_score(i)
            sample_vocab.append((i, piece, score))

        vocab_info['sample_vocab'] = sample_vocab

        return vocab_info

    except Exception as e:
        print(f"获取词汇表信息失败: {e}")
        return None