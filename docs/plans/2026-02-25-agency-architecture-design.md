# Design: Marketing Agency Architecture

**Date:** 2026-02-25
**Topic:** Restructuring the project into a virtualized, autonomous marketing agency.

## 1. Overview
The current iteration of the project functions as a flat, single-box application. This design outlines the transition to a SaaS-ready, multi-tenant "Virtualized Marketing Agency." The goal is to allow users to input high-level demands (e.g., "Mother's Day Campaign"), which are autonomously orchestrated, executed, reviewed, and learned from by a network of specialized agents using tools (MCPs).

## 2. Core Entities & Database Structure (Relational + Vector)
To solve the "untidy single box" problem, the system will adopt a strict hierarchical data structure backed by a robust database (e.g., PostgreSQL/Supabase).

*   **Workspace/Agency:** The root tenant. Allows for multi-tenant SaaS scaling.
*   **Brand:** Associated with an agency. Contains core identity rules, voice profiles, and immutable constraints (`brandcore_id`).
*   **Product/Campaign:** Belong to a brand. Contains target audience profiles, objectives, and unique value propositions.
*   **Demand (Task):** The specific request (e.g., "Instagram Post"). It holds a status (`queued`, `running`, `needs_review`, `approved`), a `workflow_id`, and pointers to format best practices.

**Context Inheritance:** When a Demand is processed, the system programmatically builds the RAG context/prompt by inheriting the Product's audience and the Brand's core rules automatically.

## 3. Autonomous Orchestration (Supervisor-Worker Pattern)
Work is delegated through an asynchronous, queue-based architecture to ensure resilience and prevent agent collision.

1.  **Manager Agent (Orchestrator):**
    *   Receives the high-level Demand.
    *   Reads the inherited context (Brand + Product).
    *   Splits the Demand into an array of sub-tasks (e.g., Research -> Copy -> Design).
    *   Pushes sub-tasks to the `sub_tasks` database table with a `pending` status.
2.  **Worker Agents (Specialists):**
    *   Listen to the task queue.
    *   A specialist (e.g., Copywriter) pulls a task matching its skill set.
    *   Loads specific execution MCPs (e.g., SEO Auditor).
    *   Executes the task and marks the output for review.
3.  **Reviewer Agent (Quality Gate):**
    *   Inspects the Worker's output against the Brand and Product constraints.
    *   If constraints are violated (e.g., wrong tone of voice), the task is rejected back to the queue with specific feedback for the Worker to fix.

## 4. Collective Knowledge & Continuous Learning
The agency constantly improves through implicit and explicit feedback loops, leveraging a hybrid RAG approach.

*   **Implicit Feedback (Vector RAG):**
    *   When a Demand reaches the `approved` status, its text assets are indexed into a Vector Database.
    *   Future Workers querying for similar tasks within the same Brand retrieve these approved assets. By injecting these into the prompt, the agent naturally adheres to historically successful styles.
*   **Explicit Feedback (Rule Updating via MCP):**
    *   If a human user rejects a generated asset with specific feedback (e.g., "This brand never uses technical jargon, speak colloquially"), the system doesn't just retry the single task.
    *   The Reviewer Agent analyzes the human feedback and utilizes an `UpdateBrandRules` tool (MCP).
    *   This tool writes a new, explicit rule (a "Golden Rule") to the Brand's database configuration.
    *   All future prompts for this Brand will inherently include this new rule, ensuring the mistake is never repeated.

## 5. Next Steps
*   Adopt the `writing-plans` workflow to break this design down into bite-sized implementation tasks.
*   Initialize the core database schema (Brands, Products, Demands).
*   Implement the Orchestrator and Queue mechanism.
*   Implement the `UpdateBrandRules` MCP for explicit learning.
