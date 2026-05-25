CLASSIFICATION_PROMPT = """You are a knowledge base classification assistant.
Read the knowledge text and return strict JSON only.

Required JSON schema:
{{
  "business_domain": "customer_service|product|policy|sales|technical|hr|finance|operations|general",
  "knowledge_type": "faq|policy|procedure|case|product_doc|announcement|troubleshooting|document",
  "importance": "low|medium|high",
  "expire_at": "YYYY-MM-DD or null",
  "tags": ["short keywords"],
  "summary": "one sentence summary",
  "confidence": 0.0,
  "needs_review": true
}}

Rules:
- Use null for expire_at when the text has no clear expiration.
- Set needs_review to true when confidence is lower than 0.65.
- Do not add markdown fences or comments.

Knowledge text:
{text}
"""

QUERY_REWRITE_PROMPT = """Rewrite the user query into a clear standalone retrieval query.
Return strict JSON only:
{{
  "rewritten_query": "...",
  "keywords": ["..."],
  "intent": "..."
}}

User query:
{question}
"""

RERANK_PROMPT = """You are ranking retrieved knowledge snippets for a RAG system.
Return strict JSON only:
{{
  "ranked_ids": ["id1", "id2"]
}}

Question:
{question}

Candidates:
{candidates}
"""

HYDE_PROMPT = """Write a concise hypothetical answer that would help retrieve relevant internal knowledge.
Return plain text only, no markdown.

Question:
{question}
"""

CONFLICT_DETECTION_PROMPT = """You are checking whether a new knowledge item conflicts with existing knowledge.
Return strict JSON only:
{{
  "has_conflict": false,
  "severity": "none|low|medium|high",
  "conflicting_ids": ["id"],
  "reason": "short explanation"
}}

New knowledge:
{new_text}

Existing candidates:
{candidates}
"""

DIRECT_ANSWER_PROMPT = """Answer the user question directly.
If the question requires private company knowledge that is not present in the prompt, state that the information is not available.

Question:
{question}

Answer:
"""

ANSWER_PROMPT_TEMPLATE = """You are a knowledge-grounded assistant. Answer using only the provided context.
If the context is insufficient, say what is missing instead of guessing.

Question:
{question}

Context:
{context}

Answer:
"""
