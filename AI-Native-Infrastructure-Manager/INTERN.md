# 🧠 AI-Assisted Configuration Management: Technical Overview

## 1. Project Philosophy & Architecture

This project implements a **Natural Language Interface for Infrastructure (NLI)** using a microservices architecture. The core goal is to bridge the gap between human intent ("increase memory") and strict machine configurations (JSON Schema validation).

### 🏛 Microservices Architecture
The system is composed of three decoupled services, ensuring separation of concerns:

1.  **Schema Service (Port 5001):**
    *   **Role:** Single Source of Truth for configuration rules.
    *   **Function:** Serves JSON Schemas that define strict validation rules for each application (e.g., `tournament`, `matchmaking`).
    *   **Tech:** Flask, static file serving.

2.  **Values Service (Port 5002):**
    *   **Role:** Configuration State Manager.
    *   **Function:** Stores and retrieves the *current* state of the application configurations.
    *   **Tech:** Flask, JSON file I/O.

3.  **Bot Service (Port 5003) - The "Brain":**
    *   **Role:** Orchestrator & AI Integration.
    *   **Registry:** Coordinates communication between Schema and Values services.
    *   **AI Logic:** Interfaces with **Ollama (Llama 3)** to interpret natural language.
    *   **Safety Layer:** Implements code-level guards before applying any changes.

---

## 2. 🛡 Defense-in-Depth: Safety & Robustness Strategies

One of the primary challenges in LLM-driven infrastructure is **Hallucination**. An LLM might generate syntactically correct JSON that is semantically disastrous (e.g., inventing a `memory` field in the wrong location).

We implemented a **4-Layer Safety Mechanism** to guarantee reliability:

### Layer 1: Advanced Prompt Engineering (The "Contract")
We moved away from generic prompts to a strict "Patching Contract".
*   **Rule:** The AI must *never* rewrite the full file. It must only return a list of patches.
*   **Context:** We serve specific "One-Shot Examples" for complex services like `tournament` to teach the model the correct nesting structure.
*   **Negative Constraints:** Explicit instruction to *never* use generic keys like `data`, `config`, or `values`.

### Layer 2: Code-Level Safety Filters (The "Firewall")
Even with good prompts, LLMs can be unpredictable. We implemented Python-level heuristic filters in `bot-server/main.py` that act as a firewall against bad paths:
*   **Service Isolation:** Rejects any attempt to add `cpu`, `memory`, or `replicas` under the `services` root key (common hallucination).
*   **Container Enforcement:** strictly blocks any `envs` or `resources` changes that do not include `containers` in their path.
*   **Root Key Whitelisting:** Any update path starting with an unknown root key (e.g., `data. replicas`) is instantly discarded.

### Layer 3: JSON Schema Validation (The "Gatekeeper")
Before any change is committed to the "Values Service":
1.  The patch is applied to a temporary in-memory copy of the configuration.
2.  The resulting JSON is validated against the **Strict JSON Schema**.
3.  If validation fails (e.g., wrong data type, unknown field), the transaction is rolled back immediately.

### Layer 4: Automated Recovery & Health Checks
The `run.sh` automation script ensures the environment is always consistent:
*   **Ollama Detection:** Automatically checks if the inference engine is running.
*   **Model Pulling:** Auto-downloads `llama3` if missing.
*   **Self-Healing:** Docker Compose restarts services automatically if they crash.

### Layer 5: Strict Mode & Heuristics (New!)
We observed that standard LMs can be "too helpful," guessing applications or values even when requests are nonsensical. We introduced **Strict Mode** to prevent this:
*   **Anti-Hallucination for Apps:** If a user asks for "unicorn service," the AI is strictly instructed to return `none` instead of guessing the closest match. The system then returns a **404 Not Found** or **400 Bad Request**.
*   **Type Enforcement:** If a user inputs an invalid type (e.g., "set memory to banana"), the AI now returns an empty changeset `[]`. The system detects this "no-op" and raises a **400 Error** rather than silently ignoring the request.
*   **Explicit Whitelisting:** The AI prompt now contains a hardcoded "Legal List" of applications. Any request falling outside this list is immediately rejected.

---

## 3. 🔍 Solved Technical Challenges

### Challenge A: The "Root Injection" Hallucination
*   **Issue:** The AI would often wrap the entire response in a `{"matchmaking": ...}` object or invent a `data` key.
*   **Solution:** Implemented logic to extract the *inner* list from JSON responses and a root key allowlist (`workloads`, `services`, `ingresses`).

### Challenge B: Resource Misplacement
*   **Issue:** Requests like "set memory to 1GB" caused the AI to add `memory` to the `deployment` root or `services` definition.
*   **Solution:** 
    1.  **Prompt:** Added explicit rule: *"Resources MUST be under `containers.<app_name>.resources`"*.
    2.  **Code:** Added a filter: `if 'resources' in path and 'containers' not in path: continue`.

### Challenge C: The "Envs" Ambiguity
*   **Issue:** Setting environment variables caused schema errors because the AI forgot the `containers` nesting level.
*   **Solution:** Similar to resources, we enforced a strict path requirement for `envs` via both Prompt and Code.

---

## 4. 🚀 Automation & Workflow

The project uses a unified entry point `run.sh` to abstract away complexity:

1.  **Environment Audit:** Checks `docker`, `docker-compose`, and `ollama`.
2.  **Inference Setup:** Ensures `llama3` is loaded into memory (Warm-up).
3.  **Orchestration:** Builds and launches the container mesh.
4.  **Verification:** Runs health checks on ports 5001, 5002, and 5003.

**User command:**
```bash
./run.sh
```
This single command delivers a production-ready environment in seconds.
