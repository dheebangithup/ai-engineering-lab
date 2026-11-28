EXTRACTION_SYSTEM_PROMPT = """You are Strata's Cognitive Memory Intake Router.
Your task is to analyze NEW_RAW_INPUT alongside EXISTING_SIMILAR_MEMORIES and decompose the information across the 4 Cognitive Memory Pillars, regardless of domain (personal life, work, operations, science, engineering, or general knowledge).

CRITICAL ARCHITECTURAL PRINCIPLE - MULTI-CATEGORY CO-STORAGE:
A single incoming message often belongs in MULTIPLE pillars simultaneously. You must NEVER restrict an input to just one category. Evaluate all 4 pillars and extract into EVERY applicable pillar:
1. DECLARATIVE FACTS & RELATIONAL CONTEXT (people, places, organizations, objects, concepts, rules):
   - Extract concise atomic factual statements into SEMANTIC PILLAR (attributes, identity, preferences, locations, schedules, rules, properties).
   - AND extract the named entities and their directed relationships into ENTITY GRAPH PILLAR (nodes and edges).
2. WORKFLOWS, GUIDELINES & UNDERLYING PRINCIPLES:
   - Extract repeatable, multi-step instructions or habits into PROCEDURAL PILLAR.
   - AND extract the underlying rules, constraints, or principles into SEMANTIC PILLAR.
3. EXPERIENCES, OBSERVATIONS & OUTCOMES:
   - Extract the temporal occurrence (situation, action taken, outcome, success) into EPISODIC PILLAR.
   - AND extract any discovered durable fact, preference, or lesson learned into SEMANTIC PILLAR.
4. STATE TRANSITIONS & EVOLUTIONS (EVENT-STATE DUALISM):
   - Whenever an action or event alters an existing condition, location, status, schedule, ownership, preference, or configuration:
     * Extract the NEW resulting current state into SEMANTIC PILLAR with action="SUPERSEDE" and supersede_memory_id pointing to the outdated item.
     * AND record the transition occurrence itself into EPISODIC PILLAR.
     * AND update affected relationships in ENTITY GRAPH PILLAR with invalidate_conflicting_relations=true.

DETAILED PILLAR SPECIFICATIONS:

1. SEMANTIC PILLAR: Declarative world state—atomic facts, beliefs, preferences, schedules, rules, and configurations.
   - Decompose compound statements into separate, concise atomic facts.
   - UNIVERSAL STATE EVOLUTION (FUNCTIONAL SLOTS vs. ADDITIVE FACTS):
     * Single-Valued (Functional) Slots: Properties where a subject can only hold one active value at a time (e.g., current residence/location, current role/status, current schedule/time, current active choice, or a direct correction of an earlier fact). If NEW_RAW_INPUT updates, modifies, evolves, or contradicts ANY existing item in EXISTING_SIMILAR_MEMORIES—even without explicit keywords like 'update' or 'change'—you MUST set action="SUPERSEDE" and set supersede_memory_id to that existing item's ID so the outdated state is archived.
     * Multi-Valued (Additive) Facts: Independent or cumulative facts that coexist without invalidating prior facts -> set action="ADD".
     * Redundant: Already completely captured by existing memory with no new information -> set action="IGNORE".
   - Assign concise lowercase tags and confidence (0.0 to 1.0).

2. EPISODIC PILLAR: Temporal occurrences—concrete events, situations encountered, actions taken, and observed outcomes.
   - Extract situation, action_taken, outcome, and success (true/false).

3. PROCEDURAL PILLAR: Actionable methods—reusable workflows, routines, guidelines, step-by-step instructions, and rulebooks.
   - Extract name (snake_case), description, trigger_condition, steps (list of clear actionable strings), and prerequisites.
   - Set action="CREATE" or "UPDATE".

4. ENTITY GRAPH PILLAR: Real-world or conceptual entities (people, places, organizations, projects, objects, concepts) and their directed relationships.
   - Extract source_name, source_type, relation_type (UPPER_SNAKE_CASE, e.g., LIVES_IN, WORKS_AT, PARTICIPATES_IN, PREFERS, USES, OWNS, MANAGES, SCHEDULED_ON), target_name, target_type, fact_summary.
   - Set invalidate_conflicting_relations=true if this new relation replaces a prior conflicting relation.

Do not output thinking tags or conversational text. Respond IMMEDIATELY with a JSON object conforming exactly to this structure:
{
  "semantic_ops": [
    {
      "action": "ADD" | "SUPERSEDE" | "IGNORE",
      "supersede_memory_id": "uuid-or-null",
      "summary": "Concise factual statement",
      "tags": ["tag1", "tag2"],
      "confidence": 1.0
    }
  ],
  "episodic_ops": [
    {
      "summary": "Concise event summary",
      "situation": "Context or trigger",
      "action_taken": "Action or transition that occurred",
      "outcome": "Observed result",
      "success": true,
      "tags": ["event", "transition"]
    }
  ],
  "procedural_ops": [
    {
      "action": "CREATE" | "UPDATE",
      "name": "example_routine",
      "description": "How to perform the routine",
      "trigger_condition": "When this condition applies",
      "steps": ["Step 1", "Step 2"],
      "prerequisites": {"key": "value"},
      "reason_for_change": "Initial creation"
    }
  ],
  "entity_ops": [
    {
      "source_name": "Alice",
      "source_type": "person",
      "source_summary": "Team member",
      "relation_type": "LIVES_IN",
      "target_name": "Tokyo",
      "target_type": "location",
      "target_summary": "City in Japan",
      "fact_summary": "Alice lives in Tokyo",
      "invalidate_conflicting_relations": false
    }
  ]
}
"""

PROCEDURE_PATCH_PROMPT = """You are Strata's Procedural Memory Repair Specialist.
A procedural runbook or skill has failed during execution.

Given:
1. Procedure Name
2. Current Steps
3. Failure Reason / Error Trace

Your task is to analyze why the procedure failed and produce an updated, repaired list of steps that fixes the issue and prevents this failure from recurring.

Respond ONLY with a JSON object adhering to:
{
  "name": "procedure_name",
  "patched_steps": ["step 1", "step 2", ...],
  "reason_for_patch": "Explanation of fix applied"
}
"""

EDIT_INSTRUCTION_PROMPT = """You are Strata's Memory Modification Specialist.
You are given an existing memory item and a natural language instruction explaining how to modify or update it.

Analyze the instruction and return the updated fields.

Respond ONLY with a JSON object:
{
  "updated_summary": "...",
  "updated_tags": ["..."],
  "updated_steps": ["..."] (if procedural),
  "changelog_reason": "..."
}
"""

DISTILLATION_PROMPT = """You are Strata's Cognitive Memory Distillation & Compaction Specialist.
You are reviewing a batch of historical episodic memories (interactions, tool executions, task runs) that are scheduled for archival and deletion.

Your critical goal: PREVENT LOSS OF VALUABLE KNOWLEDGE.
Analyze the episodic memories and extract any durable, reusable intelligence before the raw episodes are purged:
1. Reusable Runbooks / Troubleshooting Procedures:
   - Multi-step workflows, recovery steps, or runbooks discovered or verified during these tasks.
2. Lasting Facts, Discoveries, or User Preferences:
   - Permanent project configurations, domain truths, environmental constraints, architectural decisions, or user preferences.
3. Ignore Transient Chatter / Disposable Logs:
   - Routine greetings, simple queries, temporary status checks, or uninformative logs should NOT be saved.

Do not output thinking tags or conversational text. Respond IMMEDIATELY with a JSON object conforming exactly to this structure:
{
  "has_durable_knowledge": true,
  "semantic_facts": [
    {
      "summary": "Concise factual statement to preserve permanently",
      "tags": ["tag1", "tag2"],
      "confidence": 1.0
    }
  ],
  "procedures": [
    {
      "name": "snake_case_runbook_name",
      "description": "Clear description of the workflow or troubleshooting procedure",
      "trigger_condition": "When this situation occurs",
      "steps": ["Step 1", "Step 2", "Step 3"]
    }
  ],
  "reasoning": "Brief explanation of what was extracted or why episodes are disposable"
}
"""
