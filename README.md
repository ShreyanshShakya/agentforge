# AgentForge: Multi-Agent Software Engineering Assistant

A locally deployed multi-agent AI system that transforms high-level problem statements into structured technical specifications through collaborative reasoning between specialized AI agents.

The system leverages local Large Language Models (LLMs) through Ollama and employs role-based agent orchestration to perform requirement analysis, architecture design, risk assessment, and implementation planning.

---

## Project Overview

AgentForge is an experimental agentic AI framework designed to simulate a software engineering team.

Instead of relying on a single model response, multiple specialized agents collaborate to analyze a problem from different perspectives before generating a consolidated technical plan.

### Current Capabilities

* Requirement analysis
* System architecture design
* Technical risk assessment
* Project planning and task decomposition
* Local LLM execution using Ollama
* Modular agent framework

### Future Capabilities

* Consensus Agent
* Codex Integration
* Automated Code Generation
* Test Generation
* Debug Agent
* Memory System
* RAG Integration
* LangGraph Workflow Management

---

## Architecture


```text

User
  │
  ▼
Analyst Agent
  │
  ▼
Architect Agent
  │
  ▼
Critic Agent
  │
  ▼
Planner Agent
  │
  ▼
Technical Specification
```

---

## Agent Roles

### Analyst Agent

Responsibilities:

* Understand user requirements
* Identify objectives
* Extract constraints
* Define success criteria

Input:

* User problem statement

Output:

* Structured requirements document

---

### Architect Agent

Responsibilities:

* Design system architecture
* Select technologies
* Define major components
* Propose implementation strategy

Input:

* Requirements document

Output:

* Architecture proposal

---

### Critic Agent

Responsibilities:

* Identify risks
* Detect missing requirements
* Review scalability concerns
* Review security considerations

Input:

* Requirements and architecture

Output:

* Technical critique

---

### Planner Agent

Responsibilities:

* Break project into phases
* Define implementation tasks
* Establish dependencies
* Create execution roadmap

Input:

* Requirements
* Architecture
* Critique

Output:

* Project plan

---

## Project Structure

```text
agentforge/
│
├── agents/
│   ├── base_agent.py
│   ├── analyst.py
│   ├── architect.py
│   ├── critic.py
│   └── planner.py
│
├── examples/
│
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Technology Stack

### Core Technologies

* Python
* Ollama
* WSL2

### Models

* Qwen2.5 3B
* Qwen3 4B
* Qwen2.5-Coder 7B
* Nomic Embed Text

### Planned Integrations

* Codex
* LangGraph
* ChromaDB
* Docker

---

## Installation

### 1. Clone Repository

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd agentforge
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama Models

```bash
ollama pull qwen2.5:3b
ollama pull qwen3:4b
ollama pull qwen2.5-coder:7b
```

### 5. Run

```bash
python main.py
```

---

## Example Run

### Input

```text
Build a travel demand intelligence system
```

### Analyst Output

```text
1. Objectives:
   - To gather, analyze and visualize travel demand data to inform urban planning decisions.
   - To provide real-time traffic updates and optimize route suggestions for commuters.

2. Functional Requirements:
   - Collect data from various sources (traffic cameras, GPS devices, public transportation systems).
   - Analyze travel patterns to predict future demand in specific areas.
   - Generate reports on congestion levels across different regions.
   - Provide customized route suggestions based on user inputs and historical traffic data.
   - Real-time tracking of events that may affect traffic flow such as road works or accidents.

3. Non-Functional Requirements:
   - High availability: Ensure the system is operational 24/7 without downtime.
   - Scalability: The system should be able to handle increasing volumes of user and sensor data.
   - Security: All data handling must comply with GDPR regulations, ensuring data privacy and security.
   - Accuracy: Predictions and recommendations need to be as accurate as possible to support
```

### Architect Output

```text
1. System Architecture:
   - Distributed architecture using microservices for scalability and fault isolation.
   - Centralized database management system for data storage and integration across services.

2. Major Components:
   - Data Collector Service: Interfaces with various sensors, devices and APIs.
   - Data Processor Service: Analyzes incoming data and prepares it for visualization or recommendations.
   - Visualization Service: Provides real-time and historical visual analytics of travel demand patterns.
   - Routing Service: Generates optimal routes based on user input and traffic conditions.

3. Technology Stack:
   - Microservices using Node.js, Python or Java for development.
   - Database Management System (MongoDB/MySQL) for storing raw data and intermediate results.
   - Data Visualization Frameworks like D3.js/Vega-Lite for interactive analytics interfaces.
   - APIs for inter-service communication following RESTful principles.

4. Data Flow:
   - Sensors/Data Collectors send data to the Collector Service.
   - Processor Service processes incoming data,
```

### Critic Output

```text
1. Risks: Increased complexity in managing multiple microservices, potential integration issues between services, and risk of data inconsistency across systems due to concurrent updates.

2. Scalability Issues: As the number of sensors and users increases, there may be challenges scaling the database management system and microservices without compromising performance or availability.

3. Security Concerns: Ensuring secure data transmission and storage requires robust encryption protocols, regular security audits, and compliance with GDPR regulations. Additionally, protecting against cyber-attacks such as SQL injection attacks on databases and unauthorized access to APIs is crucial.

4. Missing Components: A comprehensive user authentication and authorization system might be necessary for securing interactions between services and handling API requests from external applications. Also, implementing machine learning models for more accurate travel demand predictions could enhance the system's predictive capabilities.

5. Recommendations:
- Implement a centralized security framework including authentication and encryption mechanisms to secure data.
- Introduce an automated monitoring system to detect and respond quickly to potential security breaches or anomalies
```

### Planner Output

```text
Phase 1:
Tasks

### Task 1: Data Collection Infrastructure Setup
**Description:** Establish the initial setup for collecting travel demand data from various sources including traffic cameras, GPS devices, and public transportation systems.
**Dependencies:** Existing IT infrastructure, APIs for data collection services, software development environment.
**Deliverables:** Operational Data Collector Service capable of interfacing with multiple external data sources.

### Task 2: Data Storage System Design
**Description:** Design the database system to store raw sensor data and intermediate processing results securely and efficiently.
**Dependencies:** Architecture blueprint provided in the Architecture section.
**Deliverables:** Prototype Database Management System (DBMS) setup capable of integrating various types of travel demand data.

### Task 3: User Authentication & Authorization
**Description:** Implement a secure user authentication and authorization system to ensure only authorized users can access services and APIs.
**Dependencies:** Basic IT infrastructure, existing security standards in place.
```

---

## Performance Notes

Development Environment:

* WSL2
* AMD Ryzen 5 5500U
* 16 GB RAM

Optimization Techniques:

* Local inference with Ollama
* Lightweight reasoning models
* Prompt optimization
* Resource-aware deployment

---

## Roadmap

### Phase 1 (Completed)

* [x] Base Agent Framework
* [x] Analyst Agent
* [x] Architect Agent
* [x] Critic Agent
* [x] Planner Agent
* [x] Local Ollama Integration

### Phase 2 (In Progress)

* [ ] Consensus Agent
* [ ] Structured JSON Outputs
* [ ] Improved Prompt Engineering

### Phase 3 (Planned)

* [ ] Codex Integration
* [ ] Automated Code Generation
* [ ] Testing Pipeline
* [ ] Self-Correction Loop

### Phase 4 (Planned)

* [ ] LangGraph Integration
* [ ] Long-Term Memory
* [ ] RAG Pipeline
* [ ] Multi-Project Support

---

## Key Learnings


* Multi-agent orchestration design
* Local LLM deployment
* Prompt engineering
* Agent specialization
* Resource optimization in constrained environments

---

## Author

Name: Shreyansh Shakya


LinkedIn: [[LINKEDIN PROFILE]](https://www.linkedin.com/in/shreyansh-shakya-3b019022a)
