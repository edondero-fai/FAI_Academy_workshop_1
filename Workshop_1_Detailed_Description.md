# Workshop 1 — The Smallest Runnable Product

**One request in, one response out, every call diagnosable**

*Duration: 6 instructional hours · Module 1 · Lecture 1 foundations + Lecture 2*

## Introduction and situation

The municipality needs an initial proof of life for a **Municipal Front-Desk Assistant**: a small application that accepts a routine service-desk question, sends it to a language model and returns a usable response. At this stage, answer depth and factual correctness are not the principal assessment target. The priority is engineering readiness: a new machine must be able to reproduce the run, a second pair must understand the project without oral handover, and failures must leave enough evidence to diagnose what happened.

This first workshop establishes the operating habits used throughout the programme. Participants work in pairs and keep progress visible in one continuously runnable vertical slice. The environment is isolated from the host system; dependencies and runtime settings are explicit; secrets remain outside source code; and every model interaction is observable. The workshop treats the model as one component in a four-part application—**prompt, model call, response and application logic**—rather than as a self-contained product. That framing helps participants distinguish model behaviour from errors in configuration, networking, request construction or response handling.

## Objectives

By the end of the day, participants will be able to:

- prepare and verify an isolated Python development environment suitable for AI-assisted development, using WSL/Ubuntu where applicable, VS Code Remote Development and a terminal-based workflow;
- manage a Python project with `uv`, a pinned dependency set and a documented, repeatable command surface;
- protect credentials through environment-based configuration, a local `.env`, a shareable `.env.example` and an appropriate `.gitignore`;
- explain and demonstrate the complete request lifecycle: assemble context, invoke the OpenAI Responses API, read the structured response and pass the output to application logic;
- recognise and surface authentication, rate-limit, connection/timeout and malformed-request or malformed-response failures without silent crashes;
- capture sufficient structured evidence to reconstruct every model call, including prompt version, model identifier, decoding settings, raw response, token usage, latency and error state; and
- demonstrate liveness with a small fixed smoke-test set and transfer operation of the system to another pair.

## What participants build

### 1. Reproducible repository and safe configuration

The pair creates a minimal repository with one documented entry point and a small, intelligible project layout. Runtime configuration is externalised: the API key is read from `OPENAI_API_KEY`, model and generation settings are configurable, and no credential appears in source, logs, screenshots or commits. The repository records its Python requirement and locked dependencies so that `uv` can recreate the same environment on another workstation. A README names the supported setup, the command used to run the assistant and the expected proof-of-life behaviour.

### 2. Minimal request-to-response path

The application exposes a command-line interface that accepts one municipal service-desk query and returns the model's text response. The implementation uses the OpenAI Python SDK and the Responses API. It keeps the stable instruction separate from the user's input and reads the result from the response object rather than assuming the transport returns plain text. The activity remains intentionally narrow: no web interface, persistent conversation, retrieval, structured triage or answer-quality evaluation is introduced.

### 3. Diagnostic visibility and explicit failure states

Every call produces a structured, JSON-compatible diagnostic event. The course observability stack—OpenTelemetry, OpenInference and locally hosted Phoenix—provides the trace view; the event or exported span retains the full input context, raw output, model name/version, decoding parameters, token counts, elapsed time and any typed error. Manual application spans add the municipal request identifier and outcome without mixing instrumentation into the model client. User-facing diagnostics translate the four expected failure families into readable states while preserving technical detail for investigation.

### 4. Smoke test and operational handover

The pair prepares five to ten fixed, realistic municipal prompts that exercise the complete call path. The check establishes liveness and output presence; it does not score factual quality, which belongs to later evaluation work. A short diagnostic guide covers an unsupported Python version, missing dependency, missing or invalid key, and network/proxy blockage. The workshop closes with a cold handover: another pair uses only the repository documentation and supplied configuration placeholders to run a representative query and locate its diagnostic evidence.

## Tools and working conventions

The expected toolchain is Python in an isolated Linux environment (preferably WSL with Ubuntu when participants use Windows), VS Code with Remote Development, Git, `uv`, `.env`/`python-dotenv`, the OpenAI Python SDK and Responses API, OpenTelemetry with OpenInference instrumentation, local Phoenix for trace inspection, and `pytest` for the smoke-test command. Participants use AI coding assistance only inside the isolated workspace, inspect generated changes, avoid granting access to Windows-mounted personal files, and make one bounded change before rerunning the application or smoke test.

## Six-hour flow

| Time  | Activity                              | Required output                                                                              |
|-------|---------------------------------------|----------------------------------------------------------------------------------------------|
| 0.5 h | Entry check and pair setup            | Python/WSL environment, repository access and safe key loading confirmed                     |
| 1.0 h | Repository and configuration design   | Runnable skeleton, locked dependencies, `.env.example`, `.gitignore` and entry command           |
| 1.5 h | Model call and CLI vertical slice     | One municipal query travels from terminal input to a displayed Responses API result          |
| 1.5 h | Observability and failure exercise    | Complete diagnostic event/trace plus readable handling of the four expected failure families |
| 1.0 h | Smoke test and operator documentation | Five-to-ten fixed prompts, one test command, README and four-case diagnostic guide           |
| 0.5 h | Peer acceptance                       | A second pair completes a cold run and identifies the corresponding diagnostic record        |

## Deliverables

- Repository with one documented entry point, pinned dependencies and safe configuration handling.
- CLI that accepts a municipal service-desk question and returns a model response.
- Structured diagnostic evidence for every call, inspectable locally and containing all required fields.
- Five-to-ten fixed smoke-test prompts with a repeatable execution command.
- README and concise diagnostic guide covering the four named setup/runtime failures.

## Acceptance criterion

A second pair can clone or copy the repository, create the documented environment, supply its own key and run one representative query **without author intervention**. A non-empty response is returned; the matching diagnostic record contains the prompt version, model identifier, decoding parameters, raw response, token usage, latency and error field; and each seeded setup failure produces an explicit, readable diagnosis rather than a silent or unexplained crash. No secret is present in tracked files or diagnostic output.

## Andragogical objective

Adult learners benefit from early, visible progress and from practices that increase autonomy. Completing a real end-to-end call creates confidence, while the independent handover makes reproducibility observable rather than aspirational. By diagnosing seeded failures and reconstructing calls from structured evidence, participants learn that reliable LLM development begins with environment control, clear system boundaries and observability—not with repeated prompt guessing. These habits form the foundation for maintainability, evaluation, stability controls and structured outputs in later workshops.
