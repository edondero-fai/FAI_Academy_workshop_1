"""Workshop 1: a small Municipal Front-Desk Assistant."""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)
from opentelemetry import trace

#used to load environmental variables from .env
load_dotenv()

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5-mini")
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "municipal-assistant-v1")
DIAGNOSTICS_PATH = Path(
    os.getenv("DIAGNOSTICS_PATH", "diagnostics/model_calls.jsonl")
)

INSTRUCTIONS = """You are a concise, helpful municipal front-desk assistant.

Answer the resident's service question in plain language. Explain practical next steps and
which municipal office or official channel they should contact when relevant. Do not invent
local rules, fees, opening hours, addresses, phone numbers, deadlines, or eligibility
requirements. If the answer depends on the resident's municipality or missing details, say
what must be verified with the municipality. Clearly state that emergencies should be
directed to the local emergency services. Do not claim that you completed an application,
booking, payment, or other real-world action."""

tracer = trace.get_tracer(__name__)


class ConfigurationError(ValueError):
    """Raised when a required setting is missing or invalid."""


class AssistantError(RuntimeError):
    """Raised when the model call fails."""

    def __init__(self, family: str, message: str) -> None:
        super().__init__(message)
        self.family = family


def write_diagnostic(path: Path, event: dict) -> None:
    """Append one JSON event to the diagnostic file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def error_message(exc: Exception) -> tuple[str, str]:
    """Translate the expected OpenAI SDK errors into readable messages."""
    if isinstance(exc, AuthenticationError):
        return "authentication", "Authentication failed. Check OPENAI_API_KEY."
    if isinstance(exc, RateLimitError):
        return "rate_limit", "The API rate or quota limit was reached. Wait and retry."
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return (
            "connection_or_timeout",
            "The API could not be reached. Check network, proxy, DNS, and firewall settings.",
        )
    if isinstance(exc, BadRequestError):
        return "malformed_request", f"The API rejected the request: {exc}"
    return "unexpected", f"Unexpected model-call failure: {exc}"


def model_call(
    query: str,
    request_id: str,
    api_client=None,
    diagnostics_path: Path | None = None,
) -> str:
    """Send one request to the model and return its text output."""
    path = diagnostics_path or DIAGNOSTICS_PATH
    start = time.time()

    event = {
        "event": "model_call",
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "prompt_version": PROMPT_VERSION,
        "input_context": {"instructions": INSTRUCTIONS, "user_input": query},
        "model": {"requested": MODEL_NAME, "resolved": None},
        "raw_response": None,
        "usage": None,
        "outcome": "error",
        "error": None,
    }

    try:
        client = api_client or OpenAI()
        response = client.responses.create(
            model=MODEL_NAME,
            instructions=INSTRUCTIONS,
            input=query,
        )
        event["model"]["resolved"] = response.model
        event["raw_response"] = response.model_dump(mode="json")
        event["usage"] = response.usage.model_dump(mode="json")

        answer = response.output_text.strip()
        if not answer:
            raise AssistantError(
                "malformed_response",
                "The API response contained no usable text. Inspect the diagnostic event.",
            )

        event["output_text"] = answer
        event["outcome"] = "success"
        return answer
    except AssistantError as exc:
        event["error"] = {
            "type": type(exc).__name__,
            "family": exc.family,
            "message": str(exc),
        }
        raise
    except Exception as exc:
        family, message = error_message(exc)
        technical_message = str(exc)
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            technical_message = technical_message.replace(api_key, "[REDACTED]")
        event["error"] = {
            "type": type(exc).__name__,
            "family": family,
            "message": technical_message,
        }
        raise AssistantError(family, message) from exc
    finally:
        event["latency_ms"] = round((time.time() - start) * 1000, 3)
        write_diagnostic(path, event)


def setup_tracing() -> None:
    """Configure Phoenix and instrument the OpenAI client."""
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from phoenix.otel import register

    tracer_provider = register(
        project_name=os.getenv("PHOENIX_PROJECT", "municipal-front-desk"),
        endpoint=os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
    )
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)


def answer_question(
    query: str,
    request_id: str | None = None,
    api_client=None,
    diagnostics_path: Path | None = None,
) -> str:
    """Run the complete municipal question-answering path."""
    if not query.strip():
        raise ConfigurationError("The municipal question must not be empty.")
    if api_client is None and not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your own key."
        )

    request_id = request_id or str(uuid.uuid4())

    with tracer.start_as_current_span("municipal_front_desk.request") as span:
        span.set_attribute("municipal.request_id", request_id)
        span.set_attribute("municipal.prompt_version", PROMPT_VERSION)
        try:
            answer = model_call(query.strip(), request_id, api_client, diagnostics_path)
        except AssistantError as exc:
            span.set_attribute("municipal.outcome", "error")
            span.set_attribute("municipal.error_family", exc.family)
            raise
        span.set_attribute("municipal.outcome", "success")
        return answer


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ask one question of the Municipal Front-Desk Assistant."
    )
    parser.add_argument("query", nargs="+", help="municipal service-desk question")
    parser.add_argument("--request-id", help="identifier included in diagnostics")
    parser.add_argument("--no-tracing", action="store_true", help="do not export Phoenix traces")
    args = parser.parse_args()

    try:
        if not args.no_tracing:
            setup_tracing()
        answer = answer_question(" ".join(args.query), args.request_id)
    except (ConfigurationError, AssistantError) as exc:
        print(f"Error [{getattr(exc, 'family', 'configuration')}]: {exc}", file=sys.stderr)
        return 2

    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
