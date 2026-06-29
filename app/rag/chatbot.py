"""
RAG-powered financial chatbot.

Architecture:
  1. DocumentLoader   — loads user financial context + knowledge base
  2. EmbeddingPipeline — embeds chunks with sentence-transformers
  3. VectorStore      — FAISS in-process vector store (ChromaDB for prod)
  4. Retriever        — top-k semantic search
  5. ContextBuilder   — structures user-specific context + retrieved docs
  6. PromptBuilder    — assembles system + user prompt
  7. LLMInterface     — calls open-source LLM (Mistral/Llama via HuggingFace)
  8. ConversationMemory — maintains per-session history (Redis-backed)

The chatbot NEVER fabricates financial data. If user-specific data isn't
available, it clearly states this and answers in general terms only.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.core.exceptions import MLModelError
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)


class ConversationMemory:
    """
    Redis-backed conversation history.

    Keeps last N turns per session_id. Sessions expire after 24 hours.
    """

    MAX_TURNS = 10
    TTL_SECONDS = 86400  # 24 hours

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def _key(self, session_id: str) -> str:
        return f"chat:session:{session_id}"

    async def add_turn(self, session_id: str, role: str, content: str) -> None:
        key = self._key(session_id)
        history = await self.get_history(session_id)
        history.append({"role": role, "content": content})
        if len(history) > self.MAX_TURNS * 2:
            history = history[-(self.MAX_TURNS * 2):]
        await self._redis.setex(key, self.TTL_SECONDS, json.dumps(history))

    async def get_history(self, session_id: str) -> List[Dict]:
        key = self._key(session_id)
        raw = await self._redis.get(key)
        if not raw:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    async def clear(self, session_id: str) -> None:
        await self._redis.delete(self._key(session_id))


class EmbeddingPipeline:
    """
    Sentence-transformer embedding pipeline.

    Uses all-MiniLM-L6-v2 by default — fast, 384-dim, good quality.
    Upgrade to all-mpnet-base-v2 for higher quality (slower).
    """

    _model = None
    _cache: Dict[str, Any] = {}  # In-memory cache for text embeddings

    def __init__(self) -> None:
        self._model_name = settings.ml.embedding_model

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded", model=self._model_name)
        except ImportError:
            raise MLModelError("EmbeddingPipeline", "sentence-transformers not installed")

    def embed(self, texts: List[str]) -> Any:
        """Return numpy embedding matrix for a list of texts."""
        self._load()
        results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            if text in self._cache:
                results.append(self._cache[text])
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)

        if uncached_texts:
            embeddings = self._model.encode(uncached_texts, show_progress_bar=False, convert_to_numpy=True)
            for idx, text, emb in zip(uncached_indices, uncached_texts, embeddings):
                self._cache[text] = emb
                results[idx] = emb

        import numpy as np
        return np.array(results)

    def embed_single(self, text: str) -> Any:
        return self.embed([text])[0]


class FAISSVectorStore:
    """
    In-process FAISS vector store for semantic retrieval.

    For production with millions of documents, replace with ChromaDB
    or Pinecone. FAISS is fine for per-user context (hundreds of chunks).
    """

    def __init__(self, embedding_pipeline: EmbeddingPipeline) -> None:
        self._embedder = embedding_pipeline
        self._index = None
        self._docs: List[str] = []
        self._meta: List[Dict] = []

    def build_index(self, documents: List[str], metadata: List[Dict]) -> None:
        """Embed and index a list of text chunks."""
        try:
            import faiss
            import numpy as np
        except ImportError:
            raise MLModelError("FAISSVectorStore", "faiss-cpu not installed")

        embeddings = self._embedder.embed(documents).astype("float32")
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)  # Inner product (cosine after normalisation)
        faiss.normalize_L2(embeddings)
        self._index.add(embeddings)
        self._docs = documents
        self._meta = metadata

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, Dict, float]]:
        """Return top-k chunks with metadata and similarity scores."""
        if self._index is None or len(self._docs) == 0:
            return []
        import faiss
        import numpy as np
        q_emb = self._embedder.embed_single(query).astype("float32").reshape(1, -1)
        faiss.normalize_L2(q_emb)
        scores, indices = self._index.search(q_emb, min(top_k, len(self._docs)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append((self._docs[idx], self._meta[idx], float(score)))
        return results


class ContextBuilder:
    """
    Assembles the RAG context from user financial data and retrieved documents.
    """

    def build_user_context(self, graph_context: Dict) -> str:
        """Serialise user's financial graph context into a readable text block."""
        parts = []
        user = graph_context.get("user", {})
        if user:
            parts.append(
                f"USER PROFILE: {user.get('full_name', 'User')}, "
                f"risk tolerance: {user.get('risk_tolerance', 'moderate')}, "
                f"currency: {user.get('currency', 'USD')}, "
                f"financial health score: {user.get('financial_health_score', 'N/A')}"
            )

        wallets = graph_context.get("wallets", [])
        if wallets:
            total_cash = sum(w.get("balance", 0) for w in wallets if w)
            parts.append(f"LIQUID ASSETS: ${total_cash:,.2f} across {len(wallets)} account(s)")

        loans = graph_context.get("loans", [])
        if loans:
            loans_clean = [l for l in loans if l]
            total_debt = sum(l.get("balance", 0) for l in loans_clean)
            highest_rate = max((l.get("rate", 0) for l in loans_clean), default=0)
            parts.append(
                f"DEBT: ${total_debt:,.2f} total across {len(loans_clean)} loan(s). "
                f"Highest APR: {highest_rate:.1f}%"
            )

        goals = graph_context.get("goals", [])
        if goals:
            goals_clean = [g for g in goals if g]
            parts.append(
                f"SAVINGS GOALS: {len(goals_clean)} active goal(s). "
                + ", ".join(f"{g.get('name')}: {g.get('current',0)/max(g.get('target',1),1)*100:.0f}% funded"
                            for g in goals_clean[:3])
            )

        investments = graph_context.get("investments", [])
        if investments:
            invs_clean = [i for i in investments if i]
            parts.append(
                f"INVESTMENTS: {len(invs_clean)} holding(s): "
                + ", ".join(i.get("symbol", "") for i in invs_clean[:5])
            )

        portfolio_graph = graph_context.get("portfolio_graph", [])
        if portfolio_graph:
            parts.append("PORTFOLIO ENRICHED DETAILS:")
            for p in portfolio_graph:
                pred_str = f", ML prediction: {p.get('latest_prediction')} (confidence: {p.get('prediction_confidence', 0)*100:.0f}%)" if p.get("latest_prediction") else ""
                sent_str = f", average news sentiment: {p.get('avg_sentiment', 0.0):+.2f}" if p.get("avg_sentiment") is not None else ""
                parts.append(
                    f"  - Symbol: {p.get('a.symbol')} | Name: {p.get('a.name')} | Price: ${p.get('a.current_price', 0):,.2f}"
                    f"{pred_str}{sent_str}"
                )

        debt_arb = graph_context.get("debt_arbitrage", {})
        if debt_arb:
            parts.append(
                f"DEBT ARBITRAGE STATS: Total liquid assets: ${debt_arb.get('total_liquid_assets', 0):,.2f}. "
                f"Risk tolerance: {debt_arb.get('risk_tolerance')}."
            )

        risk_ctx = graph_context.get("risk_context", {})
        if risk_ctx and risk_ctx.get("asset_count", 0) > 0:
            parts.append(
                f"RISK OVERVIEW: {risk_ctx.get('asset_count')} assets across classes {', '.join(risk_ctx.get('asset_types', []))}. "
                f"Total Cash: ${risk_ctx.get('total_cash', 0):,.2f} | Total Debt: ${risk_ctx.get('total_debt', 0):,.2f} | Total Investment Value: ${risk_ctx.get('total_investment_value', 0):,.2f}"
            )

        return "\n".join(parts) if parts else "No financial data available for this user."

    def build_documents(self, graph_context: Dict) -> Tuple[List[str], List[Dict]]:
        """Convert graph context into indexable document chunks."""
        docs, meta = [], []

        for wallet in (graph_context.get("wallets") or []):
            if wallet:
                docs.append(
                    f"Wallet: {wallet.get('name')} | Type: {wallet.get('type')} | "
                    f"Balance: ${wallet.get('balance', 0):,.2f}"
                )
                meta.append({"type": "wallet", "id": wallet.get("id")})

        for loan in (graph_context.get("loans") or []):
            if loan:
                docs.append(
                    f"Loan: {loan.get('name')} | Balance: ${loan.get('balance', 0):,.2f} | "
                    f"APR: {loan.get('rate', 0):.1f}%"
                )
                meta.append({"type": "loan", "id": loan.get("id")})

        for goal in (graph_context.get("goals") or []):
            if goal:
                docs.append(
                    f"Savings goal: {goal.get('name')} | "
                    f"Target: ${goal.get('target', 0):,.2f} | "
                    f"Current: ${goal.get('current', 0):,.2f}"
                )
                meta.append({"type": "goal", "id": goal.get("id")})

        for inv in (graph_context.get("investments") or []):
            if inv:
                docs.append(
                    f"Investment: {inv.get('symbol')} ({inv.get('name')}) | "
                    f"Price: ${inv.get('price', 0):,.2f}"
                )
                meta.append({"type": "investment", "symbol": inv.get("symbol")})

        for p in (graph_context.get("portfolio_graph") or []):
            if p:
                pred_str = f" | Prediction: {p.get('latest_prediction')} ({p.get('prediction_confidence', 0)*100:.0f}% confidence)" if p.get("latest_prediction") else ""
                sent_str = f" | News Sentiment: {p.get('avg_sentiment', 0.0):+.2f}" if p.get("avg_sentiment") is not None else ""
                docs.append(
                    f"Asset: {p.get('a.symbol')} ({p.get('a.name')}) | Price: ${p.get('a.current_price', 0):,.2f}"
                    f"{pred_str}{sent_str}"
                )
                meta.append({"type": "investment_enriched", "symbol": p.get("a.symbol")})

        debt_arb = graph_context.get("debt_arbitrage")
        if debt_arb and debt_arb.get("loans"):
            for l in debt_arb.get("loans"):
                docs.append(
                    f"Debt Arbitrage: Loan '{l.get('name')}' balance ${l.get('balance', 0):,.2f} | "
                    f"APR {l.get('rate', 0):.1f}% | Payment ${l.get('payment', 0):,.2f} | "
                    f"Total liquid assets available for arbitrage: ${debt_arb.get('total_liquid_assets', 0):,.2f}"
                )
                meta.append({"type": "debt_arbitrage", "id": l.get("id")})

        return docs, meta


class PromptBuilder:
    """
    Assembles the final LLM prompt with system context and conversation history.
    """

    SYSTEM_PROMPT = """You are FinAI, a knowledgeable and empathetic personal financial advisor.
You have access to the user's financial data and must provide personalised, accurate advice.

CRITICAL RULES:
1. Never fabricate financial figures. Only reference data you've been given.
2. Always prioritise: emergency fund → high-interest debt → savings goals → investments.
3. Never recommend investments to someone with no emergency fund or crushing debt.
4. Be specific and actionable. Vague advice helps no one.
5. Always explain WHY you're making each recommendation.
6. If you don't have enough data to answer a question, say so clearly.
7. You are NOT a licensed financial advisor. Always recommend consulting a professional for major decisions.

RESPONSE FORMAT:
- Be conversational but professional.
- Use concrete numbers when available.
- Bullet points for lists of actions.
- Keep responses focused (200–500 words unless a detailed breakdown is requested).
"""

    def build(
        self,
        user_context: str,
        retrieved_chunks: List[Tuple[str, Dict, float]],
        conversation_history: List[Dict],
        user_message: str,
    ) -> List[Dict]:
        """Assemble the full message list for the LLM."""
        context_block = f"\n\nUSER FINANCIAL CONTEXT:\n{user_context}"

        if retrieved_chunks:
            relevant = "\n".join(f"- {chunk}" for chunk, _, score in retrieved_chunks if score > 0.3)
            if relevant:
                context_block += f"\n\nRELEVANT CONTEXT:\n{relevant}"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT + context_block}
        ]
        messages.extend(conversation_history[-8:])  # Last 4 turns
        messages.append({"role": "user", "content": user_message})
        return messages


class LLMInterface:
    """
    Interface to open-source LLMs via HuggingFace transformers pipeline.

    Falls back to a template-based response if the model isn't loaded.
    Supports: Mistral-7B, Llama-3-8B, Gemma-7B.
    """

    _pipeline = None

    def __init__(self) -> None:
        self._model_path = settings.ml.llm_model_path
        self._max_new_tokens = 512

    def _load(self) -> bool:
        """Attempt to load LLM. Returns False if model files not present."""
        if self._pipeline is not None:
            return True
        import os
        if not os.path.exists(self._model_path):
            logger.warning("LLM model path not found — using fallback", path=self._model_path)
            return False
        try:
            from transformers import pipeline
            self._pipeline = pipeline(
                "text-generation",
                model=self._model_path,
                max_new_tokens=self._max_new_tokens,
                do_sample=True,
                temperature=0.7,
                repetition_penalty=1.1,
            )
            logger.info("LLM loaded", model=self._model_path)
            return True
        except Exception as exc:
            logger.error("LLM load failed", error=str(exc))
            return False

    def generate(self, messages: List[Dict]) -> str:
        """Generate a response from the LLM given a message list."""
        if not self._load():
            return self._fallback_response(messages)

        # Format messages into a chat template
        prompt = self._format_chat(messages)
        import asyncio
        loop = asyncio.get_event_loop()
        result = self._pipeline(prompt)[0]["generated_text"]
        # Extract only the new generated content
        return result[len(prompt):].strip()

    def _format_chat(self, messages: List[Dict]) -> str:
        """Format messages dynamically into Mistral, Llama, or Gemma templates."""
        model_path_lower = str(self._model_path).lower()
        if "llama-3" in model_path_lower or "llama3" in model_path_lower:
            formatted = "<|begin_of_text|>"
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                formatted += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
            formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
            return formatted
        elif "gemma" in model_path_lower:
            formatted = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                formatted += f"<start_of_turn>{role}\n{content}<end_of_turn>\n"
            formatted += "<start_of_turn>model\n"
            return formatted
        else:
            formatted = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    formatted += f"<s>[INST] {content} [/INST]\n"
                elif role == "user":
                    formatted += f"[INST] {content} [/INST]\n"
                elif role == "assistant":
                    formatted += f"{content}</s>\n"
            return formatted

    def _fallback_response(self, messages: List[Dict]) -> str:
        """Template-based response when LLM is unavailable."""
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return (
            f"I understand you're asking about: '{user_msg[:100]}...'\n\n"
            "The AI model is currently being initialised. In the meantime:\n"
            "• Check your Dashboard for your latest Financial Health Score\n"
            "• Review your Recommendations tab for personalised action items\n"
            "• Ensure your emergency fund covers 3–6 months of expenses first\n\n"
            "The full conversational AI will be available once model loading completes."
        )


class FinancialChatbot:
    """
    Main chatbot orchestrator — wires together all RAG components.

    Usage:
        chatbot = FinancialChatbot(redis_client, graph_service)
        response = await chatbot.chat(
            user_id="...",
            message="Should I pay off my student loan or invest?",
            session_id="...",
        )
    """

    def __init__(self, redis_client: Any, graph_service: Any) -> None:
        self._memory = ConversationMemory(redis_client)
        self._embedder = EmbeddingPipeline()
        self._vector_store = FAISSVectorStore(self._embedder)
        self._context_builder = ContextBuilder()
        self._prompt_builder = PromptBuilder()
        self._llm = LLMInterface()
        self._graph = graph_service

    async def chat(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        include_portfolio_context: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a user message and return a personalised AI response.

        Args:
            user_id: The authenticated user's UUID.
            message: The user's chat message.
            session_id: Conversation session ID (creates new if None).
            include_portfolio_context: Whether to include portfolio data.

        Returns:
            dict with response, session_id, and sources used.
        """
        session_id = session_id or str(uuid.uuid4())

        # 1. Fetch user financial context from Neo4j
        graph_context: Dict = {}
        context_used = []
        if include_portfolio_context:
            graph_context = await self._graph.get_user_financial_context(user_id)
            if graph_context:
                context_used.append("user_financial_graph")

                # Fetch additional sources for a truly multi-source RAG
                from datetime import datetime, timedelta, timezone
                since_time = (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat()

                try:
                    portfolio_graph = await self._graph.get_portfolio_graph(user_id, since=since_time)
                    if portfolio_graph:
                        graph_context["portfolio_graph"] = portfolio_graph
                        context_used.append("portfolio_graph")
                except Exception as exc:
                    logger.warning("Failed to fetch portfolio graph for chat", error=str(exc))

                try:
                    debt_arbitrage = await self._graph.get_debt_arbitrage_context(user_id)
                    if debt_arbitrage:
                        graph_context["debt_arbitrage"] = debt_arbitrage
                        context_used.append("debt_arbitrage")
                except Exception as exc:
                    logger.warning("Failed to fetch debt arbitrage context for chat", error=str(exc))

                try:
                    risk_context = await self._graph.get_risk_scoring_context(user_id)
                    if risk_context:
                        graph_context["risk_context"] = risk_context
                        context_used.append("risk_context")
                except Exception as exc:
                    logger.warning("Failed to fetch risk context for chat", error=str(exc))

        # 2. Build and index documents
        user_context_text = self._context_builder.build_user_context(graph_context)
        docs, meta = self._context_builder.build_documents(graph_context)
        if docs:
            try:
                self._vector_store.build_index(docs, meta)
            except Exception as exc:
                logger.warning("Vector index build failed", error=str(exc))

        # 3. Retrieve relevant chunks
        retrieved = []
        if docs:
            try:
                retrieved = self._vector_store.search(message, top_k=5)
            except Exception as exc:
                logger.warning("Vector search failed", error=str(exc))

        # 4. Load conversation history
        history = await self._memory.get_history(session_id)

        # 5. Build prompt
        messages = self._prompt_builder.build(
            user_context=user_context_text,
            retrieved_chunks=retrieved,
            conversation_history=history,
            user_message=message,
        )

        # 6. Generate response
        import asyncio
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(None, self._llm.generate, messages)

        # 7. Persist turn to memory
        await self._memory.add_turn(session_id, "user", message)
        await self._memory.add_turn(session_id, "assistant", response_text)

        sources = [m.get("type", "") for _, m, _ in retrieved]

        logger.info(
            "Chat response generated",
            user_id=user_id,
            session_id=session_id,
            sources=sources,
        )

        return {
            "response": response_text,
            "session_id": session_id,
            "sources": list(set(sources)),
            "context_used": context_used,
        }
