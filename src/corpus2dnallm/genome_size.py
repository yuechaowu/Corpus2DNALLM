"""
基因组文件检查和大小统计模块

这个模块提供了检查基因组文件存在性和计算统计信息的功能。
"""

import os
import pandas as pd
from Bio import SeqIO
import pyfastx
from glob import glob
import re
import fnmatch
import gzip


def check_genome_files(genomes_info_path, masked_dir, unmasked_dir):
    """
    检查基因组文件是否存在。

    Args:
        genomes_info_path (str): 包含基因组信息的txt文件路径。
        masked_dir (str): hardmasked基因组文件所在的目录。
        unmasked_dir (str): unmasked基因组文件所在的目录。

    Returns:
        bool: 所有文件是否存在
    """
    FLAG = True

    # 读取基因组信息文件
    genome_df = pd.read_csv(genomes_info_path, sep='\t', index_col=0)
    # 保留原始大小写，但同时创建小写版本用于匹配
    original_index = genome_df.index.copy()
    genome_df.index = genome_df.index.to_series().str.lower()

    for i, genome_name_lower in enumerate(genome_df.index):
        genome_name_original = original_index[i]
        # 获取基因组类型
        genome_type = genome_df.loc[genome_name_lower, 'genome_type']

        # 定义基因组文件的匹配模式（考虑大小写变体）
        def find_genome_file(directory):
            """在目录中查找基因组文件，考虑不同的大小写变体"""
            file_patterns = ["fa", 'fasta', 'fa.gz', 'fasta.gz']

            # 尝试原始名称和不同的大小写变体
            name_variants = [
                genome_name_original,  # 原始名称
                genome_name_lower,     # 小写版本
                genome_name_lower.title(),  # 首字母大写
                genome_name_lower.upper()   # 全大写
            ]

            for name in name_variants:
                for pattern in file_patterns:
                    if pattern.endswith('.gz'):
                        base_pattern = pattern[:-3]  # 移除.gz
                        path_pattern = f"{name}*.{base_pattern}.gz"
                    else:
                        path_pattern = f"{name}*.{pattern}"

                    matches = glob(os.path.join(directory, path_pattern))
                    if matches:
                        return True
            return False

        if genome_type == 'both':
            # 检查hardmasked基因组文件是否存在
            if not find_genome_file(masked_dir):
                print(f"{genome_name_original} hardmasked not existed")
                FLAG = False
            # 检查unmasked基因组文件是否存在
            if not find_genome_file(unmasked_dir):
                print(f"{genome_name_original} unmasked not existed")
                FLAG = False
        else:
            # 检查unmasked基因组文件是否存在
            if not find_genome_file(unmasked_dir):
                print(f"{genome_name_original} unmasked not existed")
                FLAG = False

    return FLAG


def fasta_stats(fasta_file):
    """
    计算FASTA文件的统计信息。

    Args:
        fasta_file (str): FASTA文件的路径。

    Returns:
        dict: 包含统计信息的字典。
    """
    total_bases = 0
    num_sequences = 0
    min_length = float('inf')
    max_length = 0
    lengths = []

    # 使用Biopython的SeqIO模块解析FASTA文件
    if fasta_file.endswith('.gz') or fasta_file.endswith('.gzip'):
        with gzip.open(fasta_file, "rt") as handle:
            for record in SeqIO.parse(handle, 'fasta'):
                seq_length = len(record.seq)
                total_bases += seq_length
                num_sequences += 1
                min_length = min(min_length, seq_length)
                max_length = max(max_length, seq_length)
                lengths.append(seq_length)
    else:
        for record in SeqIO.parse(fasta_file, 'fasta'):
            seq_length = len(record.seq)
            total_bases += seq_length
            num_sequences += 1
            min_length = min(min_length, seq_length)
            max_length = max(max_length, seq_length)
            lengths.append(seq_length)

    average_length = int(round(total_bases / num_sequences, 0))

    return {
        'sum_len': total_bases,
        'num_seqs': num_sequences,
        'min_len': min_length,
        'max_len': max_length,
        'avg_len': average_length
    }


def write_genome_sizes(genomes_info_path, unmasked_dir, output_dir):
    """
    计算并写入基因组大小的统计信息。

    参数:
        genomes_info_path (str): 包含基因组信息的TSV文件路径。
        unmasked_dir (str): unmasked基因组文件所在的目录。
        output_dir (str): 输出文件的路径。
    """
    output_file = os.path.join(output_dir, 'genome_sizes.txt')

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 打开输出文件并准备写入表头
    with open(output_file, 'w') as outfile:
        print('file', 'format', 'type', 'num_seqs', 'sum_len', 'min_len',
              'avg_len', 'max_len', sep='\t', file=outfile)

        # 读取包含基因组信息的TSV文件
        try:
            genome_df = pd.read_csv(genomes_info_path, sep='\t', index_col=0)
            # 保留原始大小写，但同时创建小写版本用于匹配
            original_index = genome_df.index.copy()
            genome_df.index = genome_df.index.to_series().str.lower()
        except Exception as e:
            print(f"错误: 无法读取基因组信息文件 {genomes_info_path}: {e}")
            return

        file_patterns = ["fa", 'fasta', 'fa.gz', 'fasta.gz']

        # 遍历所有基因组名称
        for i, genome_name in enumerate(genome_df.index):
            genome_name_original = original_index[i]
            fasta_file = None  # 初始化变量

            # 尝试多种大小写变体查找基因组文件
            name_variants = [
                genome_name_original,  # 原始名称
                genome_name,           # 小写版本
                genome_name.title(),   # 首字母大写
                genome_name.upper()    # 全大写
            ]

            # 遍历所有可能的文件后缀模式
            for pattern in file_patterns:
                if pattern.endswith('.gz'):
                    base_pattern = pattern[:-3]  # 移除.gz
                    path_pattern = f"*.{base_pattern}.gz"
                else:
                    path_pattern = f"*.{pattern}"

                # 尝试每个名称变体
                for name in name_variants:
                    full_pattern = f"{name}{path_pattern}"
                    matches = glob(os.path.join(unmasked_dir, full_pattern))
                    if matches:
                        # 获取符合条件的第一个文件路径
                        fasta_file = matches[0]
                        print(f"找到基因组文件: {os.path.basename(fasta_file)}")
                        break

                if fasta_file is not None:
                    break  # 找到文件，跳出循环

            # 检查是否找到了文件
            if fasta_file is None:
                print(f"警告: 未找到 {genome_name_original} 的基因组文件，跳过处理")
                continue

            # 验证文件是否可读
            if not os.access(fasta_file, os.R_OK):
                print(f"警告: 无法读取文件 {fasta_file}，跳过处理")
                continue

            try:
                # 计算该FASTA文件的统计信息
                result = fasta_stats(fasta_file)

                # 将统计信息写入输出文件
                print(genome_name, 'FASTA', 'DNA', result['num_seqs'],
                      result['sum_len'], result['min_len'], result['avg_len'],
                      result['max_len'], sep='\t', file=outfile)

                print(f"成功处理 {genome_name}: {result['num_seqs']} 条序列, "
                      f"总长度 {result['sum_len']:,} bp")

            except Exception as e:
                print(f"错误: 处理文件 {fasta_file} 时出错: {e}")
                continue

    print(f"基因组统计信息已保存到: {output_file}")


def split_hardmask_genome(masked_dir, out_dir):
    """
    拆分hardmasked基因组文件，按N区域分割序列。

    Args:
        masked_dir (str): hardmasked基因组文件目录
        out_dir (str): 输出目录
    """
    # 列出所有.fa文件
    filenames = (glob(os.path.join(masked_dir, '*.fa')) +
                glob(os.path.join(masked_dir, '*.fasta')) +
                glob(os.path.join(masked_dir, '*.gz')) +
                glob(os.path.join(masked_dir, '*.gzip')))

    # 创建输出目录
    out_dir = os.path.join(out_dir, 'hardmask_split')
    os.makedirs(out_dir, exist_ok=True)

    for filename in filenames:
        # 创建pyfastx Fasta对象
        fa = pyfastx.Fasta(filename, build_index=True, uppercase=True)

        # 生成输出文件名
        outfilename = (os.path.join(out_dir, os.path.basename(filename))
                      .replace('.fa', '_sp.txt')
                      .replace('.fasta', '_sp.txt')
                      .replace('.fa.gz', '_sp.txt')
                      .replace('.fasta.gz', '_sp.txt'))

        # 打开输出文件
        with open(outfilename, 'w') as outio:
            for seq in fa:
                sequence = seq.seq
                seqlist = re.split(r'[N]+', sequence)

                for seq_in_list in seqlist:
                    if seq_in_list:  # 只输出非空序列
                        print(seq_in_list, file=outio)