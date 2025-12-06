"""
基因组语料库准备模块

这个模块提供了从基因组文件中提取序列并准备训练语料库的功能。
"""

import os
import glob
import pyfastx
from glob import glob
import fnmatch
import numpy as np
import pandas as pd


def prepare_genome_corpus(genomes_info_path, unmasked_dir, split_mask_dir,
                         genome_size_file, output_file, max_length=4000,
                         genome_split_size=500):
    """
    准备基因组语料库

    Args:
        genomes_info_path (str): 包含基因组名称的文件路径
        unmasked_dir (str): unmasked基因组文件目录
        split_mask_dir (str): 分割的masked基因组文件目录
        genome_size_file (str): 包含基因组大小信息的文件路径
        output_file (str): 输出文件路径
        max_length (int): 拆分序列的最长长度，默认为4000
        genome_split_size (int): 拆分Unmasked基因组的最大长度(MB)，默认为500
    """
    # 读取基因组信息
    genome_df = pd.read_csv(genomes_info_path, sep='\t', index_col=0)
    # 保留原始大小写，但同时创建小写版本用于索引
    original_index = genome_df.index.copy()
    genome_df.index = genome_df.index.to_series().str.lower()

    # 读取基因组大小信息
    size_df = pd.read_csv(genome_size_file, sep='\t', index_col=0)

    # 打开输出文件
    with open(output_file, 'w') as outfile:
        for i, genome_name in enumerate(genome_df.index):
            genome_name_original = original_index[i]
            genome_type = genome_df.loc[genome_name, 'genome_type']
            genome_size = size_df.loc[genome_name, 'sum_len']
            genome_size_mb = genome_size / (1024 * 1024)  # 转换为MB

            print(f"处理基因组: {genome_name} (大小: {genome_size_mb:.2f} MB)")

            if genome_type == 'both':
                # 处理有masked和unmasked两种类型的基因组
                process_both_types(genome_name, genome_name_original, unmasked_dir, split_mask_dir,
                                  genome_size_mb, genome_split_size,
                                  max_length, outfile)
            else:
                # 只处理unmasked基因组
                process_unmasked_only(genome_name, genome_name_original, unmasked_dir,
                                    genome_size_mb, genome_split_size,
                                    max_length, outfile)


def process_both_types(genome_name, genome_name_original, unmasked_dir, split_mask_dir,
                      genome_size_mb, genome_split_size, max_length, outfile):
    """
    处理同时有masked和unmasked的基因组

    Args:
        genome_name (str): 基因组名称
        unmasked_dir (str): unmasked基因组文件目录
        split_mask_dir (str): 分割的masked基因组文件目录
        genome_size_mb (float): 基因组大小(MB)
        genome_split_size (int): 拆分阈值(MB)
        max_length (int): 最大序列长度
        outfile: 输出文件句柄
    """
    if genome_size_mb < genome_split_size:
        # 小基因组，使用全部unmasked序列
        print(f"  小基因组: 使用全部unmasked序列")
        process_unmasked_genome(genome_name, genome_name_original, unmasked_dir, max_length, outfile)
    else:
        # 大基因组，混合使用masked和unmasked
        print(f"  大基因组: 混合使用masked和unmasked序列")

        # 处理masked部分
        masked_file = find_split_mask_file(split_mask_dir, genome_name_original)
        if masked_file:
            masked_size = process_masked_genome(masked_file, max_length, outfile, 250)
            print(f"  处理了 {masked_size} MB masked序列")
        else:
            print(f"  警告: 未找到{genome_name}的masked文件")

        # 处理unmasked部分 (最多250MB)
        process_unmasked_genome(genome_name, genome_name_original, unmasked_dir, max_length, outfile, 250)


def process_unmasked_only(genome_name, genome_name_original, unmasked_dir, genome_size_mb,
                         genome_split_size, max_length, outfile):
    """
    处理只有unmasked的基因组

    Args:
        genome_name (str): 基因组名称
        unmasked_dir (str): unmasked基因组文件目录
        genome_size_mb (float): 基因组大小(MB)
        genome_split_size (int): 拆分阈值(MB)
        max_length (int): 最大序列长度
        outfile: 输出文件句柄
    """
    if genome_size_mb < genome_split_size:
        # 小基因组，使用全部序列
        print(f"  小基因组: 使用全部序列")
        process_unmasked_genome(genome_name, genome_name_original, unmasked_dir, max_length, outfile)
    else:
        # 大基因组，只使用部分序列
        print(f"  大基因组: 使用部分序列 ({genome_split_size} MB)")
        process_unmasked_genome(genome_name, genome_name_original, unmasked_dir, max_length,
                              outfile, genome_split_size)


def find_split_mask_file(split_mask_dir, genome_name):
    """
    查找分割的masked文件

    Args:
        split_mask_dir (str): 分割文件目录
        genome_name (str): 基因组名称（原始大小写）

    Returns:
        str: 文件路径，如果未找到返回None
    """
    # 尝试多种大小写变体
    name_variants = [
        genome_name,              # 原始名称
        genome_name.lower(),      # 小写版本
        genome_name.title(),      # 首字母大写
        genome_name.upper()       # 全大写
    ]

    for name in name_variants:
        pattern = f"{name}*_sp.txt"
        matches = glob(os.path.join(split_mask_dir, pattern))
        if matches:
            return matches[0]
    return None


def find_genome_file(directory, genome_name):
    """
    查找基因组文件

    Args:
        directory (str): 搜索目录
        genome_name (str): 基因组名称（原始大小写）

    Returns:
        str: 文件路径，如果未找到返回None
    """
    # 尝试多种大小写变体
    name_variants = [
        genome_name,              # 原始名称
        genome_name.lower(),      # 小写版本
        genome_name.title(),      # 首字母大写
        genome_name.upper()       # 全大写
    ]

    file_patterns = ["*.fa", "*.fasta", "*.fa.gz", "*.fasta.gz"]

    for name in name_variants:
        for pattern in file_patterns:
            full_pattern = f"{name}{pattern}"
            matches = glob(os.path.join(directory, full_pattern))
            if matches:
                return matches[0]
    return None


def process_unmasked_genome(genome_name, genome_name_original, unmasked_dir, max_length, outfile,
                           max_mb=None):
    """
    处理unmasked基因组文件

    Args:
        genome_name (str): 基因组名称
        unmasked_dir (str): unmasked文件目录
        max_length (int): 最大序列长度
        outfile: 输出文件句柄
        max_mb (float): 最大处理大小(MB)，None表示无限制
    """
    genome_file = find_genome_file(unmasked_dir, genome_name_original)
    if not genome_file:
        print(f"  警告: 未找到{genome_name}的unmasked文件")
        return 0

    print(f"  处理文件: {os.path.basename(genome_file)}")
    fa = pyfastx.Fasta(genome_file, build_index=True)

    total_chars = 0
    max_chars = max_mb * 1024 * 1024 if max_mb else float('inf')

    for seq in fa:
        sequence = str(seq.seq).upper()

        # 拆分序列
        for i in range(0, len(sequence), max_length):
            sub_seq = sequence[i:i + max_length]
            if len(sub_seq) >= 100:  # 过滤过短的序列
                print(sub_seq, file=outfile)
                total_chars += len(sub_seq)

            # 检查是否达到大小限制
            if total_chars >= max_chars:
                return total_chars / (1024 * 1024)  # 返回处理的MB数

    return total_chars / (1024 * 1024)


def process_masked_genome(masked_file, max_length, outfile, max_mb):
    """
    处理分割的masked基因组文件

    Args:
        masked_file (str): masked文件路径
        max_length (int): 最大序列长度
        outfile: 输出文件句柄
        max_mb (float): 最大处理大小(MB)

    Returns:
        float: 处理的MB数
    """
    total_chars = 0
    max_chars = max_mb * 1024 * 1024

    with open(masked_file, 'r') as f:
        for line in f:
            sequence = line.strip().upper()
            if len(sequence) >= 100:  # 过滤过短的序列
                # 拆分序列
                for i in range(0, len(sequence), max_length):
                    sub_seq = sequence[i:i + max_length]
                    print(sub_seq, file=outfile)
                    total_chars += len(sub_seq)

            # 检查是否达到大小限制
            if total_chars >= max_chars:
                break

    return total_chars / (1024 * 1024)