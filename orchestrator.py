from auditmate.agents.definitions import AGENT_DEFINITIONS, SYNTHESIZER_SYSTEM, AgentDefinition
from auditmate.agents.runner import run_agent_sync, run_synthesizer
from auditmate.cli.main import SAMPLE_PITCH, main
from auditmate.core.evaluator import evaluate_pitch
from auditmate.core.reporting import print_report
from auditmate.models.reports import AgentResult, CommitteeReport
from auditmate.providers.catalog import (
    ALL_MODELS,
    CLOUD_MODELS,
    DEFAULT_MODEL_KEY,
    LMSTUDIO_BASE_URL,
    LOCAL_MODELS,
    OPENROUTER_BASE_URL,
    is_local,
    print_available_models,
    provider_for_model,
    resolve_model_id,
)
from auditmate.providers.factory import get_provider_for_model


def get_client_for_model(model_key: str, lmstudio_url: str = LMSTUDIO_BASE_URL):
    return get_provider_for_model(model_key, lmstudio_url).client


if __name__ == "__main__":
    main()

