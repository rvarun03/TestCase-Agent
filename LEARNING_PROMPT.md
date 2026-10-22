# Prompt for ChatGPT: Explain and Extend This Project

Copy the prompt below into ChatGPT after opening this folder in your editor.

```text
I am learning to build a Python FastAPI project named BRD-AGENT. It currently
uses LangChain and Groq to turn pasted BRD text into structured test cases.

My current folder structure is:

BRD-AGENT/
  app/
    __init__.py
    main.py
    config.py
    models.py
    agent.py
  .env
  .env.example
  .gitignore
  requirements.txt

Please act as a patient senior Python developer and tutor. First explain, in
simple words, what every folder and file does and why it exists. Then explain
the complete request flow from a BRD entered by a user to the FastAPI endpoint,
LangChain, Groq, Pydantic validation, and the JSON response.

Next, give me a small, beginner-friendly plan to change this one-agent starter
into a BRD-to-test-case workflow with four stages:

1. Requirement Analysis: extract features, users, rules, fields, acceptance
   criteria, and unclear requirements.
2. Scenario Design: create positive, negative, boundary, edge, security, and
   integration scenarios only when supported by the requirements.
3. Test-Case Generation: create detailed test cases with preconditions, test
   data, ordered steps, expected results, priority, and traceability.
4. QA Review: find missing coverage, duplicates, vague expected results, and
   unsupported assumptions.

Do not give all code at once. Teach me in milestones. For each milestone,
explain which files I should add or change, why that change is needed, and give
only the code needed for that milestone. Start with Milestone 1: define the
folder structure and Pydantic models for the four-stage workflow.

Keep the project simple. Do not add a database, RAG, LangGraph, Docker, queues,
authentication, or file upload until I ask for them. Keep the Groq API key in
.env and never place it in Python code.
```
