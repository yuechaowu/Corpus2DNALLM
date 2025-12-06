import os
import glob
import argparse
from random import randint
import pyfastx
from glob import glob
import fnmatch
import re
import numpy as np
import pandas as pd

"""
功能:
拆分大基因组，从Unmasked或HardMasked基因组文件中提取序列，拆分成长度为N的子序列，并将子序列写入到输出文件中。

输入参数:
--genomes_info_path: 包含基因组名称的文件路径
--UnMaskDir: 未屏蔽基因组文件的目录
--SplitMaskDir: 分割屏蔽基因组文件的目录
--GenomeSizeFile: 包含基因组大小信息的文件路径
--outfile: 输出文件路径
--length: 拆分序列的最长长度，默认为4000
--GenomeSplit: 拆分Unmasked基因组的最大长度，默认为500

输出:
将拆分后的子序列写入到输出文件中。
"""


def parseArgs():
    # 创建一个argparse对象，用于解析命令行参数
    parser = argparse.ArgumentParser(description='Prepare genome corpus for SentencePiece.')

    parser.add_argument('--genomes_info_path', type=str, required=True,
                        help='Path to the file containing genome name')

    # 添加一个命令行参数，参数名为'--UnMaskDir'，目标变量名为'UnMaskDir'，帮助信息为空，类型为字符串，且为必选参数
    parser.add_argument('--UnMaskDir', dest='UnMaskDir', help='', type=str, required=True)

    # 添加一个命令行参数，参数名为'--SplitMaskDir'，目标变量名为'SplitMaskDir'，帮助信息为空，类型为字符串，且为必选参数
    parser.add_argument('--SplitMaskDir', dest='SplitMaskDir', help='', type=str, required=True)

    # 添加一个命令行参数，参数名为'--GenomeSizeFile'，目标变量名为'GenomeSizeFile'，帮助信息为空，类型为字符串，且为必选参数
    parser.add_argument('--GenomeSizeFile', dest='GenomeSizeFile', help='', type=str, required=True)

    # 添加一个命令行参数，参数名为'--outfile'，目标变量名为'outfile'，帮助信息为空，类型为字符串，且为必选参数
    parser.add_argument('--outfile', dest='outfile', help='', type=str, required=True)

    # 指定拆分序列的最长长度
    parser.add_argument('--length', dest='length', help='Max length for split sequences', type=int, default=4000)

    # 指定拆分Unmasked基因组的最大长度
    parser.add_argument('--GenomeSplit', dest='GenomeSplit', help='Max length for split genome according to genome size (MB)',
                        type=int, default=500)

    # 解析命令行参数并返回结果
    args = parser.parse_args()

    return args



def findfiles(which, where='.'):
    '''Returns list of filenames from `where` path matched by 'which'
    shell pattern. Matching is case-insensitive.'''

    # TODO: recursive param with walk() filtering
    rule = re.compile(fnmatch.translate(which), re.IGNORECASE)
    return [name for name in os.listdir(where) if rule.match(name)]


class GenomeObj():

    def __init__(self, genomes_info_path, genome_name, UnMaskDir, SplitMaskDir, GenomeSizeFile):
        # 设置基因组名称
        self.genome_name = genome_name

        file_patterns = ["fa", 'fasta', 'fa.gz', 'fasta.gz']

        # 遍历所有基因组名称的扩展名，找到对应的基因组文件
        for pattern in file_patterns:
            UnMaskPath = findfiles(f"{genome_name}*{pattern}", UnMaskDir)
            if len(UnMaskPath) > 0:
                # 获取第一个找到的基因组文件路径
                self.UnMask_genome_file_path = os.path.join(UnMaskDir, UnMaskPath[0])
                # 跳出循环
                break
            # # 拼接未屏蔽基因组的路径
            # UnMaskPath = os.path.join(UnMaskDir, f"{genome_name}*{pattern}")
            # # 如果找到了对应的基因组文件
            # if len(glob(UnMaskPath)) > 0:
            #     # 获取第一个找到的基因组文件路径
            #     self.UnMask_genome_file_path = glob(UnMaskPath)[0]
            #     # 跳出循环
            #     break

        # 从文件中读取UnMask基因组的大小
        self.UnMask_genome_size = round(
            int(pd.read_csv(GenomeSizeFile, sep='\t', index_col=0).loc[genome_name, 'sum_len']) / 1000000, 2)

        genome_df = pd.read_csv(genomes_info_path, sep='\t', index_col=0)
        genome_df.index = genome_df.index.to_series().str.lower()

        genome_type = genome_df.loc[genome_name, 'genome_type']

        if genome_type == 'both':
            # 拼接分割屏蔽基因组的路径
            SplitMaskPath = findfiles(f"{genome_name}*sp.txt", SplitMaskDir)
            # 获取分割屏蔽基因组文件的路径
            self.SplitMask_genome_file_path = os.path.join(SplitMaskDir, SplitMaskPath[0])
            # # 拼接分割屏蔽基因组的路径
            # SplitMaskPath = os.path.join(SplitMaskDir, f"{genome_name}*sp.txt")
            # # 获取分割屏蔽基因组文件的路径
            # self.SplitMask_genome_file_path = glob(SplitMaskPath)[0]

            # 打开SplitMask基因组文件
            with open(self.SplitMask_genome_file_path, 'r') as file:
                content = file.read()
                # 移除空格和换行符
                cleaned_content = content.replace('\n', '')

            # 计算分割屏蔽基因组的大小，并转换为MB单位
            # 计算分割屏蔽基因组的大小
            self.SplitMask_genome_size =  round(len(cleaned_content)/ 1000000, 2)
        else:
            SplitMaskPath = 'none'
            self.SplitMask_genome_size =  'none'


    def judge_and_generate(self, split_size=500, max_length=4000):

        # if genome size < 500M use all unmask
        # if hardmask > 250M, hardmask use 250M, unmask use 250M
        # if hardmask < 250M, hardmask use all, unmask use 250M

        total_seq_list = []

        if self.UnMask_genome_size <= split_size:

            total_seq_list = self.get_all_UnMask(max_length)

        else:
            
            max_genome_size = int(split_size / 2 * 1e6)

            if self.SplitMask_genome_size >= split_size / 2:

                total_seq_list = self.get_SplitHardMask(total_len=max_genome_size, max_length=max_length) + \
                                 self.get_SplitUnMask(total_len=max_genome_size, max_length=max_length)

            else:

                total_seq_list = self.get_all_HardMask(max_length=max_length) + \
                                 self.get_SplitUnMask(total_len=max_genome_size, max_length=max_length)

        return total_seq_list


    def split_sequence(self, sequence, min_length=5, max_length=4000):
        seqlist = []  # 初始化一个空列表来存储子序列
        n = len(sequence)  # 获取序列的长度
        s = 0  # 初始化一个变量s，用于追踪当前的位置
        #print(f'{self.UnMask_genome_file_path}\t{seq.name}\t{n}')  # 打印fasta文件名、序列名和序列长度

        # 当s小于n时，继续循环
        while s < n:
            subseq = ''  # 初始化一个空字符串来存储子序列
            a = randint(0, 1)  # 随机生成0或1
            if a == 0:
                # 如果a为0，那么子序列为从s开始的max_length个字符
                subseq = sequence[s:s+max_length]
                s += max_length  # 更新s的值
            else:
                # 如果a为1，那么子序列的长度为min_length到max_length之间的随机数
                sublen = randint(min_length, max_length)
                subseq = sequence[s:s+sublen]
                s += sublen  # 更新s的值
            if len(subseq) >= min_length:
                # 判断子序列中是否包含除A、C、G、T、N以外的字符
                invalid_base = [char for char in subseq if char not in ['A', 'C', 'G', 'T', 'N']]
                if len(invalid_base) > 0:
                    continue
                else:
                    N_count = subseq.count('N')  # 统计子序列中N的个数
                    if N_count / len(subseq) > 0.2:
                        continue
                    else:
                        seqlist.append(subseq)  # 将子序列添加到seqlist中

        return seqlist


    def get_all_HardMask(self, max_length=4000):
        # 初始化一个空列表用于存储序列
        seqlist = []

        # 打开文件并读取内容
        with open(self.SplitMask_genome_file_path) as inio:
            # 循环读取文件的每一行
            for line in inio:
                # 去除行尾的换行符
                line = line.rstrip()
                # 将拆分的行添加到seqlist中
                seqlist.extend(self.split_sequence(line, max_length=max_length))

        # 返回包含所有序列的列表
        return seqlist


    def get_all_UnMask(self, max_length=4000):

        fa = pyfastx.Fasta(self.UnMask_genome_file_path, build_index=True, uppercase=True)
        seqlist = []  # 初始化一个空列表来存储子序列

        for seq in fa:
            sequence = seq.seq  # 获取序列
            sequence = sequence.upper()  # 将序列转换为大写
            # 替换连续超过10个N的序列为换行符（可能是大片段未拼装或masked重复序列）
            pattern = "N" * 10 + "+"
            sequences = re.sub(pattern, "\n", sequence).split("\n")
            # sequence = sequence.replace('N', '')  # 删除序列中的所有"N"
            # 将拆分的行添加到seqlist中
            for sequence in sequences:
                seqlist.extend(self.split_sequence(sequence, max_length=max_length))

        return seqlist

    def get_SplitHardMask(self, total_len=250000000, max_length=4000):
        seqlist = []
        allseqlen = 0
        with open(self.SplitMask_genome_file_path) as inio:
            for line in inio:
                line = line.rstrip()
                seqlist.extend(self.split_sequence(line, max_length=max_length))
                allseqlen += len(line)
        #print(f"total len {allseqlen}")

        listlen = len(seqlist)  # 获取seqlist的长度
        used = set()  # 初始化一个空列表来存储已经使用过的索引
        sllength = 0  # 初始化一个变量sllength，用于追踪当前的长度
        outlist = list()  # 初始化一个空列表来存储最终的输出

        trytime = 0
        # 当sllength小于total_len时，继续循环
        arr = np.arange(listlen)
        np.random.shuffle(arr)
        randomlist = arr.tolist()

        while sllength < total_len:
            a =  randomlist.pop()
            # 如果索引在used中，那么继续循环
            if a in used:
                continue
            else:
                # 如果a没有在used中，那么将seqlist[a]添加到outlist中，并更新sllength和used
                outlist.append(seqlist[a])
                sllength += len(seqlist[a])
                used.add(a)

            # if trytime % 10000==0:
            #     print(f"{self.SplitMask_genome_file_path} try {trytime} time, now have {len(used)}, nowlen {sllength} ")

            # trytime+=1

        return outlist  # 返回outlist


    def get_SplitUnMask(self, total_len=250000000, max_length=4000):

        # 使用pyfastx读取fasta文件，构建索引，并将所有序列转换为大写
        fa = pyfastx.Fasta(self.UnMask_genome_file_path, build_index=True, uppercase=True)
        seqlist = []  # 初始化一个空列表来存储子序列

        # 遍历fasta文件中的每一个序列
        for seq in fa:
            sequence = seq.seq  # 获取序列
            sequence = sequence.upper()  # 将序列转换为大写
            # 替换连续超过10个N的序列为换行符（可能是大片段未拼装或masked重复序列）
            pattern = "N" * 10 + "+"
            sequences = re.sub(pattern, "\n", sequence).split("\n")
            # sequence = sequence.replace('N', '')  # 删除序列中的所有"N"

            # 将拆分的行添加到seqlist中
            for sequence in sequences:
                seqlist.extend(self.split_sequence(sequence, max_length=max_length))

        listlen = len(seqlist)  # 获取seqlist的长度
        used = set()  # 初始化一个空列表来存储已经使用过的索引
        sllength = 0  # 初始化一个变量sllength，用于追踪当前的长度
        outlist = list()  # 初始化一个空列表来存储最终的输出

        arr = np.arange(listlen)
        np.random.shuffle(arr)
        randomlist = arr.tolist()

        while sllength < total_len:
            a =  randomlist.pop()
            # 如果索引在used中，那么继续循环
            if a in used:
                continue
            else:
                # 如果a没有在used中，那么将seqlist[a]添加到outlist中，并更新sllength和used
                outlist.append(seqlist[a])
                sllength += len(seqlist[a])
                used.add(a)

        return outlist  # 返回outlist


def main():

    # 解析命令行参数
    args = parseArgs()
    genomes_info_path = args.genomes_info_path
    UnMaskDir = args.UnMaskDir
    SplitMaskDir = args.SplitMaskDir
    GenomeSizeFile = args.GenomeSizeFile
    outfile = args.outfile
    max_length = args.length
    split_size = args.GenomeSplit

    # 读取基因组信息文件
    df = pd.read_csv(GenomeSizeFile, sep='\t', index_col=0)

    with open(outfile, 'w') as out:  # 使用with语句确保文件在操作完成后被正确关闭
        for genome_name in df.index:
            print(genome_name)
            # 去除基因组名称中的后缀'.unmasked.fa'
            #genome_name = genome_name.replace('.unmasked.fa', '')

            # 创建Genome对象
            Genome = GenomeObj(genomes_info_path = genomes_info_path, genome_name=genome_name, UnMaskDir=UnMaskDir, SplitMaskDir=SplitMaskDir, GenomeSizeFile=GenomeSizeFile)

            # 调用Genome对象的judge_and_generate方法生成序列列表
            total_seq_list = Genome.judge_and_generate(split_size, max_length)

            # 将序列写入到输出文件中
            for seq in total_seq_list:
                out.write(seq + '\n')


if __name__ == "__main__":

    main()
