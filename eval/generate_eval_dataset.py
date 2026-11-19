"""
Skrip generator dataset evaluasi Telaah.
Menghasilkan 5 berkas PDF benchmark di eval/papers/ dan 30 butir pertanyaan acuan di eval/dataset.jsonl
sesuai spesifikasi di EVAL.md dan SPEC.md.
"""

import json
from pathlib import Path

import fitz  # PyMuPDF


def create_eval_pdfs(eval_dir: Path) -> dict[str, dict]:
    papers_dir = eval_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    papers_info = {
        "attention_vaswani2017.pdf": {
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Lukasz Kaiser", "Illia Polosukhin"],
            "arxiv_id": "1706.03762",
            "domain": "Natural Language Processing / Deep Learning",
            "character": "Arsitektur murni attention tanpa recurrent atau convolutional neural network.",
            "pages": [
                # Page 1: Abstract & Introduction
                (
                    "Attention Is All You Need\n\n"
                    "Abstract\n"
                    "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks "
                    "that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an "
                    "attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention "
                    "mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks "
                    "show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.\n\n"
                    "1 Introduction\n"
                    "Recurrent neural networks, particularly LSTM and GRU, have been established as state of the art approaches in sequence "
                    "modeling and transduction problems. Recurrent models typically factor computation along the symbol positions of the input "
                    "and output sequences. Aligning the positions to steps in computation time generates a sequence of hidden states h_t, "
                    "precluding parallelization within training examples. In this work we propose the Transformer, a model architecture eschewing "
                    "recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output."
                ),
                # Page 2: Model Architecture
                (
                    "2 Model Architecture\n\n"
                    "Most competitive neural sequence transduction models have an encoder-decoder structure. Here, the encoder maps an input "
                    "sequence of symbol representations (x_1, ..., x_n) to a sequence of continuous representations z = (z_1, ..., z_n). "
                    "Given z, the decoder then generates an output sequence (y_1, ..., y_m) of symbols one element at a time.\n\n"
                    "Encoder: The encoder is composed of a stack of N = 6 identical layers. Each layer has two sub-layers: a multi-head "
                    "self-attention mechanism and a simple, position-wise fully connected feed-forward network. We employ a residual connection "
                    "around each of the two sub-layers, followed by layer normalization. The output of each sub-layer is LayerNorm(x + Sublayer(x)). "
                    "To facilitate residual connections, all sub-layers in the model, as well as the embedding layers, produce outputs of "
                    "dimension d_model = 512.\n\n"
                    "Decoder: The decoder is also composed of a stack of N = 6 identical layers. In addition to the two sub-layers in each "
                    "encoder layer, the decoder inserts a third sub-layer, which performs multi-head attention over the output of the encoder stack. "
                    "We also modify the self-attention sub-layer in the decoder stack to prevent positions from attending to subsequent positions. "
                    "This masking ensures that the predictions for position i can depend only on the known outputs at positions less than i."
                ),
                # Page 3: Attention Mechanism Details
                (
                    "3 Attention\n\n"
                    "An attention function can be described as mapping a query and a set of key-value pairs to an output. "
                    "The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a "
                    "compatibility function of the query with the corresponding key.\n\n"
                    "3.1 Scaled Dot-Product Attention\n"
                    "We call our particular attention 'Scaled Dot-Product Attention'. The input consists of queries and keys of dimension d_k, "
                    "and values of dimension d_v. We compute the dot products of the query with all keys, divide each by sqrt(d_k), and apply a "
                    "softmax function to obtain the weights on the values:\n"
                    "Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V\n\n"
                    "3.2 Multi-Head Attention\n"
                    "Instead of performing a single attention function with d_model-dimensional queries, keys and values, we found it beneficial "
                    "to linearly project the queries, keys and values h times with different, learned linear projections to d_k, d_k and d_v dimensions, "
                    "respectively. In this work we employ h = 8 parallel attention layers, or heads. For each of these we use d_k = d_v = d_model / h = 64. "
                    "Due to the reduced dimension of each head, the total computational cost is similar to that of single-head attention with full dimensionality."
                ),
                # Page 4: Training & Results
                (
                    "4 Training & Results\n\n"
                    "4.1 Training Data and Batching\n"
                    "We trained on the standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs. Sentences were encoded "
                    "using byte-pair encoding with a shared source-target vocabulary of about 37,000 tokens. For English-French, we used the significantly "
                    "larger WMT 2014 English-French dataset consisting of 36 million sentence pairs with a 32,000 word-piece vocabulary.\n\n"
                    "Table 2: Machine Translation Performance and Training Costs\n"
                    "Model                 BLEU (EN-DE)   BLEU (EN-FR)   Training Cost (FLOPs)\n"
                    "ByteNet               23.75          -              - \n"
                    "MoE                   26.03          40.56          1.2e20\n"
                    "GNMT + RL             24.60          39.92          2.3e19\n"
                    "ConvS2S               25.16          40.46          9.6e18\n"
                    "Transformer (base)    27.3           38.1           3.3e18\n"
                    "Transformer (big)     28.4           41.8           2.3e19\n\n"
                    "On the WMT 2014 English-to-German translation task, the big transformer model establishes a new state-of-the-art BLEU score "
                    "of 28.4, outperforming the best existing models including ensembles by more than 2.0 BLEU. On the WMT 2014 English-to-French "
                    "translation task, our big model achieves a BLEU score of 41.8, outperforming all previously published single models, at less than "
                    "1/4 the training cost of the previous state-of-the-art model."
                ),
                # Page 5: Conclusion & Limitations
                (
                    "5 Conclusion & Limitations\n\n"
                    "In this work, we presented the Transformer, the first sequence transduction model based entirely on attention, replacing the "
                    "recurrent layers most commonly used in encoder-decoder architectures with multi-head self-attention.\n\n"
                    "Limitations:\n"
                    "Despite its empirical success, the Transformer has notable limitations. The self-attention mechanism incurs a quadratic "
                    "computational and memory complexity O(n^2) with respect to input sequence length n. This makes processing very long documents "
                    "or high-resolution images memory-intensive without sparse attention approximations. Furthermore, training the big model required "
                    "specialized hardware (8 NVIDIA P100 GPUs for 3.5 days), which may limit immediate accessibility for resource-constrained environments."
                ),
            ],
        },
        "bert_devlin2018.pdf": {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
            "arxiv_id": "1810.04805",
            "domain": "Natural Language Processing / Pre-training",
            "character": "Representasi bahasa bidirectional dua arah menggunakan Masked Language Model dan Next Sentence Prediction.",
            "pages": [
                # Page 1: Abstract & Introduction
                (
                    "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding\n\n"
                    "Abstract\n"
                    "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. "
                    "Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by "
                    "jointly conditioning on both left and right context in all layers. As a result, the pre-trained BERT model can be fine-tuned with just "
                    "one additional output layer to create state-of-the-art models for a wide range of tasks, such as question answering and language inference, "
                    "without substantial task-specific architecture modifications.\n\n"
                    "1 Introduction\n"
                    "Language model pre-training has been shown to be effective for improving many natural language processing tasks. There are two existing "
                    "strategies for applying pre-trained language representations to downstream tasks: feature-based and fine-tuning. We argue that current "
                    "techniques restrict the power of the pre-trained representations, primarily because standard language models are unidirectional, "
                    "which severely limits the choice of architectures during pre-training."
                ),
                # Page 2: Pre-training Objectives
                (
                    "2 Pre-training BERT\n\n"
                    "BERT alleviates the unidirectionality constraint by using a 'masked language model' (MLM) pre-training objective. "
                    "The masked language model randomly masks some of the tokens from the input, and the objective is to predict the original vocabulary "
                    "id of the masked word based only on its context.\n\n"
                    "Task #1: Masked LM (MLM)\n"
                    "In our experiments, we mask 15% of all WordPiece tokens in each sequence at random. If the i-th token is chosen, we replace the "
                    "i-th token with: (1) the [MASK] token 80% of the time, (2) a random token 10% of the time, and (3) the unchanged i-th token 10% of the time.\n\n"
                    "Task #2: Next Sentence Prediction (NSP)\n"
                    "Many important downstream tasks such as Question Answering (QA) and Natural Language Inference (NLI) are based on understanding the "
                    "relationship between two sentences, which is not directly captured by language modeling. In order to train a model that understands sentence "
                    "relationships, we pre-train for a binarized next sentence prediction task. Specifically, when choosing the sentences A and B for each "
                    "pre-training example, 50% of the time B is the actual next sentence that follows A (labeled as IsNext), and 50% of the time it is a random "
                    "sentence from the corpus (labeled as NotNext)."
                ),
                # Page 3: Model Configurations
                (
                    "3 Model Architecture and Configurations\n\n"
                    "BERT's model architecture is a multi-layer bidirectional Transformer encoder based on the original implementation described in Vaswani et al. (2017).\n\n"
                    "We denote the number of layers (i.e., Transformer blocks) as L, the hidden size as H, and the number of self-attention heads as A.\n"
                    "We primarily report results on two model sizes:\n"
                    "- BERT_BASE: L=12, H=768, A=12, Total Parameters = 110M\n"
                    "- BERT_LARGE: L=24, H=1024, A=16, Total Parameters = 340M\n\n"
                    "BERT_BASE was chosen to have the identical model size as OpenAI GPT for comparison purposes. However, BERT Transformer uses bidirectional "
                    "self-attention, whereas the GPT Transformer uses constrained self-attention where every token can only attend to context to its left."
                ),
                # Page 4: GLUE Benchmark Results
                (
                    "4 Experiments & Results on GLUE Benchmark\n\n"
                    "The General Language Understanding Evaluation (GLUE) benchmark is a collection of diverse natural language understanding tasks.\n\n"
                    "Table 1: GLUE Test Results scored by the evaluation server.\n"
                    "Model          MNLI-(m/mm)   QQP     QNLI    SST-2   CoLA    STS-B   MRPC    RTE     Average\n"
                    "Pre-BERT SOTA  80.6/80.1     66.1    82.3    93.2    35.0    81.0    86.0    61.7    74.0\n"
                    "OpenAI GPT     82.1/81.4     70.3    87.4    91.3    45.4    80.0    82.3    56.0    75.1\n"
                    "BERT_BASE      84.6/83.4     71.2    90.5    93.5    52.1    85.8    88.9    66.4    79.6\n"
                    "BERT_LARGE     86.7/85.9     72.1    92.7    94.9    60.5    86.5    89.3    70.1    82.1\n\n"
                    "BERT_BASE and BERT_LARGE outperform all existing systems on all tasks by a wide margin, achieving 4.5% and 7.0% average accuracy "
                    "improvement over the previous state of the art, respectively. Note that BERT_LARGE significantly outperforms BERT_BASE across all tasks, "
                    "especially those with very little training data."
                ),
                # Page 5: Conclusion & Limitations
                (
                    "5 Conclusion & Limitations\n\n"
                    "Recent empirical improvements due to transfer learning with language models have demonstrated that rich, unsupervised pre-training "
                    "is an integral part of many language understanding systems. In particular, these results enable even low-resource tasks to benefit "
                    "from deep bidirectional architectures.\n\n"
                    "Limitations:\n"
                    "BERT's pre-training relies on BooksCorpus (800M words) and English Wikipedia (2,500M words). The [MASK] token never appears during "
                    "fine-tuning, creating a pre-train vs. fine-tune mismatch that required our 80-10-10 replacement heuristic. Furthermore, BERT has a "
                    "maximum sequence length limitation of 512 tokens due to positional embeddings and quadratic attention computation, making it unsuitable "
                    "for long document classification without chunking."
                ),
            ],
        },
        "lora_hu2021.pdf": {
            "title": "LoRA: Low-Rank Adaptation of Large Language Models",
            "authors": ["Edward J. Hu", "Yelong Shen", "Phillip Wallis", "Zeyuan Allen-Zhu", "Yuanzhi Li", "Shean Wang", "Lu Wang", "Weizhu Chen"],
            "arxiv_id": "2106.09685",
            "domain": "Machine Learning / Parameter-Efficient Fine-Tuning",
            "character": "Efisiensi adaptasi LLM dengan dekomposisi matriks rank rendah tanpa latensi inferensi tambahan.",
            "pages": [
                # Page 1: Abstract & Introduction
                (
                    "LoRA: Low-Rank Adaptation of Large Language Models\n\n"
                    "Abstract\n"
                    "An important paradigm of natural language processing consists of large-scale pre-training on general domain data and adaptation to "
                    "particular tasks or domains. As we pre-train larger models, full fine-tuning, which retrains all model parameters, becomes less feasible. "
                    "Using GPT-3 175B as an example, deploying independent instances of fine-tuned models, each with 175B parameters, is prohibitively expensive. "
                    "We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained model weights and injects trainable rank decomposition matrices into "
                    "each layer of the Transformer architecture, greatly reducing the number of trainable parameters for downstream tasks.\n\n"
                    "1 Introduction\n"
                    "Many applications in natural language processing rely on adapting one large, pre-trained language model to multiple downstream tasks. "
                    "This adaptation is typically done via fine-tuning, which updates all the parameters of the pre-trained model. The major downside of full "
                    "fine-tuning is that the new model contains as many parameters as the original model. For massive models such as GPT-3 (175 billion parameters), "
                    "storing and serving multiple fine-tuned models becomes a severe operational bottleneck."
                ),
                # Page 2: Method and Low-Rank Decomposition
                (
                    "2 Low-Rank Adaptation (LoRA) Method\n\n"
                    "A neural network contains many dense layers which perform matrix multiplication. The weight matrices in these layers typically have "
                    "full-rank. When adapting to a specific task, Aghajanyan et al. (2020) show that the pre-trained language models have a low 'intrinsic dimension' "
                    "and can still learn efficiently despite a random projection to a smaller subspace.\n\n"
                    "Inspired by this, we hypothesize the updates to the weights also have a low 'intrinsic rank' during adaptation. For a pre-trained weight matrix "
                    "W_0 in R^{d x k}, we constrain its update by representing the latter with a low-rank decomposition:\n"
                    "W_0 + Delta_W = W_0 + B * A\n"
                    "where B in R^{d x r}, A in R^{r x k}, and the rank r << min(d, k).\n\n"
                    "During training, W_0 is frozen and does not receive gradient updates, while A and B contain trainable parameters. Note both W_0 and "
                    "Delta_W = BA are multiplied with the same input x, and their respective output vectors are summed coordinate-wise:\n"
                    "h = W_0 x + Delta_W x = W_0 x + B A x\n"
                    "We use a random Gaussian initialization for A and zero for B, so Delta_W = BA is zero at the beginning of training."
                ),
                # Page 3: Memory and Latency Advantages
                (
                    "3 Advantages: No Additional Inference Latency\n\n"
                    "When deploying in production, we can explicitly compute and store W = W_0 + BA and perform inference as usual. "
                    "Because both W_0 and Delta_W are in R^{d x k}, there is zero additional latency compared to the fully fine-tuned model. When switching "
                    "to another downstream task, we can recover W_0 by subtracting BA and then adding a different B'A', a quick operation with minimal memory overhead.\n\n"
                    "Memory Reduction:\n"
                    "When applying LoRA to GPT-3 175B, we reduce VRAM consumption during training from 1.2 TB to 350 GB. With r = 4 and adapting only the attention "
                    "weights (W_q, W_v), the checkpoint size is reduced by roughly 10,000x (from 350 GB to 35 MB per task). This allows training with significantly "
                    "fewer GPUs and eliminates CPU-GPU transfer bottlenecks during task-switching."
                ),
                # Page 4: Experimental Results on GPT-3
                (
                    "4 Empirical Evaluation on GPT-3 175B\n\n"
                    "We evaluate LoRA on GPT-3 175B across WikiSQL, MultiNLI, and SAMSum.\n\n"
                    "Table 2: Comparison on GPT-3 175B benchmarks.\n"
                    "Method                  Trainable Params   WikiSQL (Acc)   MultiNLI (Acc)   SAMSum (Rouge-1/2/L)\n"
                    "Pre-trained GPT-3 (0-shot) 0                  63.1            68.0             38.5 / 14.2 / 31.8\n"
                    "Full Fine-Tuning        175,000M           73.8            89.5             52.0 / 28.0 / 44.5\n"
                    "Prefix-Tuning (len=10)  3.2M               71.2            88.1             50.8 / 26.3 / 43.1\n"
                    "Series Adapter          11.5M              72.5            88.9             51.3 / 27.2 / 43.8\n"
                    "LoRA (r=4, W_q,v)       4.7M               73.4            89.7             51.8 / 27.6 / 44.3\n"
                    "LoRA (r=8, W_q,v)       9.4M               74.1            89.9             52.3 / 28.5 / 44.8\n\n"
                    "LoRA matches or exceeds the performance of full fine-tuning while using less than 0.01% of the trainable parameters. "
                    "Furthermore, LoRA outperforms Prefix-Tuning and Adapter methods while maintaining constant inference latency."
                ),
                # Page 5: Conclusion & Limitations
                (
                    "5 Conclusion & Limitations\n\n"
                    "LoRA provides an efficient and effective alternative to full fine-tuning for large language models, preserving output quality "
                    "while drastically lowering storage and serving requirements.\n\n"
                    "Limitations:\n"
                    "It is not straightforward to batch inputs in different tasks with different LoRA modules in a single forward pass when W is merged. "
                    "While one can choose not to merge W = W_0 + BA and dynamically route batches, this introduces additional memory lookups and latency. "
                    "Additionally, LoRA's performance gains are primarily validated on attention weights; adapting MLP layers or convolutional layers "
                    "shows diminishing returns relative to parameter growth."
                ),
            ],
        },
        "resnet_he2015.pdf": {
            "title": "Deep Residual Learning for Image Recognition",
            "authors": ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
            "arxiv_id": "1512.03385",
            "domain": "Computer Vision / Deep Learning",
            "character": "Koneksi residual identity shortcut untuk mengatasi masalah degradasi gradien pada jaringan sangat dalam.",
            "pages": [
                # Page 1: Abstract & Introduction
                (
                    "Deep Residual Learning for Image Recognition\n\n"
                    "Abstract\n"
                    "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks "
                    "that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference "
                    "to the layer inputs, instead of learning unreferenced functions. We provide comprehensive empirical evidence showing that these residual "
                    "networks are easier to optimize, and can gain accuracy from considerably increased depth. On the ImageNet dataset we evaluate residual "
                    "nets with a depth of up to 152 layers—8x deeper than VGG nets but still having lower complexity. An ensemble of these residual nets "
                    "achieves 3.57% error on the ImageNet test set. This result won the 1st place on the ILSVRC 2015 classification task.\n\n"
                    "1 Introduction\n"
                    "Deep convolutional neural networks have led to a series of breakthroughs for image classification. When deeper networks are able to start "
                    "converging, a degradation problem has been exposed: with the network depth increasing, accuracy gets saturated and then degrades rapidly. "
                    "Unexpectedly, such degradation is not caused by overfitting, and adding more layers to a suitably deep model leads to higher training error."
                ),
                # Page 2: Deep Residual Learning Formulation
                (
                    "2 Deep Residual Learning Formulation\n\n"
                    "Instead of hoping every few stacked layers directly fit a desired underlying mapping H(x), we explicitly let these layers fit a "
                    "residual mapping F(x) := H(x) - x. The original mapping is recast into F(x) + x. We hypothesize that it is easier to optimize the "
                    "residual mapping than to optimize the original, unreferenced mapping. To the extreme, if an identity mapping were optimal, it would be "
                    "easier to push the residual to zero than to fit an identity mapping by a stack of nonlinear layers.\n\n"
                    "The formulation of F(x) + x by feedforward neural networks with 'shortcut connections' can be realized. Shortcut connections are those "
                    "skipping one or more layers. In our case, shortcut connections simply perform identity mapping, and their outputs are added to the outputs "
                    "of the stacked layers. Identity shortcut connections introduce neither extra parameter nor computation complexity. The entire network "
                    "can still be trained end-to-end by SGD with backpropagation."
                ),
                # Page 3: Network Architectures & Bottleneck Design
                (
                    "3 Network Architectures\n\n"
                    "Plain Network: Our plain baselines are mainly inspired by the philosophy of VGG nets. The convolutional layers mostly have 3x3 filters "
                    "and follow two design rules: (i) for the same output feature map size, the layers have the same number of filters; and (ii) if the feature "
                    "map size is halved, the number of filters is doubled so as to preserve the time complexity per layer.\n\n"
                    "Residual Network: Based on the above plain network, we insert shortcut connections which turn the network into its counterpart residual version.\n\n"
                    "Deeper Bottleneck Architecture: For deeper networks such as ResNet-50, ResNet-101, and ResNet-152, we use a bottleneck design. For each "
                    "residual function F, we use a stack of 3 layers: 1x1, 3x3, and 1x1 convolutions, where the 1x1 layers are responsible for reducing and then "
                    "restoring (increasing) dimensions, leaving the 3x3 layer a bottleneck with smaller input/output dimensions."
                ),
                # Page 4: ImageNet Classification Results
                (
                    "4 Experiments & Results on ImageNet\n\n"
                    "We evaluate our methods on the ImageNet 2012 classification dataset that consists of 1000 classes. The models are trained on the 1.28 million "
                    "training images, and evaluated on the 50k validation images.\n\n"
                    "Table 3: Top-1 and Top-5 error rates (%) on ImageNet validation.\n"
                    "Model                 Top-1 Error (%)   Top-5 Error (%)   FLOPs\n"
                    "VGG-16                28.07             9.33              15.3 x 10^9\n"
                    "GoogLeNet             -                 9.15              - \n"
                    "Plain-34              28.54             10.02             3.6 x 10^9\n"
                    "ResNet-18             27.88             8.92              1.8 x 10^9\n"
                    "ResNet-34             25.03             7.76              3.6 x 10^9\n"
                    "ResNet-50             22.85             6.71              3.8 x 10^9\n"
                    "ResNet-101            21.75             6.05              7.6 x 10^9\n"
                    "ResNet-152            21.43             5.71              11.3 x 10^9\n\n"
                    "Our 152-layer ResNet achieves 21.43% top-1 and 5.71% top-5 error rate on the validation set, substantially outperforming all previous "
                    "models. The ensemble of six ResNets achieved 3.57% top-5 error on the test set, winning 1st place in ILSVRC 2015."
                ),
                # Page 5: Conclusion & Limitations
                (
                    "5 Conclusion & Limitations\n\n"
                    "We have introduced a residual learning framework that eases the training of substantially deeper networks. Our results demonstrate that "
                    "residual networks can achieve superior accuracy with depths of over 100 layers without suffering from degradation.\n\n"
                    "Limitations:\n"
                    "While residual connections eliminate the degradation problem during optimization, extremely deep models (e.g., ResNet-1000 tested on CIFAR) "
                    "exhibit mild overfitting because the network capacity is needlessly large for smaller datasets. Furthermore, identity additions require "
                    "matching tensor dimensions, necessitating 1x1 projection shortcuts when stride > 1, which increases parameter count slightly."
                ),
            ],
        },
        "rag_lewis2020.pdf": {
            "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            "authors": ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus", "Fabio Petroni", "Vladimir Karpukhin", "Naman Goyal", "Heinrich Küttler", "Mike Lewis", "Wen-tau Yih", "Tim Rocktäschel", "Sebastian Riedel", "Douwe Kiela"],
            "arxiv_id": "2005.11401",
            "domain": "Natural Language Processing / Question Answering & RAG",
            "character": "Model hibrida memori parametrik (BART) dan non-parametrik (DPR Wikipedia index).",
            "pages": [
                # Page 1: Abstract & Introduction
                (
                    "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks\n\n"
                    "Abstract\n"
                    "Large pre-trained language models have been shown to store factual knowledge in their parameters, and achieve state-of-the-art results "
                    "when fine-tuned on downstream NLP tasks. However, their ability to access and precisely manipulate knowledge is still limited, and "
                    "they often hallucinate on knowledge-intensive tasks. We explore a general-purpose fine-tuning recipe for retrieval-augmented generation (RAG) "
                    "— models which combine pre-trained parametric and non-parametric memory for language generation. We introduce RAG models where the "
                    "parametric memory is a pre-trained seq2seq model and the non-parametric memory is a dense vector index of Wikipedia, accessed with a "
                    "pre-trained neural retriever.\n\n"
                    "1 Introduction\n"
                    "Pre-trained neural language models learn a substantial amount of in-depth world knowledge from data. Despite these successes, such models "
                    "have severe shortcomings: they cannot easily expand or revise their memory, they cannot straightforwardly provide insight into their "
                    "predictions or cite their sources, and they may produce 'hallucinations'."
                ),
                # Page 2: Methods: RAG-Sequence and RAG-Token
                (
                    "2 Methods\n\n"
                    "RAG models leverage a retriever p_eta(z|x) with parameters eta, and a generator p_theta(y_i|x, z, y_{1:i-1}) parametrized by theta. "
                    "Given input sequence x, we use the retriever to query top-K latent documents z, and then the generator conditions on both z and x "
                    "to generate target sequence y.\n\n"
                    "We propose two variants of RAG:\n\n"
                    "RAG-Sequence Model:\n"
                    "The RAG-Sequence model uses the same retrieved document to generate the complete sequence. Formally, it treats the retrieved document "
                    "as a single latent variable that is marginalized to get the seq2seq probability via a top-K approximation:\n"
                    "p_RAG-Seq(y|x) = sum_{z in top-K(p(·|x))} p_eta(z|x) prod_{i}^N p_theta(y_i|x, z, y_{1:i-1})\n\n"
                    "RAG-Token Model:\n"
                    "In the RAG-Token model, we can draw a different latent document for each target token and marginalize accordingly. This allows the "
                    "generator to choose content from multiple documents when producing an answer:\n"
                    "p_RAG-Token(y|x) = prod_{i}^N sum_{z in top-K(p(·|x))} p_eta(z|x) p_theta(y_i|x, z, y_{1:i-1})"
                ),
                # Page 3: Retriever and Generator Components
                (
                    "3 Components: Retriever and Generator\n\n"
                    "Retriever: Dense Passage Retriever (DPR)\n"
                    "The retriever p_eta(z|x) is based on DPR (Karpukhin et al., 2020). DPR uses a bi-encoder architecture based on BERT_BASE: "
                    "one encoder q(x) embeds query x, and a second encoder d(z) embeds document passage z. The retrieval score is the dot product:\n"
                    "sim(x, z) = q(x)^T d(z)\n"
                    "The non-parametric knowledge index uses the December 2018 dump of Wikipedia, split into 21 million 100-word chunks, indexed using FAISS.\n\n"
                    "Generator: BART\n"
                    "The generator component p_theta(y_i|x, z, y_{1:i-1}) is parameterized using BART-large, a pre-trained seq2seq Transformer with "
                    "400 million parameters (Lewis et al., 2019). When combining input x and retrieved passage z, they are simply concatenated as input to BART."
                ),
                # Page 4: Open-Domain QA Results
                (
                    "4 Experimental Results on Open-Domain QA\n\n"
                    "We evaluate RAG on four open-domain question answering benchmarks: Natural Questions (NQ), TriviaQA (TQA), WebQuestions (WQ), "
                    "and CuratedTREC (CT).\n\n"
                    "Table 1: Open-domain QA Test Results (Exact Match %)\n"
                    "Model                 NQ      TriviaQA   WebQuestions   CuratedTREC\n"
                    "T5-11B (closed-book)  34.5    50.1       37.4           - \n"
                    "REALM                 40.4    -          40.7           - \n"
                    "DPR + Reader          41.5    56.8       41.1           44.6\n"
                    "RAG-Token             44.1    55.2       45.5           50.0\n"
                    "RAG-Sequence          44.5    56.1       45.2           52.2\n\n"
                    "RAG sets a new state-of-the-art on Natural Questions (44.5% EM), WebQuestions (45.5% EM), and CuratedTREC (52.2% EM). "
                    "Remarkably, RAG achieves these scores while combining a 400M parameter generator with non-parametric retrieval, outperforming "
                    "the closed-book T5-11B model which possesses 11 billion parameters."
                ),
                # Page 5: Conclusion & Limitations
                (
                    "5 Conclusion & Limitations\n\n"
                    "In this work, we presented RAG models which combine parametric memory with non-parametric dense retrieval. RAG establishes state-of-the-art "
                    "performance across multiple open-domain QA and knowledge generation benchmarks.\n\n"
                    "Limitations:\n"
                    "The retrieval index of 21 million passages requires substantial disk and memory footprint (~100 GB RAM for uncompressed FAISS index). "
                    "Furthermore, while RAG significantly reduces hallucinations compared to purely parametric models, it can still generate fluent yet incorrect "
                    "answers when retrieved passages contain contradictory or partially irrelevant information."
                ),
            ],
        },
    }

    # Generate each PDF
    for filename, info in papers_info.items():
        doc = fitz.open()
        for page_num, text_content in enumerate(info["pages"], start=1):
            page = doc.new_page(width=595, height=842)  # A4 size
            # Insert header
            page.insert_text(
                fitz.Point(50, 40),
                f"Telaah Evaluation Benchmark — {info['title']}",
                fontsize=8,
                color=(0.5, 0.5, 0.5),
            )
            # Insert main text
            page.insert_textbox(
                fitz.Rect(50, 60, 545, 800),
                text_content,
                fontsize=9.5,
                lineheight=1.3,
            )
            # Insert footer page number
            page.insert_text(
                fitz.Point(280, 820),
                f"- Halaman {page_num} -",
                fontsize=8,
                color=(0.6, 0.6, 0.6),
            )
        pdf_path = papers_dir / filename
        doc.save(str(pdf_path))
        doc.close()
        print(f"Generated PDF: {pdf_path} ({len(info['pages'])} halaman)")

    return papers_info


def create_eval_dataset(eval_dir: Path) -> list[dict]:
    """
    Menghasilkan 30 pertanyaan uji lengkap dengan ground truth acuan dan kategori sesuai EVAL.md:
    - 15 Factual (3 per paper)
    - 5 Table/Figure (1 per paper)
    - 5 Reasoning/Limitations (1 per paper)
    - 5 Unanswerable (1 per paper - menguji mode tidak ditemukan / penolakan halusinasi)
    """
    dataset = [
        # --- Paper 1: Attention Is All You Need (attention_vaswani2017.pdf) ---
        {
            "id": "q001",
            "paper": "attention_vaswani2017.pdf",
            "category": "factual",
            "question": "Berapa banyak lapisan (layers) encoder dan decoder yang digunakan dalam arsitektur Transformer?",
            "reference_answer": "Arsitektur Transformer menggunakan tumpukan N = 6 lapisan identik untuk encoder dan N = 6 lapisan identik untuk decoder.",
            "source_pages": [2],
            "should_refuse": False,
        },
        {
            "id": "q002",
            "paper": "attention_vaswani2017.pdf",
            "category": "factual",
            "question": "Berapa jumlah attention heads (h) dan dimensi tiap head (d_k) pada model Transformer?",
            "reference_answer": "Model Transformer menggunakan h = 8 parallel attention heads dengan dimensi d_k = d_v = 64 untuk tiap head.",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q003",
            "paper": "attention_vaswani2017.pdf",
            "category": "factual",
            "question": "Apa rumus matematis dari Scaled Dot-Product Attention yang dijelaskan pada paper?",
            "reference_answer": "Rumusnya adalah Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V.",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q004",
            "paper": "attention_vaswani2017.pdf",
            "category": "table_figure",
            "question": "Berdasarkan Tabel 2, berapa skor BLEU yang dicapai oleh model Transformer (big) pada tugas penerjemahan English-to-German?",
            "reference_answer": "Pada Tabel 2, model Transformer (big) mencapai skor BLEU 28.4 pada English-to-German.",
            "source_pages": [4],
            "should_refuse": False,
        },
        {
            "id": "q005",
            "paper": "attention_vaswani2017.pdf",
            "category": "reasoning",
            "question": "Mengapa komputasi self-attention pada Transformer menjadi beban memori pada teks yang sangat panjang?",
            "reference_answer": "Karena mekanisme self-attention memiliki kompleksitas komputasi dan memori kuadratik O(n^2) terhadap panjang sequence masukan n.",
            "source_pages": [5],
            "should_refuse": False,
        },
        {
            "id": "q006",
            "paper": "attention_vaswani2017.pdf",
            "category": "unanswerable",
            "question": "Berapa akurasi klasifikasi citra model Transformer pada dataset ImageNet-1K?",
            "reference_answer": "Informasi tersebut tidak ditemukan di dalam paper ini, karena paper ini hanya mengevaluasi tugas machine translation (WMT 2014) dan parsing teks, bukan klasifikasi citra ImageNet.",
            "source_pages": [],
            "should_refuse": True,
        },

        # --- Paper 2: BERT (bert_devlin2018.pdf) ---
        {
            "id": "q007",
            "paper": "bert_devlin2018.pdf",
            "category": "factual",
            "question": "Berapa jumlah parameter total dan jumlah layer pada model BERT_BASE dan BERT_LARGE?",
            "reference_answer": "BERT_BASE memiliki 12 layer (L=12) dengan total 110 juta parameter (110M), sedangkan BERT_LARGE memiliki 24 layer (L=24) dengan total 340 juta parameter (340M).",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q008",
            "paper": "bert_devlin2018.pdf",
            "category": "factual",
            "question": "Bagaimana aturan pembagian persentase penggantian token saat melakukan Masked Language Model (MLM) 15% pada BERT?",
            "reference_answer": "Dari 15% token yang dipilih, 80% diganti dengan token [MASK], 10% diganti dengan token acak, dan 10% dipertahankan tanpa perubahan.",
            "source_pages": [2],
            "should_refuse": False,
        },
        {
            "id": "q009",
            "paper": "bert_devlin2018.pdf",
            "category": "factual",
            "question": "Apa tujuan dari task Next Sentence Prediction (NSP) pada pre-training BERT?",
            "reference_answer": "Tujuannya adalah untuk melatih model memahami hubungan antar-kalimat yang penting untuk tugas lanjutan seperti Question Answering (QA) dan Natural Language Inference (NLI).",
            "source_pages": [2],
            "should_refuse": False,
        },
        {
            "id": "q010",
            "paper": "bert_devlin2018.pdf",
            "category": "table_figure",
            "question": "Berdasarkan Tabel 1 hasil GLUE benchmark, berapa skor rata-rata (Average) yang dicapai oleh BERT_LARGE dibandingkan OpenAI GPT?",
            "reference_answer": "Pada Tabel 1, BERT_LARGE mencapai skor rata-rata 82.1, sedangkan OpenAI GPT mencapai 75.1.",
            "source_pages": [4],
            "should_refuse": False,
        },
        {
            "id": "q011",
            "paper": "bert_devlin2018.pdf",
            "category": "reasoning",
            "question": "Mengapa keberadaan token [MASK] menimbulkan ketidaksesuaian (mismatch) antara fase pre-training dan fine-tuning pada BERT?",
            "reference_answer": "Karena token [MASK] hanya muncul saat fase pre-training dan tidak pernah muncul sama sekali pada data downstream saat fine-tuning.",
            "source_pages": [5],
            "should_refuse": False,
        },
        {
            "id": "q012",
            "paper": "bert_devlin2018.pdf",
            "category": "unanswerable",
            "question": "Berapa skor ROUGE-L yang dicapai BERT pada tugas peringkasan dokumen CNN/DailyMail?",
            "reference_answer": "Informasi tersebut tidak ditemukan di dalam paper ini, karena evaluasi paper BERT berfokus pada GLUE benchmark, SQuAD, dan SWAG, bukan summarization CNN/DailyMail.",
            "source_pages": [],
            "should_refuse": True,
        },

        # --- Paper 3: LoRA (lora_hu2021.pdf) ---
        {
            "id": "q013",
            "paper": "lora_hu2021.pdf",
            "category": "factual",
            "question": "Bagaimana formulasi matematis pembaruan bobot W_0 pada metode LoRA?",
            "reference_answer": "Pembaruan bobot diformulasikan sebagai W_0 + Delta_W = W_0 + B * A, di mana B berdimensi (d x r), A berdimensi (r x k), dan r << min(d, k).",
            "source_pages": [2],
            "should_refuse": False,
        },
        {
            "id": "q014",
            "paper": "lora_hu2021.pdf",
            "category": "factual",
            "question": "Bagaimana inisialisasi awal matriks A dan matriks B pada LoRA saat mulai pelatihan?",
            "reference_answer": "Matriks A diinisialisasi menggunakan distribusi acak Gaussian (random Gaussian), sedangkan matriks B diinisialisasi dengan angka nol (zero), sehingga Delta_W = BA bernilai nol di awal pelatihan.",
            "source_pages": [2],
            "should_refuse": False,
        },
        {
            "id": "q015",
            "paper": "lora_hu2021.pdf",
            "category": "factual",
            "question": "Berapa penurunan konsumsi VRAM pelatihan pada GPT-3 175B saat menggunakan LoRA?",
            "reference_answer": "Konsumsi VRAM selama pelatihan GPT-3 175B berkurang dari 1.2 TB menjadi 350 GB.",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q016",
            "paper": "lora_hu2021.pdf",
            "category": "table_figure",
            "question": "Berdasarkan Tabel 2, berapa skor akurasi LoRA (r=8) pada dataset MultiNLI dibandingkan Full Fine-Tuning pada GPT-3 175B?",
            "reference_answer": "Pada Tabel 2, LoRA (r=8) mencapai akurasi MultiNLI sebesar 89.9%, melampaui Full Fine-Tuning yang memperoleh 89.5%.",
            "source_pages": [4],
            "should_refuse": False,
        },
        {
            "id": "q017",
            "paper": "lora_hu2021.pdf",
            "category": "reasoning",
            "question": "Mengapa LoRA tidak menambah latensi inferensi saat diterapkan pada lingkungan produksi?",
            "reference_answer": "Karena saat deployment, matriks hasil kali BA dapat langsung digabungkan (merged) ke dalam bobot asli W = W_0 + BA, sehingga operasi komputasinya identik dengan model asli tanpa struktur tambahan.",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q018",
            "paper": "lora_hu2021.pdf",
            "category": "unanswerable",
            "question": "Berapa konsumsi daya listrik (kWh) per GPU selama proses fine-tuning LoRA di cluster server?",
            "reference_answer": "Informasi tersebut tidak ditemukan di dalam paper ini, karena paper ini hanya membahas alokasi memori VRAM, parameter size, dan akurasi, bukan konsumsi daya listrik dalam kWh.",
            "source_pages": [],
            "should_refuse": True,
        },

        # --- Paper 4: ResNet (resnet_he2015.pdf) ---
        {
            "id": "q019",
            "paper": "resnet_he2015.pdf",
            "category": "factual",
            "question": "Apa formulasi pemetaan residual F(x) yang dipelajari pada blok residual ResNet?",
            "reference_answer": "Pemetaan residual diformulasikan sebagai F(x) := H(x) - x, sehingga pemetaan asli yang dipulihkan adalah F(x) + x menggunakan shortcut connection.",
            "source_pages": [2],
            "should_refuse": False,
        },
        {
            "id": "q020",
            "paper": "resnet_he2015.pdf",
            "category": "factual",
            "question": "Berapa kedalaman lapisan jaringan ResNet terdalam yang dievaluasi pada dataset ImageNet?",
            "reference_answer": "Jaringan terdalam yang dievaluasi pada ImageNet mencapai 152 lapisan (ResNet-152).",
            "source_pages": [1, 4],
            "should_refuse": False,
        },
        {
            "id": "q021",
            "paper": "resnet_he2015.pdf",
            "category": "factual",
            "question": "Bagaimana susunan 3 lapisan konvolusi pada desain bottleneck untuk ResNet-50/101/152?",
            "reference_answer": "Desain bottleneck menggunakan tumpukan 3 lapisan konvolusi: 1x1, 3x3, dan 1x1, di mana lapisan 1x1 berfungsi mengurangi dan memulihkan dimensi, menyisakan 3x3 sebagai bottleneck dimensi kecil.",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q022",
            "paper": "resnet_he2015.pdf",
            "category": "table_figure",
            "question": "Berdasarkan Tabel 3, berapa Top-1 dan Top-5 error rate yang diperoleh ResNet-152 pada set validasi ImageNet?",
            "reference_answer": "Pada Tabel 3, ResNet-152 mencapai Top-1 Error sebesar 21.43% dan Top-5 Error sebesar 5.71%.",
            "source_pages": [4],
            "should_refuse": False,
        },
        {
            "id": "q023",
            "paper": "resnet_he2015.pdf",
            "category": "reasoning",
            "question": "Mengapa degradasi akurasi pada jaringan konvolusional yang sangat dalam bukan disebabkan oleh overfitting?",
            "reference_answer": "Karena fenomena degradasi tersebut justru ditandai dengan training error yang lebih tinggi pada model yang lebih dalam, bukan hanya penurunan akurasi validasi.",
            "source_pages": [1],
            "should_refuse": False,
        },
        {
            "id": "q024",
            "paper": "resnet_he2015.pdf",
            "category": "unanswerable",
            "question": "Berapa akurasi ResNet ketika digunakan untuk estimasi kedalaman (monocular depth estimation) pada dataset NYUv2?",
            "reference_answer": "Informasi tersebut tidak ditemukan di dalam paper ini, karena evaluasi pada paper difokuskan untuk klasifikasi ImageNet, deteksi objek COCO/PASCAL VOC, bukan estimasi kedalaman NYUv2.",
            "source_pages": [],
            "should_refuse": True,
        },

        # --- Paper 5: RAG (rag_lewis2020.pdf) ---
        {
            "id": "q025",
            "paper": "rag_lewis2020.pdf",
            "category": "factual",
            "question": "Apa perbedaan mendasar antara model RAG-Sequence dan RAG-Token?",
            "reference_answer": "RAG-Sequence menggunakan dokumen yang sama untuk menghasilkan seluruh urutan token jawaban, sedangkan RAG-Token dapat memilih dokumen laten yang berbeda untuk setiap token target yang digenerasi.",
            "source_pages": [2],
            "should_refuse": False,
        },
        {
            "id": "q026",
            "paper": "rag_lewis2020.pdf",
            "category": "factual",
            "question": "Komponen model apa yang digunakan sebagai retriever dan generator pada arsitektur RAG?",
            "reference_answer": "Retriever menggunakan Dense Passage Retriever (DPR) berbasis bi-encoder BERT, sedangkan generator menggunakan model seq2seq BART-large (400M parameter).",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q027",
            "paper": "rag_lewis2020.pdf",
            "category": "factual",
            "question": "Berapa jumlah passage dan dump Wikipedia apa yang digunakan sebagai indeks non-parametrik pada RAG?",
            "reference_answer": "Indeks non-parametrik menggunakan dump Wikipedia Desember 2018 yang dibagi menjadi 21 juta potongan teks (passages) masing-masing 100 kata.",
            "source_pages": [3],
            "should_refuse": False,
        },
        {
            "id": "q028",
            "paper": "rag_lewis2020.pdf",
            "category": "table_figure",
            "question": "Berdasarkan Tabel 1, berapa skor Exact Match (EM %) yang diraih RAG-Sequence pada dataset CuratedTREC?",
            "reference_answer": "Pada Tabel 1, RAG-Sequence mencapai skor Exact Match 52.2% pada CuratedTREC.",
            "source_pages": [4],
            "should_refuse": False,
        },
        {
            "id": "q029",
            "paper": "rag_lewis2020.pdf",
            "category": "reasoning",
            "question": "Mengapa model RAG tetap dapat menghasilkan jawaban yang salah meskipun telah menggunakan retrieval dokumen faktual?",
            "reference_answer": "Karena jika dokumen yang terambil memuat informasi yang kontradiktif atau kurang relevan, generator masih dapat menghasilkan jawaban yang tampak meyakinkan namun tidak akurat.",
            "source_pages": [5],
            "should_refuse": False,
        },
        {
            "id": "q030",
            "paper": "rag_lewis2020.pdf",
            "category": "unanswerable",
            "question": "Berapa nilai Cross-Entropy Loss model RAG ketika dilatih pada corpus percakapan Reddit Comment Dataset?",
            "reference_answer": "Informasi tersebut tidak ditemukan di dalam paper ini, karena indeks retrieval RAG dibangun dari Wikipedia dan dievaluasi pada dataset tanya jawab seperti NQ, TriviaQA, WQ, dan Jeopardy, bukan Reddit.",
            "source_pages": [],
            "should_refuse": True,
        },
    ]

    dataset_path = eval_dir / "dataset.jsonl"
    with open(dataset_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in dataset)

    print(f"Generated dataset: {dataset_path} ({len(dataset)} butir pertanyaan)")
    return dataset


def main():
    eval_dir = Path(__file__).resolve().parent
    papers_info = create_eval_pdfs(eval_dir)

    metadata_path = eval_dir / "papers_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        clean_metadata = {
            k: {
                "title": v["title"],
                "authors": v["authors"],
                "arxiv_id": v["arxiv_id"],
                "domain": v["domain"],
                "character": v["character"],
                "page_count": len(v["pages"]),
            }
            for k, v in papers_info.items()
        }
        json.dump(clean_metadata, f, indent=2, ensure_ascii=False)
    print(f"Saved metadata: {metadata_path}")

    dataset = create_eval_dataset(eval_dir)

    # Print summary statistics
    cat_counts = {}
    for item in dataset:
        cat = item["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print("\n" + "=" * 50)
    print("STATISTIK DATASET EVALUASI:")
    print("=" * 50)
    print(f"Total Pertanyaan: {len(dataset)}")
    for cat, count in cat_counts.items():
        print(f"  - Kategori '{cat}': {count} pertanyaan")
    print("=" * 50)


if __name__ == "__main__":
    main()
