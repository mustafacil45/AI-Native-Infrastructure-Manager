# 🤖 AI-Native Infrastructure Manager

> **Manage your Kubernetes-style configurations using natural language.**  
> Powered by Local LLMs (Ollama + Llama 3) strict Schema Validation.

---

## 📖 Overview

This project demonstrates a **reliable, hallucination-resistant** system for managing complex application configurations via a chat interface. It bridges the gap between unstructured human intent and strict JSON Schema requirements.

**Key Features:**
*   **🗣️ Natural Language Interface:** "Set memory to 1GB" instead of editing YAML/JSON.
*   **🛡️ Zero Hallucinations:** Implements a 4-layer safety defense (see [INTERN.md](INTERN.md)).
*   **🔒 Local & Private:** Runs entirely offline using Ollama and Llama 3.
*   **✅ Schema Validated:** Every change is validated against rigorous JSON Schemas before application.

---

## 🚀 Quick Start

### Prerequisites
*   **Docker** & **Docker Compose**
*   **Ollama** (installed on host)

### One-Command Setup
We provide a unified automation script that handles everything (model pulling, building, health checks):

```bash
./run.sh
```

*This script will:*
1.  Start Docker services (Bot, Schema, Values).
2.  Check for Ollama and automatically pull `llama3` if missing.
3.  Wait for all services to be healthy.

---

## ⚡️ Usage Examples

Once up, send requests to `http://localhost:5003/message`.

### 1. Update Resources
> "Set tournament service memory to 1024mb"
```bash
curl -X POST http://localhost:5003/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set tournament service memory to 1024mb"}'
```

### 2. Set Environment Variables
> "Set GAME_NAME env to toyblast for matchmaking service"
```bash
curl -X POST http://localhost:5003/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set the GAME_NAME environment variable to toyblast for matchmaking service"}'
```

### 3. Scaling
> "Set matchmaking replicas to 5"
```bash
curl -X POST http://localhost:5003/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set matchmaking replicas to 5"}'
```

---

## 🏗 Architecture & Technical Details

The system consists of three microservices:
1.  **Bot Server:** The AI orchestrator and safety enforcement layer.
2.  **Schema Server:** Provides validation rules.
3.  **Values Server:** Manages configuration state.

👉 **For a deep dive into the design decisions, safety mechanisms (anti-hallucination filters), and implementation details, please read [INTERN.md](INTERN.md).**

---

## 📂 Project Structure

```
.
├── bot-server/        # AI Logic & Safety Filters
├── schema-server/     # Validation Rules
├── values-server/     # State Management
├── data/              # JSON Storage
├── run.sh             # Automation Script
├── INTERN.md          # Technical Documentation
└── README.md          # This file
```
