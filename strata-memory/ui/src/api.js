const API_BASE = '/v1';

export async function fetchStats(namespace = 'default') {
  try {
    const res = await fetch(`${API_BASE}/ui/stats?namespace=${encodeURIComponent(namespace)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Using offline stats fallback:", err);
    return {
      namespaces: ['default', 'user_alice', 'coding_assistant'],
      semantic: { active: 142, superseded: 8, total: 150 },
      episodic: { active: 38, superseded: 0, total: 38 },
      procedural: { count: 12 },
      entity_nodes: { count: 89 },
      entity_edges: { active: 123, invalidated: 11, total: 134 }
    };
  }
}

export async function fetchMemories(namespace = 'default', pillar = null, status = 'all', limit = 50, offset = 0) {
  try {
    let url = `${API_BASE}/ui/memories?namespace=${encodeURIComponent(namespace)}&status=${status}&limit=${limit}&offset=${offset}`;
    if (pillar) url += `&pillar=${pillar}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Using offline memories fallback:", err);
    return {
      total: 3,
      items: [
        {
          memory_id: "mem-003c",
          namespace: namespace,
          type: "semantic",
          summary: "User architecture uses Neon Serverless Postgres with scale-to-zero suspend and HNSW 768-dim embeddings.",
          payload: { engine: "neon", extension: "pgvector" },
          tags: ["database", "postgres", "neon", "pgvector"],
          confidence: 1.0,
          utility_score: 8,
          access_count: 14,
          is_active: true,
          created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
          superseded_by: null
        },
        {
          memory_id: "mem-002b",
          namespace: namespace,
          type: "semantic",
          summary: "User migrated from SQLite to Neon Serverless Postgres with pgvector extension.",
          payload: {},
          tags: ["database", "postgres", "neon"],
          confidence: 0.98,
          utility_score: 5,
          access_count: 8,
          is_active: false,
          created_at: new Date(Date.now() - 86400000 * 6).toISOString(),
          superseded_by: "mem-003c"
        },
        {
          memory_id: "mem-001a",
          namespace: namespace,
          type: "semantic",
          summary: "User prefers Local SQLite for vector storage and rapid prototyping.",
          payload: {},
          tags: ["database", "sqlite"],
          confidence: 0.95,
          utility_score: 2,
          access_count: 4,
          is_active: false,
          created_at: new Date(Date.now() - 86400000 * 12).toISOString(),
          superseded_by: "mem-002b"
        }
      ]
    };
  }
}

export async function fetchGraph(namespace = 'default', includeInvalidated = true) {
  try {
    const res = await fetch(`${API_BASE}/ui/graph?namespace=${encodeURIComponent(namespace)}&include_invalidated=${includeInvalidated}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Using offline graph fallback:", err);
    return {
      nodes: [
        { id: "n1", name: "User (Alice)", entity_type: "person", summary: "Main software engineer and project lead.", is_active: true },
        { id: "n2", name: "Neon Postgres", entity_type: "technology", summary: "Serverless Postgres with pgvector & auto-suspend compute.", is_active: true },
        { id: "n3", name: "pgvector", entity_type: "technology", summary: "HNSW cosine indexing for 768-dimensional embeddings.", is_active: true },
        { id: "n4", name: "Strata Engine", entity_type: "architecture", summary: "4-Pillar Cognitive Memory Engine with bi-temporal entity graph.", is_active: true },
        { id: "n5", name: "Laya Router", entity_type: "technology", summary: "Dynamic pillar routing and fast-path classification.", is_active: true },
        { id: "n6", name: "SQLite", entity_type: "technology", summary: "Deprecated local storage previously used for embeddings.", is_active: false },
        { id: "n7", name: "FastAPI", entity_type: "technology", summary: "REST API server exposing memory ingest, recall, and feedback.", is_active: true }
      ],
      edges: [
        { id: "e1", source: "n1", target: "n2", relation: "PREFERS", fact: "User preferred database for vector memory", is_active: true },
        { id: "e2", source: "n2", target: "n3", relation: "USES_EXTENSION", fact: "Enabled for vector similarity search", is_active: true },
        { id: "e3", source: "n4", target: "n2", relation: "PERSISTS_TO", fact: "Stores all 4 memory pillars in Neon", is_active: true },
        { id: "e4", source: "n4", target: "n5", relation: "ROUTES_VIA", fact: "Uses Laya for dynamic pillar selection", is_active: true },
        { id: "e5", source: "n4", target: "n7", relation: "EXPOSED_BY", fact: "Served via REST endpoints", is_active: true },
        { id: "e6", source: "n1", target: "n6", relation: "PREVIOUSLY_USED", fact: "Superseded when migrating to Neon Serverless", is_active: false }
      ]
    };
  }
}

export async function fetchProcedures(namespace = 'default') {
  try {
    const res = await fetch(`${API_BASE}/ui/procedures?namespace=${encodeURIComponent(namespace)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Using offline procedures fallback:", err);
    return [
      {
        procedure_id: "proc-1",
        name: "deploy_to_neon_serverless",
        description: "Standard workflow to migrate and configure Neon Postgres for Strata memory.",
        trigger_condition: "When deploying or migrating database schema",
        steps: [
          "Run database migration script 001_init_schema.sql",
          "Verify pgvector extension is enabled",
          "Configure scale-to-zero compute auto-suspend"
        ],
        version: 1,
        success_count: 14,
        fail_count: 1,
        success_rate: 0.8824,
        changelog: [
          { version: 1, timestamp: new Date(Date.now() - 86400000 * 5).toISOString(), reason: "Initial creation" }
        ],
        updated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
        is_active: true
      }
    ];
  }
}

export async function executeIngest(payload) {
  const res = await fetch(`${API_BASE}/memory/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function executeRecall(payload) {
  const res = await fetch(`${API_BASE}/memory/recall`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function submitFeedback(payload) {
  const res = await fetch(`${API_BASE}/memory/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
