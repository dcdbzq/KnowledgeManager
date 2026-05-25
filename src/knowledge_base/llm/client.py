import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.request
from typing import Any

from ..config import Settings
from .prompts import (
    CLASSIFICATION_PROMPT,
    CONFLICT_DETECTION_PROMPT,
    DIRECT_ANSWER_PROMPT,
    HYDE_PROMPT,
    QUERY_REWRITE_PROMPT,
    RERANK_PROMPT,
)


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.enable_llm and bool(self.settings.llm_api_key.strip())

    def classify(self, text: str) -> dict[str, Any]:
        if self.enabled:
            try:
                prompt = CLASSIFICATION_PROMPT.format(text=text[:6000])
                raw = self._chat(prompt, temperature=0.1)
                parsed = self._parse_json(raw)
                if parsed:
                    return parsed
            except Exception as exc:
                print(f"[knowledge_base] classification API failed, fallback classifier is used: {exc}")
        return self._fallback_classify(text)

    def rewrite_query(self, question: str) -> dict[str, Any]:
        if self.enabled and self.settings.enable_query_rewrite:
            try:
                prompt = QUERY_REWRITE_PROMPT.format(question=question)
                raw = self._chat(prompt, temperature=0.1)
                parsed = self._parse_json(raw)
                if parsed:
                    return parsed
            except Exception as exc:
                print(f"[knowledge_base] query rewrite API failed, original query is used: {exc}")
        return {
            "rewritten_query": question,
            "keywords": self.extract_keywords(question),
            "intent": "retrieve_knowledge",
        }

    def rerank(self, question: str, candidates: list[dict[str, Any]]) -> list[str]:
        if not self.enabled or not self.settings.enable_rerank or not candidates:
            return [item["id"] for item in candidates]
        compact = [
            {"id": item["id"], "summary": item.get("summary", ""), "text": item.get("text", "")[:600]}
            for item in candidates[:8]
        ]
        prompt = RERANK_PROMPT.format(
            question=question,
            candidates=json.dumps(compact, ensure_ascii=False),
        )
        try:
            raw = self._chat(prompt, temperature=0.0)
            parsed = self._parse_json(raw)
            if parsed and isinstance(parsed.get("ranked_ids"), list):
                return [str(item) for item in parsed["ranked_ids"]]
        except Exception as exc:
            print(f"[knowledge_base] rerank API failed, score order is used: {exc}")
        return [item["id"] for item in candidates]

    def embed(self, text: str) -> list[float]:
        if self.enabled and self.settings.enable_embedding_api:
            try:
                url = self.settings.llm_base_url.rstrip("/") + "/embeddings"
                payload = {"model": self.settings.embedding_model, "input": text}
                if self.settings.embedding_dimensions:
                    payload["dimensions"] = self.settings.embedding_dimensions
                data = self._post_json(url, payload, timeout=30)
                return data["data"][0]["embedding"]
            except Exception as exc:
                print(f"[knowledge_base] embedding API failed, fallback embedding is used: {exc}")
                pass
        return self._fallback_embed(text)

    def generate_hyde(self, question: str) -> str:
        if self.enabled and self.settings.enable_hyde:
            try:
                return self._chat(HYDE_PROMPT.format(question=question), temperature=0.2).strip()
            except Exception as exc:
                print(f"[knowledge_base] HyDE API failed, HyDE is skipped: {exc}")
        return ""

    def detect_conflict(self, new_text: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.enabled or not self.settings.enable_conflict_check or not candidates:
            return {"has_conflict": False, "severity": "none", "conflicting_ids": [], "reason": ""}
        compact = [
            {"id": item["id"], "summary": item.get("summary", ""), "text": item.get("text", "")[:800]}
            for item in candidates[:5]
        ]
        try:
            prompt = CONFLICT_DETECTION_PROMPT.format(
                new_text=new_text[:3000],
                candidates=json.dumps(compact, ensure_ascii=False),
            )
            parsed = self._parse_json(self._chat(prompt, temperature=0.0))
            if parsed:
                return {
                    "has_conflict": bool(parsed.get("has_conflict", False)),
                    "severity": str(parsed.get("severity", "none")),
                    "conflicting_ids": list(parsed.get("conflicting_ids", [])),
                    "reason": str(parsed.get("reason", "")),
                }
        except Exception as exc:
            print(f"[knowledge_base] conflict detection API failed, conflict check is skipped: {exc}")
        return {"has_conflict": False, "severity": "none", "conflicting_ids": [], "reason": ""}

    def answer_direct(self, question: str) -> str:
        if not self.enabled:
            return "LLM API is disabled; direct answer was not generated."
        try:
            return self._chat(DIRECT_ANSWER_PROMPT.format(question=question), temperature=0.2).strip()
        except Exception as exc:
            return f"Direct LLM answer failed: {exc}"

    def answer_with_prompt(self, prompt: str) -> str:
        if not self.enabled:
            return "LLM API is disabled; RAG answer was not generated."
        try:
            return self._chat(prompt, temperature=0.2).strip()
        except Exception as exc:
            return f"RAG answer failed: {exc}"

    def extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]{2,}", text.lower())
        stopwords = {"the", "and", "for", "with", "如何", "什么", "是否", "一个", "这个"}
        result = []
        for word in words:
            if word in stopwords or len(word) < 2:
                continue
            if word not in result:
                result.append(word)
        return result[:12]

    def _chat(self, prompt: str, temperature: float) -> str:
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        data = self._post_json(url, payload, timeout=60)
        return data["choices"][0]["message"]["content"]

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

    def _post_json(self, url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        attempts = max(1, self.settings.api_retry_attempts)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")
                last_error = RuntimeError(f"LLM API request failed: {exc.code} {detail}")
                if exc.code not in {408, 409, 425, 429, 500, 502, 503, 504}:
                    raise last_error from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                last_error = RuntimeError(f"LLM API request failed: {exc}")

            if attempt < attempts:
                time.sleep(self.settings.api_retry_backoff_seconds * attempt)
        raise last_error or RuntimeError("LLM API request failed")

    def _parse_json(self, raw: str) -> dict[str, Any] | None:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def _fallback_classify(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        domain = "general"
        domain_rules = {
            "customer_service": ["客服", "客户", "退款", "投诉", "工单", "售后"],
            "product": ["产品", "功能", "版本", "套餐", "规格"],
            "policy": ["制度", "政策", "规范", "合规", "审批"],
            "sales": ["销售", "报价", "合同", "商机", "续费"],
            "technical": ["api", "接口", "故障", "部署", "数据库", "报错"],
            "hr": ["员工", "请假", "入职", "绩效", "薪酬"],
            "finance": ["发票", "付款", "报销", "预算", "账单"],
            "operations": ["运营", "活动", "流程", "排班", "库存"],
        }
        scores = {}
        for candidate, keywords in domain_rules.items():
            hit_count = sum(1 for keyword in keywords if keyword in lowered)
            first_pos = min((lowered.find(keyword) for keyword in keywords if keyword in lowered), default=10**9)
            scores[candidate] = (hit_count, -first_pos)
        best_domain, (best_score, _position_score) = max(scores.items(), key=lambda item: item[1])
        if best_score > 0:
            domain = best_domain

        knowledge_type = "document"
        if "问" in text and "答" in text:
            knowledge_type = "faq"
        elif any(word in text for word in ["步骤", "流程", "操作"]):
            knowledge_type = "procedure"
        elif any(word in text for word in ["制度", "政策", "规范"]):
            knowledge_type = "policy"
        elif any(word in lowered for word in ["故障", "报错", "troubleshoot"]):
            knowledge_type = "troubleshooting"

        importance = "high" if any(word in text for word in ["必须", "严禁", "高优先级", "紧急"]) else "medium"
        tags = self.extract_keywords(text)
        summary = re.sub(r"\s+", " ", text.strip())[:120]
        confidence = 0.62 if domain == "general" else 0.72
        return {
            "business_domain": domain,
            "knowledge_type": knowledge_type,
            "importance": importance,
            "expire_at": None,
            "tags": tags[:6],
            "summary": summary,
            "confidence": confidence,
            "needs_review": confidence < 0.65,
        }

    def _fallback_embed(self, text: str) -> list[float]:
        dims = self.settings.vector_dimensions
        vector = [0.0] * dims
        tokens = self.extract_keywords(text)
        if not tokens:
            tokens = [text[i : i + 2] for i in range(max(0, len(text) - 1))]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
