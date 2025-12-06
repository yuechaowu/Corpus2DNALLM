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
    genome_df.index = genome_df.index.to_series().str.lower()

    for genome_name in genome_df.index:
        # 定义基因组文件的匹配模式
        file_patterns = [f"{genome_name}*.fa.gz", f"{genome_name}*.fasta.gz",
                        f"{genome_name}*.fasta", f"{genome_name}*.fa"]

        # 获取基因组类型
        genome_type = genome_df.loc[genome_name, 'genome_type']

        if genome_type == 'both':
            # 检查hardmasked基因组文件是否存在
            if not any(fnmatch.fnmatch(file.lower(), pattern) for pattern in file_patterns
                      for file in os.listdir(masked_dir)):
                print(f"{genome_name} hardmasked not existed")
                FLAG = False
            # 检查unmasked基因组文件是否存在
            if not any(fnmatch.fnmatch(file.lower(), pattern) for pattern in file_patterns
                      for file in os.listdir(unmasked_dir)):
                print(f"{genome_name} unmasked not existed")
                FLAG = False
        else:
            # 检查unmasked基因组文件是否存在
            if not any(fnmatch.fnmatch(file.lower(), pattern) for pattern in file_patterns
                      for file in os.listdir(unmasked_dir)):
                print(f"{genome_name} unmasked not existed")
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
        genomes_info_path (str): 包含基因组信息的Excel文件路径。
        unmasked_dir (str): unmasked基因组文件所在的目录。
        output_dir (str): 输出文件的路径。
    """
    output_file = os.path.join(output_dir, 'genome_sizes.txt')

    # 打开输出文件并准备写入表头
    with open(output_file, 'w') as outfile:
        print('file', 'format', 'type', 'num_seqs', 'sum_len', 'min_len',
              'avg_len', 'max_len', sep='\t', file=outfile)

        # 读取包含基因组信息的Excel文件
        genome_df = pd.read_csv(genomes_info_path, sep='\t', index_col=0)
        genome_df.index = genome_df.index.to_series().str.lower()

        file_patterns = ["fa", 'fasta', 'fa.gz', 'fasta.gz']

        # 遍历所有基因组名称
        for genome_name in genome_df.index:
            # 遍历所有可能的文件后缀模式
            for pattern in file_patterns:
                # 构建文件路径
                path = os.path.join(unmasked_dir, f"{genome_name}*{pattern}")

                # 检查是否存在符合条件的文件
                if len(glob(path)) > 0:
                    # 获取符合条件的第一个文件路径
                    fasta_file = glob(path)[0]
                    break

            # 计算该FASTA文件的统计信息
            result = fasta_stats(fasta_file)
            # 将统计信息写入输出文件
            print(genome_name, 'FASTA', 'DNA', result['num_seqs'],
                  result['sum_len'], result['min_len'], result['avg_len'],
                  result['max_len'], sep='\t', file=outfile)


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