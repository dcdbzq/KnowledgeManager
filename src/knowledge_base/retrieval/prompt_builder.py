from ..llm.prompts import ANSWER_PROMPT_TEMPLATE
from ..models import RetrievalHit


class PromptBuilder:
    def __init__(self, token_limit: int):
        self.token_limit = token_limit

    def build(self, question: str, hits: list[RetrievalHit]) -> dict[str, object]:
        context_blocks = []
        used_tokens = self._estimate_tokens(question) + 120
        selected = []
        for index, hit in enumerate(hits, start=1):
            block = self._format_block(index, hit)
            block_tokens = self._estimate_tokens(block)
            if used_tokens + block_tokens > self.token_limit:
                continue
            context_blocks.append(block)
            selected.append(hit)
            used_tokens += block_tokens
        context = "\n\n".join(context_blocks)
        prompt = ANSWER_PROMPT_TEMPLATE.format(question=question, context=context)
        return {
            "prompt": prompt,
            "context": context,
            "used_tokens_estimate": used_tokens,
            "selected_ids": [hit.id for hit in selected],
        }

    def _format_block(self, index: int, hit: RetrievalHit) -> str:
        metadata = hit.metadata
        source_id = metadata.extra.get("source_id")
        source = f"{source_id or hit.logical_id} v{hit.version}"
        tags = ", ".join(metadata.tags)
        return (
            f"[{index}] source={source}; domain={metadata.business_domain}; "
            f"type={metadata.knowledge_type}; score={hit.score:.3f}; tags={tags}\n"
            f"{hit.text.strip()}"
        )

    def _estimate_tokens(self, text: str) -> int:
        ascii_count = sum(1 for char in text if ord(char) < 128)
        non_ascii_count = len(text) - ascii_count
        return max(1, ascii_count // 4 + non_ascii_count // 2)
