"""
E: §3 Downstream QA Utility — Refactored audio-driven flow
C: §3 下游 QA 测试 — 重构后的音频驱动流程

Evaluation_Schema.md §3（重构 / Refactored）:
1. 系统引导用户上传音频，并对该音频执行 STT 转录
   System guides the user to upload an audio file and runs STT on it
2. 将 STT 转录结果接入完全独立的 AI（干净对话窗口，不携带任何上下文或历史）
   Feed the STT transcript to a fully independent AI (clean window, no context/history)
3. 该独立 AI 依据音频内容生成 20 个问题，难度由浅入深
   The independent AI generates 20 questions with increasing difficulty
4. 问题交由 mindmap agent：先对音频执行 STT，再仅基于生成的一棵树（导图）回答
   The mindmap agent answers based solely on one generated tree (no other material)
5. AI 对每个回答按 1-5 分评分（以转录为参考答案）
   An AI grades each answer 1-5 (transcript as the reference)
6. 评分综合后计入系统总分（归一化 [0,1] 作为 §7.2 composite 分量）
   Scores are aggregated into the total (normalized [0,1] composite component)

旧实现（BLEU-4 / ROUGE-L / BERTScore 对照组-实验组对比）已被此流程取代。
The legacy control/experiment BLEU-4/ROUGE-L/BERTScore design is replaced.
"""
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from config import Config
from evaluation.i18n import T


@dataclass
class QAMetrics:
    """E: QA test results / C: QA 测试结果"""
    qa_score: float = 0.0          # E: Normalized [0,1] / C: 归一化 [0,1]
    avg_raw_score: float = 0.0     # E: Mean of 1-5 per-answer scores / C: 逐题 1-5 分均值
    num_questions: int = 0
    scores: list[int] = field(default_factory=list)
    per_question: list[dict] = field(default_factory=list)
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            'qa_score': round(self.qa_score, 4),
            'avg_raw_score': round(self.avg_raw_score, 4),
            'num_questions': self.num_questions,
            'scores': self.scores,
            'per_question': self.per_question,
            'total_tokens': self.total_tokens,
        }


def _serialize_map_to_text(gen_map_nodes: list[dict]) -> str:
    """E: Serialize mind map nodes to text (indented hierarchy)
    C: 将导图节点序列化为文本（缩进层级展示）"""
    lines = []
    parent_map = {}
    for n in gen_map_nodes:
        pid = n.get('parent_id')
        if pid:
            parent_map[n.get('id', '')] = pid

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
        lines.append("  " * depth + f"- {label}")
        details = n.get('details', [])
        for d in details:
            lines.append("  " * depth + f"    [{d}]")
    return "\n".join(lines)


class QAEvaluator:
    """
    E: Downstream QA evaluator — refactored audio-driven flow
    C: 下游 QA 评估器 — 重构后的音频驱动流程

    Every AI call uses a brand-new OpenAI client and a single clean message
    list (no accumulated history), satisfying the "fully independent AI"
    requirement. Model defaults to Config.LLM_*; an explicit llm_config dict
    may override api_key / base_url / model.
    每次 AI 调用均使用全新 OpenAI 客户端与单次干净消息列表（不累积历史），
    满足"完全独立 AI"要求。模型默认 Config.LLM_*，可通过 llm_config 覆盖。

    用法 / Usage:
        evaluator = QAEvaluator()
        result = evaluator.evaluate(transcript, gen_map_nodes)
    """

    def __init__(self, llm_config: Optional[dict] = None):
        """
        E: Initialize QA evaluator (config only — clients are created per call)
        C: 初始化 QA 评估器（仅保存配置 — 客户端按调用创建）

        Args / 参数:
            llm_config: LLM 配置字典（可选），未提供时从 Config 自动读取。
                        LLM config dict (optional), auto-reads from Config when not provided.
        """
        self.api_key: str = ""
        self.base_url: Optional[str] = None
        self.model: str = ""
        self._initialized = False

        if llm_config:
            self.api_key = llm_config.get('api_key') or ""
            self.base_url = llm_config.get('base_url') or None
            self.model = llm_config.get('model') or ""
            self._initialized = bool(self.api_key and self.model)
        else:
            try:
                from config import Config
                self.api_key = getattr(Config, 'LLM_API_KEY', '') or ''
                self.base_url = getattr(Config, 'LLM_BASE_URL', '') or None
                self.model = getattr(Config, 'LLM_MODEL', '') or ''
                self._initialized = bool(self.api_key and self.model)
                if not self._initialized:
                    print(T(
                        "[QA] 未配置 LLM_API_KEY / LLM_MODEL，QA 评估不可用",
                        "[QA] LLM_API_KEY / LLM_MODEL not configured, QA evaluation unavailable",
                    ))
            except ImportError:
                print(T(
                    "[QA] 无法导入 Config，QA 评估不可用",
                    "[QA] Config import failed, QA evaluation unavailable",
                ))

    # ---------------------------------------------------------
    # E: Clean-context LLM helpers / C: 干净上下文 LLM 辅助
    # ---------------------------------------------------------
    def _fresh_client(self):
        """E: Brand-new OpenAI client — fully independent, no shared state
        C: 创建全新的 OpenAI 客户端 — 完全独立，无任何共享状态"""
        from openai import OpenAI
        from config import Config
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=getattr(Config, 'API_TIMEOUT', 30),
        )

    def _complete(self, system_prompt: str, user_content: str, max_tokens: int = 2048) -> tuple[str, int]:
        """
        E: Single clean-context chat completion (no history accumulation)
        C: 单次干净上下文补全（不累积任何历史消息）

        Returns (text, total_tokens); total_tokens is 0 when usage is missing.
        返回 (text, total_tokens)；usage 缺失时 total_tokens 为 0。
        """
        client = self._fresh_client()
        # C: 推理模型（DeepSeek v4/Kimi 等）默认开启思考模式导致逐题耗时过长而超时
        #    —— 禁用思考以加快生成/作答/评分，避免 30s 超时。
        # E: Reasoning models default to slow thinking mode which times out on long
        #    Q&A batches — disable it to speed up generation/answer/grading.
        extra_body = {"thinking": {"type": "disabled"}} if Config.LLM_DISABLE_REASONING else None
        try:
            completions_kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.0,
                "max_tokens": max_tokens,
            }
            if extra_body:
                completions_kwargs["extra_body"] = extra_body
            response = client.chat.completions.create(**completions_kwargs)
            text = response.choices[0].message.content.strip()
            tokens = 0
            try:
                usage = getattr(response, 'usage', None)
                if usage is not None:
                    tokens = int(getattr(usage, 'total_tokens', 0) or 0)
            except Exception:
                tokens = 0
            return text, tokens
        except Exception as e:
            print(T(
                f"[QA] LLM 调用失败: {e}",
                f"[QA] LLM call failed: {e}",
            ))
            return "", 0

    # ---------------------------------------------------------
    # E: Step 2-3 — independent AI generates 20 questions (easy → hard)
    # C: 步骤 2-3 — 独立 AI 生成 20 个问题（由浅入深）
    # ---------------------------------------------------------
    def _generate_questions(self, transcript: str) -> tuple[list[dict], int]:
        """
        E: Independent AI generates exactly 20 questions with increasing difficulty
        C: 独立 AI 依据转录生成恰好 20 个难度由浅入深的问题

        Returns (questions, tokens); questions: [{id, difficulty(1-5), question}]
        返回 (questions, tokens)；questions: [{id, difficulty(1-5), question}]
        """
        system_prompt = (
            "You are a course instructor who has just delivered a lecture.\n"
            "Based solely on the provided lecture transcript, generate exactly 20 quiz questions.\n"
            "Questions must progress from easy to hard: difficulty 1 = recall of explicit facts, "
            "difficulty 5 = synthesis / application across the whole lecture.\n"
            "Return ONLY a JSON array, no extra text or markdown fences:\n"
            '[{"id": 1, "difficulty": 1, "question": "..."}, '
            '{"id": 2, "difficulty": 1, "question": "..."}, ...]'
        )
        user_content = f"[Lecture Transcript]\n\n{transcript}"
        raw, tokens = self._complete(system_prompt, user_content, max_tokens=4096)
        questions = self._parse_questions(raw)
        return questions, tokens

    @staticmethod
    def _parse_questions(raw: str) -> list[dict]:
        """E: Robust JSON array extraction from LLM output
        C: 从 LLM 输出中稳健提取 JSON 数组"""
        if not raw:
            return []
        text = raw.strip()
        # E: Strip markdown code fences / C: 去除 markdown 代码围栏
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            # E: Fallback — locate the outermost [...] block / C: 回退 — 定位最外层 [...] 块
            start, end = text.find("["), text.rfind("]")
            if start == -1 or end <= start:
                return []
            try:
                data = json.loads(text[start:end + 1])
            except (json.JSONDecodeError, TypeError):
                return []
        if not isinstance(data, list):
            return []
        questions = []
        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                continue
            q_text = str(item.get("question", "")).strip()
            if not q_text:
                continue
            try:
                difficulty = int(item.get("difficulty", 1))
            except (TypeError, ValueError):
                difficulty = 1
            difficulty = max(1, min(5, difficulty))
            questions.append({"id": i, "difficulty": difficulty, "question": q_text})
            if len(questions) >= 20:
                break
        return questions

    # ---------------------------------------------------------
    # E: Step 4 — mindmap agent answers based ONLY on the generated tree
    # C: 步骤 4 — mindmap agent 仅基于生成的一棵树（导图）回答
    # ---------------------------------------------------------
    def _answer_from_tree(self, questions: list[dict], tree_text: str) -> tuple[list[str], int]:
        """
        E: Answer questions using ONLY the serialized mind map (student prompt,
            prior knowledge prohibited) — no transcript or other material.
        C: 仅使用导图序列化文本回答问题（student prompt，禁止先验知识）—
            不提供转录或其他材料。

        Returns (answers, tokens); answers length == len(questions).
        返回 (answers, tokens)；answers 长度与问题数一致。
        """
        system_prompt = (
            "You are a student who has just attended a lecture.\n"
            "Your only source of information is the [provided mind map].\n"
            "Answer each question based solely on that material.\n"
            "If the material contains no relevant information, respond with "
            "\"Cannot determine from the provided material.\" Do not use prior knowledge.\n"
            'Respond with exactly one answer per line, prefixed "A{id}: ".'
        )
        qtext = "\n".join(f"Q{q['id']}: {q['question']}" for q in questions)
        user_content = (
            f"[Provided Mind Map]\n\n{tree_text}\n\n"
            f"Questions:\n{qtext}\n\n"
            "Please answer each question concisely and accurately."
        )
        raw, tokens = self._complete(system_prompt, user_content, max_tokens=4096)
        answers = self._parse_answers(raw, len(questions))
        return answers, tokens

    @staticmethod
    def _parse_answers(raw: str, count: int) -> list[str]:
        """E: Parse one answer per line (A{n}: ... or bare lines)
        C: 逐行解析答案（A{n}: ... 或裸行）"""
        if not raw:
            return [""] * count
        answers: list[str] = []
        for line in raw.splitlines():
            s = line.strip()
            if not s:
                continue
            # E: Skip question lines / C: 跳过问题行
            if s.startswith("Q") and ":" in s[:4]:
                continue
            # E: Strip "A{n}:" / "A:" prefixes (anchored, so "A1: x" keeps the text)
            # C: 去除 "A{n}:" / "A:" 前缀（锚定匹配，避免误食编号）
            if re.match(r"^A\s*\d*\s*[:.]\s*", s, re.IGNORECASE):
                s = re.sub(r"^A\s*\d*\s*[:.]\s*", "", s, count=1, flags=re.IGNORECASE)
            answers.append(s)
        while len(answers) < count:
            answers.append("")
        return answers[:count]

    # ---------------------------------------------------------
    # E: Step 5 — scoring AI grades each answer 1-5 (transcript as reference)
    # C: 步骤 5 — 评分 AI 以转录为参考答案逐题 1-5 评分
    # ---------------------------------------------------------
    def _score_answers(self, questions: list[dict], answers: list[str], transcript: str) -> tuple[list[int], int]:
        """
        E: Scoring AI grades each answer on a 1-5 scale using the transcript
            as the reference answer.
        C: 评分 AI 以转录为参考答案，逐题按 1-5 分评分。

        Returns (scores, tokens); scores length == len(questions).
        返回 (scores, tokens)；scores 长度与问题数一致。
        """
        system_prompt = (
            "You are a strict grader. Grade each student answer against the provided "
            "lecture transcript on a 1-5 scale:\n"
            "1 = completely wrong or empty, 2 = mostly wrong, 3 = partially correct, "
            "4 = mostly correct, 5 = fully correct and complete.\n"
            "Return ONLY a JSON array of integers, one per question, e.g. [5, 3, 4]."
        )
        items = []
        for q, a in zip(questions, answers):
            items.append(
                f'Q{q["id"]} (difficulty {q["difficulty"]}): {q["question"]}\n'
                f'Answer: {a or "(no answer)"}'
            )
        user_content = (
            f"[Lecture Transcript (reference)]\n\n{transcript}\n\n"
            f"[Q&A]\n\n" + "\n\n".join(items)
        )
        raw, tokens = self._complete(system_prompt, user_content, max_tokens=1024)
        scores = self._parse_scores(raw, len(questions))
        return scores, tokens

    @staticmethod
    def _parse_scores(raw: str, count: int) -> list[int]:
        """E: Robust 1-5 integer array extraction, clamped to [1, 5]
        C: 稳健的 1-5 整数数组提取，并限制在 [1, 5] 范围"""
        if not raw:
            return [1] * count
        # E: Prefer a JSON integer array (grader output) / C: 优先提取 JSON 整数数组
        try:
            start, end = raw.find("["), raw.rfind("]")
            if start != -1 and end > start:
                data = json.loads(raw[start:end + 1])
                if isinstance(data, list):
                    nums = [int(x) for x in data if isinstance(x, (int, float)) and 1 <= x <= 5]
                    scores = nums[:count]
                    while len(scores) < count:
                        scores.append(1)
                    return scores
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        # E: Fallback — bare 1-5 integers anywhere / C: 回退 — 任意位置的裸 1-5 整数
        nums = [int(x) for x in re.findall(r"\b([1-5])\b", raw)]
        scores = nums[:count]
        # E: Missing scores default to 1 (conservative) / C: 缺失评分默认 1 分（保守）
        while len(scores) < count:
            scores.append(1)
        return scores

    # ---------------------------------------------------------
    # E: Main entry / C: 主入口
    # ---------------------------------------------------------
    def evaluate(
        self,
        transcript: str,
        gen_map_nodes: list[dict],
        questions: Optional[list[dict]] = None,
    ) -> QAMetrics:
        """
        E: Execute the refactored audio-driven QA flow
        C: 执行重构后的音频驱动 QA 流程

        流程 / Flow:
        1. questions: auto-generated by an independent AI when not provided
           问题：未提供时由独立 AI 自动生成（20 题，难度由浅入深）
        2. answers: based ONLY on the generated mind map (mindmap agent)
           回答：仅基于生成的导图（mindmap agent 视角）
        3. scores: independent AI grades each answer 1-5 (transcript as reference)
           评分：独立 AI 以转录为参考答案逐题 1-5 评分
        4. aggregate: qa_score = mean(scores) / 5
           汇总：qa_score = 平均分 / 5（归一化 [0,1]）

        Args / 参数:
            transcript: 原始逐字稿全文（STT 结果）/ Full STT transcript
            gen_map_nodes: 生成导图节点列表 / Generated map nodes list
            questions: 可选预置问题 [{id, difficulty, question}]；缺省自动生成
                       Optional preset questions; auto-generated when omitted

        Returns / 返回:
            QAMetrics
        """
        if not self._initialized:
            print(T(
                "[QA] LLM 客户端未初始化，无法执行评估",
                "[QA] LLM client not initialized, cannot execute evaluation",
            ))
            return QAMetrics()

        if not transcript or not transcript.strip():
            print(T(
                "[QA] 转录文本为空，跳过评估",
                "[QA] Transcript empty, skipping evaluation",
            ))
            return QAMetrics()

        if not gen_map_nodes:
            print(T(
                "[QA] 生成导图为空，跳过评估",
                "[QA] Generated map empty, skipping evaluation",
            ))
            return QAMetrics()

        # E: Step 1-3 — independent AI generates 20 questions / 独立 AI 生成 20 题
        if not questions:
            print(T(
                "[QA] 独立 AI 生成问题...",
                "[QA] Independent AI generating 20 questions...",
            ))
            questions, q_tokens = self._generate_questions(transcript)
        else:
            q_tokens = 0
        if not questions:
            print(T(
                "[QA] 问题生成为空，跳过评估",
                "[QA] Question generation empty, skipping evaluation",
            ))
            return QAMetrics()
        num_q = len(questions)
        print(T(
            f"[QA] 问题数: {num_q}",
            f"[QA] Questions: {num_q}",
        ))

        # E: Step 4 — answer based ONLY on the generated tree / 仅基于导图回答
        tree_text = _serialize_map_to_text(gen_map_nodes)
        print(T(
            "[QA] 基于导图回答...",
            "[QA] Answering from the generated map only...",
        ))
        answers, a_tokens = self._answer_from_tree(questions, tree_text)

        # E: Step 5 — scoring AI grades 1-5 with transcript as reference
        # C: 评分 AI 以转录为参考答案逐题 1-5 评分
        print(T(
            "[QA] AI 逐题评分 1-5...",
            "[QA] AI grading each answer 1-5...",
        ))
        scores, s_tokens = self._score_answers(questions, answers, transcript)

        # E: Step 6 — aggregate / 汇总
        avg_raw = sum(scores) / num_q
        per_question = [
            {
                "id": q["id"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "answer": answers[i] if i < len(answers) else "",
                "score": scores[i] if i < len(scores) else 1,
            }
            for i, q in enumerate(questions)
        ]
        total_tokens = q_tokens + a_tokens + s_tokens

        print(T(
            f"[QA] 评估完成: avg raw={avg_raw:.2f}/5, qa_score={avg_raw / 5.0:.4f}, tokens={total_tokens}",
            f"[QA] Evaluation complete: avg raw={avg_raw:.2f}/5, qa_score={avg_raw / 5.0:.4f}, tokens={total_tokens}",
        ))

        return QAMetrics(
            qa_score=round(avg_raw / 5.0, 4),
            avg_raw_score=round(avg_raw, 4),
            num_questions=num_q,
            scores=scores,
            per_question=per_question,
            total_tokens=total_tokens,
        )
