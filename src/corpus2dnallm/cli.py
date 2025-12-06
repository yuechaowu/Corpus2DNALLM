#!/usr/bin/env python3
"""
Corpus2DNALLM - 基因组数据转换为DNA语言模型训练数据的CLI工具

这个工具提供了完整的基因组数据处理流程，包括：
1. 基因组文件检查和大小统计
2. 准备基因组语料库
3. 训练BPE分词器
4. 生成分词器配置文件
"""

import argparse
import sys
import os
from pathlib import Path

# 导入重构后的模块
from . import genome_size
from . import corpus_prep
from . import tokenizer_train
from . import config_gen


def create_parser():
    """创建主命令行解析器"""
    parser = argparse.ArgumentParser(
        prog='corpus2dnallm',
        description='将基因组数据转换为DNA语言模型训练数据的工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  corpus2dnallm prepare-genome --genomes-info genomes.txt --masked masked/ --unmasked unmasked/ --output output/
  corpus2dnallm all --genomes-info genomes.txt --masked masked/ --unmasked unmasked/ --output output/

更多信息请访问: https://github.com/yourusername/Corpus2DNALLM
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # prepare-genome 子命令
    genome_parser = subparsers.add_parser(
        'prepare-genome',
        help='检查基因组文件并生成大小统计'
    )
    genome_parser.add_argument(
        '--genomes-info-path',
        type=str,
        required=True,
        help='包含基因组名称和类型的TSV文件路径'
    )
    genome_parser.add_argument(
        '--masked-dir',
        type=str,
        required=True,
        help='hardmasked基因组文件所在目录'
    )
    genome_parser.add_argument(
        '--unmasked-dir',
        type=str,
        required=True,
        help='unmasked基因组文件所在目录'
    )
    genome_parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='输出文件目录'
    )

    # prepare-corpus 子命令
    corpus_parser = subparsers.add_parser(
        'prepare-corpus',
        help='准备基因组语料库'
    )
    corpus_parser.add_argument(
        '--genomes-info-path',
        type=str,
        required=True,
        help='包含基因组名称和类型的TSV文件路径'
    )
    corpus_parser.add_argument(
        '--unmasked-dir',
        type=str,
        required=True,
        help='unmasked基因组文件目录'
    )
    corpus_parser.add_argument(
        '--split-mask-dir',
        type=str,
        required=True,
        help='分割的masked基因组文件目录'
    )
    corpus_parser.add_argument(
        '--genome-size-file',
        type=str,
        required=True,
        help='包含基因组大小信息的文件路径'
    )
    corpus_parser.add_argument(
        '--output-file',
        type=str,
        required=True,
        help='输出语料库文件路径'
    )
    corpus_parser.add_argument(
        '--max-seq-length',
        type=int,
        default=4000,
        help='拆分序列的最大长度 (默认: 4000)'
    )
    corpus_parser.add_argument(
        '--genome-split-size',
        type=int,
        default=500,
        help='拆分Unmasked基因组的最大长度(MB) (默认: 500)'
    )

    # train-tokenizer 子命令
    tokenizer_parser = subparsers.add_parser(
        'train-tokenizer',
        help='训练BPE分词器'
    )
    tokenizer_parser.add_argument(
        '--input-file',
        type=str,
        required=True,
        help='包含训练文本数据的输入文件路径'
    )
    tokenizer_parser.add_argument(
        '--model-prefix',
        type=str,
        required=True,
        help='生成模型文件的前缀'
    )
    tokenizer_parser.add_argument(
        '--vocab-size',
        type=int,
        default=8192,
        help='词汇表大小 (默认: 8192)'
    )
    tokenizer_parser.add_argument(
        '--model-type',
        type=str,
        default='bpe',
        choices=['bpe', 'unigram', 'word', 'char'],
        help='模型类型 (默认: bpe)'
    )
    tokenizer_parser.add_argument(
        '--num-threads',
        type=int,
        default=4,
        help='训练时使用的线程数 (默认: 4)'
    )

    # generate-config 子命令
    config_parser = subparsers.add_parser(
        'generate-config',
        help='生成分词器配置文件'
    )
    config_parser.add_argument(
        '--model-path',
        type=str,
        required=True,
        help='BPE模型文件路径'
    )
    config_parser.add_argument(
        '--example-config-file',
        type=str,
        required=True,
        help='示例tokenizer配置文件路径'
    )
    config_parser.add_argument(
        '--example-tokenizer-file',
        type=str,
        required=True,
        help='示例tokenizer文件路径'
    )
    config_parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='输出目录 (默认: 当前目录)'
    )
    config_parser.add_argument(
        '--special-token-file',
        type=str,
        help='特殊标记JSON文件路径 (可选)'
    )

    # all 子命令 - 执行完整流程
    all_parser = subparsers.add_parser(
        'all',
        help='执行完整的基因组数据处理流程'
    )
    all_parser.add_argument(
        '--genomes-info-path',
        type=str,
        required=True,
        help='包含基因组名称和类型的TSV文件路径'
    )
    all_parser.add_argument(
        '--masked-dir',
        type=str,
        required=True,
        help='hardmasked基因组文件所在目录'
    )
    all_parser.add_argument(
        '--unmasked-dir',
        type=str,
        required=True,
        help='unmasked基因组文件所在目录'
    )
    all_parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='输出文件目录'
    )
    all_parser.add_argument(
        '--max-seq-length',
        type=int,
        default=4000,
        help='拆分序列的最大长度 (默认: 4000)'
    )
    all_parser.add_argument(
        '--genome-split-size',
        type=int,
        default=500,
        help='拆分Unmasked基因组的最大长度(MB) (默认: 500)'
    )
    all_parser.add_argument(
        '--vocab-size',
        type=int,
        default=8192,
        help='词汇表大小 (默认: 8192)'
    )
    all_parser.add_argument(
        '--model-type',
        type=str,
        default='bpe',
        choices=['bpe', 'unigram', 'word', 'char'],
        help='模型类型 (默认: bpe)'
    )
    all_parser.add_argument(
        '--num-threads',
        type=int,
        default=4,
        help='训练时使用的线程数 (默认: 4)'
    )

    return parser


def run_prepare_genome(args):
    """执行基因组准备步骤"""
    print("开始基因组文件检查和大小统计...")

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 调用原有功能
    if genome_size.check_genome_files(
        args.genomes_info_path,
        args.masked_dir,
        args.unmasked_dir
    ):
        genome_size.write_genome_sizes(
            args.genomes_info_path,
            args.unmasked_dir,
            args.output_dir
        )

        split_mask_dir = os.path.join(args.output_dir, 'hardmask_split')
        genome_size.split_hardmask_genome(args.masked_dir, args.output_dir)

        print(f"基因组统计完成，结果保存在: {args.output_dir}")
        return True
    else:
        print("错误: 部分基因组文件缺失，请检查")
        return False


def run_prepare_corpus(args):
    """执行语料库准备步骤"""
    print("开始准备基因组语料库...")

    # 调用新的模块化功能
    corpus_prep.prepare_genome_corpus(
        args.genomes_info_path,
        args.unmasked_dir,
        args.split_mask_dir,
        args.genome_size_file,
        args.output_file,
        args.max_seq_length,
        args.genome_split_size
    )

    print(f"语料库准备完成，结果保存在: {args.output_file}")


def run_train_tokenizer(args):
    """执行分词器训练步骤"""
    print("开始训练BPE分词器...")

    # 调用新的模块化功能
    success = tokenizer_train.train_sentencepiece_model(
        args.input_file,
        args.model_prefix,
        args.vocab_size,
        args.model_type,
        args.num_threads
    )

    if success:
        print(f"分词器训练完成，模型文件保存在: {args.model_prefix}")

        # 验证模型
        test_sequences = ["ATCGATCGATCG", "GCTAGCTAGCTA"]
        tokenizer_train.validate_model(f"{args.model_prefix}.model", test_sequences)
    else:
        print("分词器训练失败")
        sys.exit(1)


def run_generate_config(args):
    """执行配置生成步骤"""
    print("开始生成分词器配置文件...")

    # 调用新的模块化功能
    success = config_gen.generate_all_config_files(
        args.model_path,
        args.example_config_file,
        args.example_tokenizer_file,
        args.output_dir,
        args.special_token_file
    )

    if success:
        print(f"配置文件生成完成，结果保存在: {args.output_dir}")
    else:
        print("配置文件生成失败")
        sys.exit(1)


def run_all(args):
    """执行完整流程"""
    print("开始执行完整的基因组数据处理流程...")

    # 步骤1: 准备基因组
    if not run_prepare_genome(args):
        sys.exit(1)

    # 设置中间文件路径
    genome_size_file = os.path.join(args.output_dir, 'genome_sizes.txt')
    split_mask_dir = os.path.join(args.output_dir, 'hardmask_split')
    corpus_file = os.path.join(args.output_dir, 'genome_corpus.txt')
    model_prefix = os.path.join(args.output_dir, 'dna_tokenizer')

    # 步骤2: 准备语料库
    corpus_args = argparse.Namespace(
        genomes_info_path=args.genomes_info_path,
        unmasked_dir=args.unmasked_dir,
        split_mask_dir=split_mask_dir,
        genome_size_file=genome_size_file,
        output_file=corpus_file,
        max_seq_length=args.max_seq_length,
        genome_split_size=args.genome_split_size
    )
    run_prepare_corpus(corpus_args)

    # 步骤3: 训练分词器
    tokenizer_args = argparse.Namespace(
        input_file=corpus_file,
        model_prefix=model_prefix,
        vocab_size=args.vocab_size,
        model_type=args.model_type,
        num_threads=args.num_threads
    )
    run_train_tokenizer(tokenizer_args)

    # 步骤4: 生成配置文件
    config_args = argparse.Namespace(
        model_path=f"{model_prefix}.model",
        special_token_file=None,  # 可选参数
        example_config_file=None,  # 需要用户提供
        example_tokenizer_file=None,  # 需要用户提供
        output_dir=args.output_dir
    )

    # 如果示例文件不存在，跳过配置生成步骤
    if config_args.example_config_file is None:
        print("警告: 未提供示例配置文件，跳过配置文件生成步骤")
        print("请使用 'corpus2dnallm generate-config --help' 查看如何手动生成配置文件")
    else:
        run_generate_config(config_args)

    print(f"完整流程执行完成！所有结果保存在: {args.output_dir}")


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'prepare-genome':
            run_prepare_genome(args)
        elif args.command == 'prepare-corpus':
            run_prepare_corpus(args)
        elif args.command == 'train-tokenizer':
            run_train_tokenizer(args)
        elif args.command == 'generate-config':
            run_generate_config(args)
        elif args.command == 'all':
            run_all(args)
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()