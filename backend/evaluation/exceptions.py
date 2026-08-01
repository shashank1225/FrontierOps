class EvaluationError(Exception):
    """Base error for evaluation orchestration."""


class EvaluationConfigurationError(EvaluationError):
    """The selected application cannot produce a valid evaluation run."""


class PromptRenderingError(EvaluationError):
    """A prompt template violates FrontierOps rendering constraints."""
