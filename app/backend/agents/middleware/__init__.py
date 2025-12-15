"""
KidSpark AI middleware for agent processing.
"""

from app.backend.agents.middleware.tracing import TracingMiddleware
from app.backend.agents.middleware.toxicity import ToxicityDetectionMiddleware
from app.backend.agents.middleware.on_topic import OnTopicMiddleware