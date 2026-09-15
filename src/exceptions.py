"""Central exception hierarchy and their message templates.

Every domain error the codebase raises lives here so message wording is defined
once and callers import a typed exception instead of constructing ad-hoc
ValueError/RuntimeError with inline strings. The FastAPI layer maps these to
HTTP responses (see apps/api).
"""

from __future__ import annotations


class ResearchAgentError(Exception):
    """Base class for every error this system raises deliberately."""


# --- Provider / configuration --------------------------------------------


class ProviderConfigError(ResearchAgentError):
    """A provider is selected but its required credential/config is missing."""

    TEMPLATE = "{credential} required for {setting}={provider}"

    def __init__(self, credential: str, setting: str, provider: str) -> None:
        super().__init__(self.TEMPLATE.format(
            credential=credential, setting=setting, provider=provider
        ))


class UnknownProviderError(ResearchAgentError):
    """The configured provider name is not one we support."""

    TEMPLATE = "Unknown {setting}: {provider}"

    def __init__(self, setting: str, provider: str) -> None:
        super().__init__(self.TEMPLATE.format(setting=setting, provider=provider))


# --- Evidence graph -------------------------------------------------------


class InvalidRelationshipError(ResearchAgentError):
    """An edge used a relationship verb outside the allowed vocabulary."""

    TEMPLATE = "invalid relationship: {relation}"

    def __init__(self, relation: str) -> None:
        super().__init__(self.TEMPLATE.format(relation=relation))


# --- Authentication -------------------------------------------------------


class AuthenticationError(ResearchAgentError):
    """A request could not be authenticated (bad/missing/expired token)."""

    INVALID_TOKEN = "Invalid or expired authentication token"
    MISSING_TOKEN = "Missing authentication token"
    INVALID_CREDENTIALS = "Incorrect username or password"
    NO_JWT_SECRET = "Server has no JWT secret configured; refusing all requests"


class JobNotFoundError(ResearchAgentError):
    """No research job exists for the given id."""

    MESSAGE = "research job not found"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class JobAccessDeniedError(ResearchAgentError):
    """The caller does not own the research job they addressed."""

    MESSAGE = "you do not have access to this research job"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)
