import os
import pandas as pd
from Bio import SeqIO
import argparse
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
    """
    # !这里判断时候有些基因组文件只有 unmask 文件，没有 hardmasked 文件
    # 标记基因组文件是否全部存在的标志
    #!这里判断时候有些基因组文件只有 unmask 文件，没有 hardmasked 文件
    FLAG = True

    # 读取基因组信息文件
    genome_df = pd.read_csv(genomes_info_path, sep='\t', index_col=0)
    
    genome_df.index = genome_df.index.to_series().str.lower()

    for genome_name in genome_df.index:

        # 定义基因组文件的匹配模式
        file_patterns = [f"{genome_name}*.fa.gz", f"{genome_name}*.fasta.gz", f"{genome_name}*.fasta", f"{genome_name}*.fa"]

        # 获取基因组类型
        genome_type = genome_df.loc[genome_name, 'genome_type']

        if genome_type == 'both':
            # 检查hardmasked基因组文件是否存在
            if not any(fnmatch.fnmatch(file.lower(), pattern) for pattern in file_patterns for file in os.listdir(masked_dir)):
                print(f"{genome_name} hardmasked not existed")
                FLAG = False
            # 检查unmasked基因组文件是否存在
            if not any(fnmatch.fnmatch(file.lower(), pattern) for pattern in file_patterns for file in os.listdir(unmasked_dir)):
                print(f"{genome_name} unmasked not existed")
                FLAG = False
        else:
            # 检查unmasked基因组文件是否存在
            if not any(fnmatch.fnmatch(file.lower(), pattern) for pattern in file_patterns for file in os.listdir(unmasked_dir)):
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
    total_bases = 0  # 总碱基数
    num_sequences = 0  # 序列总数
    min_length = float('inf')  # 最小序列长度，初始化为正无穷大
    max_length = 0  # 最大序列长度，初始化为0
    lengths = []  # 存储所有序列长度的列表

    # 使用Biopython的SeqIO模块解析FASTA文件
    if fasta_file.endswith('.gz') or fasta_file.endswith('.gzip'):
        with gzip.open(fasta_file, "rt") as handle:
            for record in SeqIO.parse(handle, 'fasta'):
                seq_length = len(record.seq)  # 当前序列的长度
                total_bases += seq_length  # 累加总碱基数
                num_sequences += 1  # 累加序列总数
                min_length = min(min_length, seq_length)  # 更新最小序列长度
                max_length = max(max_length, seq_length)  # 更新最大序列长度
                lengths.append(seq_length)  # 将当前序列长度添加到列表中

    else:
        for record in SeqIO.parse(fasta_file, 'fasta'):
            seq_length = len(record.seq)  # 当前序列的长度
            total_bases += seq_length  # 累加总碱基数
            num_sequences += 1  # 累加序列总数
            min_length = min(min_length, seq_length)  # 更新最小序列长度
            max_length = max(max_length, seq_length)  # 更新最大序列长度
            lengths.append(seq_length)  # 将当前序列长度添加到列表中

    average_length = int(round(total_bases / num_sequences, 0))  # 计算平均序列长度，并四舍五入到整数

    return {
        'sum_len': total_bases,  # 总碱基数
        'num_seqs': num_sequences,  # 序列总数
        'min_len': min_length,  # 最小序列长度
        'max_len': max_length,  # 最大序列长度
        'avg_len': average_length  # 平均序列长度
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
        print('file', 'format', 'type', 'num_seqs', 'sum_len', 'min_len', 'avg_len', 'max_len', sep='\t', file=outfile)

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
            print(genome_name, 'FASTA', 'DNA', result['num_seqs'], result['sum_len'], result['min_len'], result['avg_len'], result['max_len'], sep='\t', file=outfile)



def split_hardmask_genome(masked_dir, out_dir):
    # 列出所有.fa文件

    filenames = glob(os.path.join(masked_dir, '*.fa')) + glob(os.path.join(masked_dir, '*.fasta')) + glob(os.path.join(masked_dir, '*.gz')) + glob(os.path.join(masked_dir, '*.gzip')) 

    # 创建输出目录（如果尚未存在）
    out_dir = os.path.join(out_dir, 'hardmask_split')
    os.makedirs(out_dir, exist_ok=True)

    for filename in filenames:
        # 创建pyfastx Fasta对象
        fa = pyfastx.Fasta(filename, build_index=True, uppercase=True)

        # 生成输出文件名
        outfilename = os.path.join(out_dir, os.path.basename(filename)).replace('.fa', '_sp.txt').replace('.fasta', '_sp.txt').replace('.fa.gz', '_sp.txt').replace('.fasta.gz', '_sp.txt')

        # 打开输出文件
        with open(outfilename, 'w') as outio:
            for seq in fa:
                sequence = seq.seq
                seqlist = re.split(r'[N]+', sequence)
                sub = 0

                for seq_in_list in seqlist:
                    n = len(seq_in_list)

                    sub += 1
                    if seq_in_list:
                        print(seq_in_list, file=outio)



def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Genome File Checker and Sizes Writer')

    # 添加命令行参数
    parser.add_argument('--genomes_info_path', type=str, required=True,
                        help='Path to the file containing genome name')
    parser.add_argument('--masked_dir', type=str, required=True,
                        help='Directory where hardmasked genome files are located')
    parser.add_argument('--unmasked_dir', type=str, required=True,
                        help='Directory where unmasked genome files are located')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Path to the output file where genome sizes will be written')

    # 解析命令行参数
    args = parser.parse_args()

    # 调用函数
    
    if check_genome_files(args.genomes_info_path, args.masked_dir, args.unmasked_dir):
    
        write_genome_sizes(args.genomes_info_path, args.unmasked_dir, args.output_dir)

        split_hardmask_genome(args.masked_dir, args.output_dir)

    else:
        print("Some genome files are missing, plaese check.")  

if __name__ == "__main__":
    main()