"""
E: §3 Downstream QA Utility
C: §3 下游 QA 测试 — Downstream QA Utility

Evaluation_Schema.md §3
使用 LLM 执行对照组（原始逐字稿）/ 实验组（仅生成导图）对比评估。
计算 BLEU-4 / ROUGE-L / BERTScore 三者加权综合评分。

Uses LLM for control group (full transcript) / experiment group (generated map only)
comparative evaluation. Computes weighted composite of BLEU-4 / ROUGE-L / BERTScore.
"""
from dataclasses import dataclass, field
from typing import Optional

import json


# E: Lazy import of scoring libs (print warning on missing, don't abort)
# C: 评分库的延迟导入（缺失时打印警告，不中断执行）
_BLEU_AVAILABLE = False
_ROUGE_AVAILABLE = False
_BERTSCORE_AVAILABLE = False


def _init_scoring_libs():
    """E: Initialize all scoring libraries, record availability
    C: 初始化所有评分库，记录可用状态
    """
    global _BLEU_AVAILABLE, _ROUGE_AVAILABLE, _BERTSCORE_AVAILABLE

    try:
        import nltk
        nltk.data.find('tokenizers/punkt') or nltk.download('punkt', quiet=True)
        _BLEU_AVAILABLE = True
    except ImportError:
        print("[QA] nltk 未安装，BLEU-4 不可用 / nltk not installed, BLEU-4 unavailable")
    except LookupError:
        _BLEU_AVAILABLE = True

    try:
        import rouge_score
        _ROUGE_AVAILABLE = True
    except ImportError:
        print("[QA] rouge-score 未安装，ROUGE-L 不可用 / rouge-score not installed, ROUGE-L unavailable")

    try:
        import bert_score
        _BERTSCORE_AVAILABLE = True
    except ImportError:
        print("[QA] bert-score 未安装，BERTScore 不可用 / bert-score not installed, BERTScore unavailable")


@dataclass
class QAMetrics:
    """E: QA test results / C: QA 测试结果"""
    control_accuracy: float = 0.0
    experiment_accuracy: float = 0.0
    qa_retention: float = 0.0
    token_reduction: float = 0.0
    bleu_4: float = 0.0
    rouge_l: float = 0.0
    bert_score: float = 0.0
    qa_composite: float = 0.0
    num_questions: int = 0
    num_runs: int = 0

    def to_dict(self) -> dict:
        return {
            'control_accuracy': round(self.control_accuracy, 4),
            'experiment_accuracy': round(self.experiment_accuracy, 4),
            'qa_retention': round(self.qa_retention, 4),
            'token_reduction': round(self.token_reduction, 4),
            'bleu_4': round(self.bleu_4, 4),
            'rouge_l': round(self.rouge_l, 4),
            'bert_score': round(self.bert_score, 4),
            'qa_composite': round(self.qa_composite, 4),
            'num_questions': self.num_questions,
            'num_runs': self.num_runs,
        }


def _exact_match_accuracy(answers: list[str], gold_answers: list[str]) -> float:
    """E: Simple accuracy based on exact string matching (always available)
    C: 基于精确字符串匹配的简单准确率（始终可用）
    """
    if not answers or not gold_answers or len(answers) != len(gold_answers):
        return 0.0
    correct = sum(1 for a, g in zip(answers, gold_answers) if a.strip().lower() == g.strip().lower())
    return correct / len(answers)


def _compute_bleu4(references: list[str], hypotheses: list[str]) -> float:
    """E: Compute BLEU-4 / C: 计算 BLEU-4"""
    if not _BLEU_AVAILABLE or not references or not hypotheses:
        return 0.0
    try:
        from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
        scores = []
        cf = SmoothingFunction().method4
        for ref, hyp in zip(references, hypotheses):
            if not ref.strip() or not hyp.strip():
                continue
            score = sentence_bleu([ref.split()], hyp.split(), smoothing_function=cf)
            scores.append(score)
        return sum(scores) / len(scores) if scores else 0.0
    except Exception as e:
        print(f"[QA] BLEU-4 计算失败 / BLEU-4 compute failed: {e}")
        return 0.0


def _compute_rouge_l(references: list[str], hypotheses: list[str]) -> float:
    """E: Compute ROUGE-L / C: 计算 ROUGE-L"""
    if not _ROUGE_AVAILABLE or not references or not hypotheses:
        return 0.0
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=False)
        scores = []
        for ref, hyp in zip(references, hypotheses):
            if not ref.strip() or not hyp.strip():
                continue
            result = scorer.score(ref, hyp)
            scores.append(result['rougeL'].fmeasure)
        return sum(scores) / len(scores) if scores else 0.0
    except Exception as e:
        print(f"[QA] ROUGE-L 计算失败 / ROUGE-L compute failed: {e}")
        return 0.0


def _compute_bert_score(references: list[str], hypotheses: list[str]) -> float:
    """E: Compute BERTScore / C: 计算 BERTScore"""
    if not _BERTSCORE_AVAILABLE or not references or not hypotheses:
        return 0.0
    try:
        import torch
        if not torch.cuda.is_available():
            print("[QA] BERTScore 使用 CPU 模式（可能较慢）/ BERTScore using CPU mode (may be slow)")
        from bert_score import score
        P, R, F1 = score(hypotheses, references, lang="en", verbose=False)
        return float(F1.mean())
    except Exception as e:
        print(f"[QA] BERTScore 计算失败 / BERTScore compute failed: {e}")
        return 0.0


def _serialize_map_to_text(gen_map_nodes: list[dict]) -> str:
    """E: Serialize mind map nodes to text
    C: 将导图节点序列化为文本
    """
    lines = []
    # E: Build id-to-node mapping for hierarchy display
    # C: 构建 id → node 映射，用于层级展示
    node_map = {n.get('id', ''): n for n in gen_map_nodes}
    parent_map = {}
    for n in gen_map_nodes:
        pid = n.get('parent_id')
        if pid:
            parent_map[n['id']] = pid

    def _depth(nid: str, cache: dict = None) -> int:
        if cache is None:
            cache = {}
        if nid in cache:
            return cache[nid]
        p = parent_map.get(nid)
        if p is None:
            cache[nid] = 0
        else:
            cache[nid] = _depth(p, cache) + 1
        return cache[nid]

    for n in gen_map_nodes:
        nid = n.get('id', '')
        label = n.get('label', '')
        depth = _depth(nid)
        prefix = "  " * depth + "- "
        line = f"{prefix}{label}"
        lines.append(line)
        details = n.get('details', [])
        for d in details:
            lines.append(f"  {'' * depth}    [{d}]")

    return "\n".join(lines)


def _call_llm_for_qa(client, model: str, system_prompt: str, user_content: str) -> list[str]:
    """E: Call LLM to answer questions, return answer list
    C: 调用 LLM 回答问题，返回答案列表
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()

        # E: Parse answers (one per line, or Q:/A: format)
        # C: 解析答案（每行一个答案，或 Q:/A: 格式）
        answers = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # E: Skip question lines / C: 跳过问题行
            if line.startswith("Q:") or line.startswith("Q"):
                continue
            if line.startswith("A:") or line.startswith("A"):
                line = line[2:].strip()
            answers.append(line)

        # E: If empty after parsing, try splitting by blank lines
        # C: 如果解析后为空，尝试按空行分割
        if not answers:
            segments = [s.strip() for s in raw.split("\n\n") if s.strip()]
            answers = segments

        return answers

    except Exception as e:
        print(f"[QA] LLM 调用失败 / LLM call failed: {e}")
        return []


class QAEvaluator:
    """
    E: Downstream QA evaluator
    C: 下游 QA 评估器

    需要提供 / Requires:
        - 原始逐字稿全文 (transcript) / Full transcript text
        - 10 道测验题 (questions) / 10 quiz questions
        - LLM API 访问 (复用 Config.LLM_*) / LLM API access (reuses Config.LLM_*)

    用法 / Usage:
        evaluator = QAEvaluator()
        result = evaluator.evaluate(transcript, gen_map_nodes, questions)
    """

    def __init__(self, llm_config: Optional[dict] = None):
        """
        E: Initialize QA evaluator
        C: 初始化 QA 评估器

        参数 / Args:
            llm_config: LLM 配置字典（可选），未提供时从 Config 自动读取。
                        LLM config dict (optional), auto-reads from Config when not provided.
        """
        # E: Initialize scoring libraries / C: 初始化评分库
        _init_scoring_libs()

        # E: Initialize LLM client / C: 初始化 LLM 客户端
        self.client = None
        self.model = ""
        self._initialized = False

        if llm_config:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=llm_config.get('api_key'),
                    base_url=llm_config.get('base_url'),
                )
                self.model = llm_config.get('model', '')
                self._initialized = True
            except Exception as e:
                print(f"[QA] LLM 客户端初始化失败 / LLM client init failed: {e}")
        else:
            try:
                from config import Config
                if Config.LLM_API_KEY:
                    from openai import OpenAI
                    self.client = OpenAI(
                        api_key=Config.LLM_API_KEY,
                        base_url=Config.LLM_BASE_URL,
                    )
                    self.model = Config.LLM_MODEL
                    self._initialized = True
                else:
                    print("[QA] 未配置 LLM_API_KEY，QA 评估不可用")
                    print("[QA] LLM_API_KEY not configured, QA evaluation unavailable")
            except ImportError:
                print("[QA] 无法导入 Config，QA 评估不可用 / Config import failed, QA unavailable")

    def evaluate(
        self,
        transcript: str,
        gen_map_nodes: list[dict],
        questions: list[dict],
    ) -> QAMetrics:
        """
        E: Execute QA comparative evaluation
        C: 执行 QA 对比评估

        流程 / Flow:
        1. 对照组：使用完整逐字稿回答问题
           Control group: answer questions using full transcript
        2. 实验组：仅使用生成导图回答问题
           Experiment group: answer questions using generated map only
        3. 计算 BLEU-4 / ROUGE-L / BERTScore 加权综合分
           Compute weighted composite of BLEU-4 / ROUGE-L / BERTScore
        4. 重复 3 次取均值
           Repeat 3 times and average

        参数 / Args:
            transcript: 原始逐字稿全文 / Full transcript text
            gen_map_nodes: 生成导图节点列表 / Generated map nodes list
            questions: 问题列表 [{id, question, answer}, ...]

        返回 / Returns:
            QAMetrics: QA 评估结果
        """
        if not self._initialized or self.client is None:
            print("[QA] LLM 客户端未初始化，无法执行评估")
            print("[QA] LLM client not initialized, cannot execute evaluation")
            return QAMetrics()

        if not questions:
            print("[QA] 问题集为空，跳过评估 / Question set empty, skipping")
            return QAMetrics()

        # E: Extract question texts and gold answers / C: 提取问题文本和标准答案
        question_texts = [q.get('question', '') for q in questions]
        gold_answers = [q.get('answer', '') for q in questions]
        num_q = len(questions)

        # E: Build System Prompt (§3.4 unified template)
        # C: 构建 System Prompt（§3.4 统一模板）
        system_prompt = (
            "You are a student who has just attended a lecture.\n"
            "Your only source of information is the [provided material].\n"
            "Answer each question based solely on that material.\n"
            "If the material contains no relevant information, respond with\n"
            "\"Cannot determine from the provided material.\" Do not use prior knowledge."
        )

        # E: Serialize map to text / C: 序列化导图文本
        map_text = _serialize_map_to_text(gen_map_nodes)

        # E: Build question list text / C: 构建问题列表文本
        questions_text = "\n".join(
            f"Q{i + 1}: {q}" for i, q in enumerate(question_texts)
        )

        # E: Build user content / C: 构建用户内容
        control_content = (
            f"[Provided Material: Full Transcript]\n\n{transcript}\n\n"
            f"Questions:\n{questions_text}\n\n"
            "Please answer each question concisely and accurately."
        )
        experiment_content = (
            f"[Provided Material: Mind Map Structure]\n\n{map_text}\n\n"
            f"Questions:\n{questions_text}\n\n"
            "Please answer each question concisely and accurately."
        )

        num_runs = 3
        control_all_answers = []
        experiment_all_answers = []

        print(f"[QA] 开始评估 / Starting evaluation: {num_q} 问题/questions, {num_runs} 轮/runs")

        for run_idx in range(num_runs):
            # E: Control group / C: 对照组
            print(f"[QA]  运行 {run_idx + 1}/{num_runs} 对照组 / Control group...")
            control_answers = _call_llm_for_qa(
                self.client, self.model, system_prompt, control_content
            )
            # E: Pad to match question count / C: 补齐长度
            while len(control_answers) < num_q:
                control_answers.append("")
            control_all_answers.append(control_answers[:num_q])

            # E: Experiment group / C: 实验组
            print(f"[QA]  运行 {run_idx + 1}/{num_runs} 实验组 / Experiment group...")
            experiment_answers = _call_llm_for_qa(
                self.client, self.model, system_prompt, experiment_content
            )
            while len(experiment_answers) < num_q:
                experiment_answers.append("")
            experiment_all_answers.append(experiment_answers[:num_q])

        # E: Compute accuracy (exact match) / C: 计算准确率（精确匹配）
        control_accuracies = []
        experiment_accuracies = []
        for run_idx in range(num_runs):
            ca = _exact_match_accuracy(control_all_answers[run_idx], gold_answers)
            ea = _exact_match_accuracy(experiment_all_answers[run_idx], gold_answers)
            control_accuracies.append(ca)
            experiment_accuracies.append(ea)

        avg_control_accuracy = sum(control_accuracies) / num_runs
        avg_experiment_accuracy = sum(experiment_accuracies) / num_runs

        # E: Compute BLEU-4 / ROUGE-L / BERTScore (using concatenated answers across runs)
        # C: 计算 BLEU-4 / ROUGE-L / BERTScore（使用所有轮次的答案拼接）
        all_control_flat = []
        all_experiment_flat = []
        for run_idx in range(num_runs):
            all_control_flat.extend(control_all_answers[run_idx])
            all_experiment_flat.extend(experiment_all_answers[run_idx])

        # E: Repeat gold answers to match multi-run / C: 重复金标准答案以匹配多轮次
        repeated_gold = gold_answers * num_runs

        bleu4 = _compute_bleu4(repeated_gold, all_control_flat)
        rouge_l = _compute_rouge_l(repeated_gold, all_control_flat)
        bert_s = _compute_bert_score(repeated_gold, all_control_flat)

        # E: Weighted composite: 0.3*BLEU-4 + 0.4*ROUGE-L + 0.3*BERTScore
        # C: 加权综合分：0.3*BLEU-4 + 0.4*ROUGE-L + 0.3*BERTScore
        qa_composite = 0.3 * bleu4 + 0.4 * rouge_l + 0.3 * bert_s

        # E: QA retention rate / C: QA 保留率（实验组相对对照组）
        qa_retention = 0.0
        if avg_control_accuracy > 0:
            qa_retention = avg_experiment_accuracy / avg_control_accuracy

        print(f"[QA] 评估完成 / Evaluation complete")
        print(f"[QA]   对照组准确率 / Control accuracy: {avg_control_accuracy:.4f}")
        print(f"[QA]   实验组准确率 / Experiment accuracy: {avg_experiment_accuracy:.4f}")
        print(f"[QA]   综合评分 / Composite: {qa_composite:.4f}")

        # E: Rough token count estimation (4 chars ≈ 1 token for English, 1.5 chars ≈ 1 token for Chinese)
        # C: 粗略 token 估算（英文 4 字符 ≈ 1 token，中文 1.5 字符 ≈ 1 token）
        transcript_len = len(transcript)
        map_text_len = len(map_text)
        # E: Weighted average: if mostly Chinese use 1.5, else 4
        # C: 加权平均：中文为主用 1.5，否则用 4
        zh_chars = sum(1 for ch in transcript if '\u4e00' <= ch <= '\u9fff')
        zh_ratio = zh_chars / max(transcript_len, 1)
        chars_per_token = 1.5 if zh_ratio > 0.3 else 4
        est_transcript_tokens = transcript_len / chars_per_token
        est_map_tokens = map_text_len / chars_per_token
        token_reduction = 1.0 - (est_map_tokens / max(est_transcript_tokens, 1))

        return QAMetrics(
            control_accuracy=avg_control_accuracy,
            experiment_accuracy=avg_experiment_accuracy,
            qa_retention=qa_retention,
            token_reduction=token_reduction,
            bleu_4=bleu4,
            rouge_l=rouge_l,
            bert_score=bert_s,
            qa_composite=qa_composite,
            num_questions=num_q,
            num_runs=num_runs,
        )
