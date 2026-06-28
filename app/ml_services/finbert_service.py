"""
FinBERT sentiment analysis service.

Loads the ProsusAI/finbert model (HuggingFace) and performs batched
sentiment inference on financial news headlines.

Architecture:
  - Model is loaded once on service instantiation.
  - Inference is batched for GPU efficiency.
  - Results are stored in PostgreSQL and linked in Neo4j.
  - High-confidence negative/positive signals trigger notifications.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import List, Optional

from app.core.logging import get_logger
from app.core.exceptions import MLModelError
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)


class SentimentResult:
    """Typed result from FinBERT inference."""

    __slots__ = ("label", "score", "positive", "negative", "neutral")

    def __init__(
        self,
        label: str,
        score: float,
        positive: float,
        negative: float,
        neutral: float,
    ) -> None:
        self.label = label
        self.score = score  # Signed: positive=+, negative=-, neutral=0
        self.positive = positive
        self.negative = negative
        self.neutral = neutral


class FinBERTService:
    """
    Financial news sentiment analysis using FinBERT.

    FinBERT is a domain-adapted BERT model fine-tuned on financial text.
    It outperforms generic sentiment models on financial corpora by ~8-12%.

    Usage:
        service = FinBERTService()
        results = await service.analyze_batch(["Apple Q4 beats estimates", ...])
    """

    _model = None
    _tokenizer = None
    _pipeline = None

    def __init__(self) -> None:
        self._model_name = settings.ml.finbert_model
        self._device = settings.ml.device
        self._alert_threshold = settings.ml.sentiment_alert_threshold

    def _load_model(self) -> None:
        """Lazy-load the FinBERT model (deferred to first inference call)."""
        if self._pipeline is not None:
            return

        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
            import torch

            logger.info("Loading FinBERT model", model=self._model_name)

            tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            model = AutoModelForSequenceClassification.from_pretrained(self._model_name)

            device = 0 if (self._device == "cuda" and __import__("torch").cuda.is_available()) else -1

            self._pipeline = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=device,
                top_k=None,  # Return all class probabilities
                truncation=True,
                max_length=512,
            )
            logger.info("FinBERT model loaded successfully")
        except ImportError as exc:
            raise MLModelError("FinBERT", f"transformers package not installed: {exc}")
        except Exception as exc:
            raise MLModelError("FinBERT", f"Model loading failed: {exc}")

    def _compute_signed_score(
        self, positive: float, negative: float, neutral: float
    ) -> float:
        """
        Compute a signed sentiment score in [-1.0, 1.0].

        Formula: positive_prob - negative_prob
        This preserves directionality and magnitude.
        """
        return positive - negative

    async def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Run FinBERT sentiment inference on a list of texts.

        Offloads CPU-bound inference to a thread pool to avoid blocking
        the async event loop.

        Args:
            texts: Financial news headlines or article summaries.

        Returns:
            List of SentimentResult objects.
        """
        if not texts:
            return []

        self._load_model()

        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(
            None, self._run_pipeline, texts
        )

        return [self._parse_result(r) for r in raw_results]

    def _run_pipeline(self, texts: List[str]) -> list:
        """Synchronous pipeline call (runs in thread pool)."""
        return self._pipeline(texts, batch_size=8)

    def _parse_result(self, raw: list) -> SentimentResult:
        """Parse raw HuggingFace pipeline output into SentimentResult."""
        scores = {item["label"].lower(): item["score"] for item in raw}
        positive = scores.get("positive", 0.0)
        negative = scores.get("negative", 0.0)
        neutral = scores.get("neutral", 0.0)

        # Determine dominant label
        if positive > negative and positive > neutral:
            label = "positive"
        elif negative > positive and negative > neutral:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(
            label=label,
            score=self._compute_signed_score(positive, negative, neutral),
            positive=positive,
            negative=negative,
            neutral=neutral,
        )

    def exceeds_alert_threshold(self, result: SentimentResult) -> bool:
        """
        Check if a sentiment score warrants a notification.

        Alerts fire when sentiment is strongly positive or negative,
        not for neutral signals.
        """
        return abs(result.score) >= self._alert_threshold

    async def analyze_single(self, text: str) -> SentimentResult:
        """Convenience wrapper for single text analysis."""
        results = await self.analyze_batch([text])
        return results[0]


@lru_cache(maxsize=1)
def get_finbert_service() -> FinBERTService:
    """Return singleton FinBERT service."""
    return FinBERTService()
