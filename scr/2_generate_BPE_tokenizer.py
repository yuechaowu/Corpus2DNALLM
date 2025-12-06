import sentencepiece as spm
import argparse
import logging

def train_sentencepiece_model(input_file, model_prefix, vocab_size, model_type, num_threads):
    """
    训练SentencePiece模型的函数。

    """
    try:
        # 使用SentencePieceTrainer的train方法训练模型
        spm.SentencePieceTrainer.train(
            input=input_file,     # 指定输入文件
            model_prefix=model_prefix,  # 指定输出模型文件的前缀
            vocab_size=vocab_size,  # 指定词汇表大小
            model_type=model_type,  # 指定模型类型
            num_threads=num_threads,  # 指定训练时使用的线程数
            input_format="text",  # 指定输入文件格式为文本
            add_dummy_prefix=False  # 指定是否添加空格前缀
        )
        # 训练成功后记录日志
        logging.info(f"Model trained successfully. Prefix: {model_prefix}")
    except Exception as e:
        # 捕获并记录训练模型时发生的任何异常
        logging.error(f"Failed to train the model: {e}")

def main():

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
                                    description='Train a SentencePiece tokenizer model. \n Usage exmaple: python 2_generate_BPE_tokenizer.py --input_file ../plants_corpus.txt --model_prefix ../plants_tokenization_BPE --vocab_size 8192 --model_type bpe --num_threads 32'
                                    )
    parser.add_argument('--input_file', type=str, required=True, help='Path to the input file containing text data for training.')
    parser.add_argument('--model_prefix', type=str, required=True, help='Prefix for the generated model files.')
    parser.add_argument('--vocab_size', type=int, default=8192, help='Size of the vocabulary, i.e. the number of unique tokens the model will learn.')
    parser.add_argument('--model_type', type=str, default='bpe', help='Type of the model, e.g. "bpe" (Byte Pair Encoding) or "unigram".')
    parser.add_argument('--num_threads', type=int, default=4, help='Number of threads to use during training for speedup.')

    # 解析命令行参数
    args = parser.parse_args()

    # 调用训练函数
    train_sentencepiece_model(args.input_file, args.model_prefix, args.vocab_size, args.model_type, args.num_threads)

if __name__ == "__main__":
    main()