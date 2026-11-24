CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- 1. SEMANTIC & EPISODIC MEMORIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    type TEXT NOT NULL CHECK (type IN ('semantic', 'episodic')),
    summary TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags TEXT[] NOT NULL DEFAULT '{}',
    embedding VECTOR(768) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    utility_score INT NOT NULL DEFAULT 0,
    access_count INT NOT NULL DEFAULT 0,
    source_id TEXT,
    superseded_by UUID REFERENCES memories(memory_id) ON DELETE SET NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ DEFAULT NULL, -- NULL means currently active/valid
    reaffirmed_at TIMESTAMPTZ DEFAULT NULL, -- When fact was confirmed or refreshed (Half-Life Decay)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE memories ADD COLUMN IF NOT EXISTS reaffirmed_at TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_memories_ns_type_valid_until
    ON memories (namespace, type, valid_until);

CREATE INDEX IF NOT EXISTS idx_memories_ns_type_created_at
    ON memories (namespace, type, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_memories_superseded_by
    ON memories (superseded_by) WHERE superseded_by IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_memories_valid_until
    ON memories (valid_until) WHERE valid_until IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw
    ON memories USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_memories_summary_fts
    ON memories USING gin (to_tsvector('english', summary));

-- ============================================================================
-- 2. PROCEDURAL MEMORY TABLE (SELF-EVOLVING WORKFLOWS & RUNBOOKS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS procedural_memories (
    procedure_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    trigger_condition TEXT NOT NULL,
    trigger_embedding VECTOR(768) NOT NULL,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    prerequisites JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    changelog JSONB NOT NULL DEFAULT '[]'::jsonb,
    success_count INT NOT NULL DEFAULT 0,
    fail_count INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace, name)
);

CREATE INDEX IF NOT EXISTS idx_procedural_trigger_hnsw
    ON procedural_memories USING hnsw (trigger_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_procedural_ns_active
    ON procedural_memories (namespace) WHERE is_active = TRUE;

-- ============================================================================
-- 3. ENTITY GRAPH MEMORY TABLES (BI-TEMPORAL NODES & EDGES)
-- ============================================================================
CREATE TABLE IF NOT EXISTS entity_nodes (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(768) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace, name, entity_type)
);

ALTER TABLE entity_nodes ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_entity_nodes_embedding_hnsw
    ON entity_nodes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_entity_nodes_ns_active
    ON entity_nodes (namespace) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS entity_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    source_entity_id UUID NOT NULL REFERENCES entity_nodes(entity_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    target_entity_id UUID NOT NULL REFERENCES entity_nodes(entity_id) ON DELETE CASCADE,
    fact_summary TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ DEFAULT NULL
);

-- 1-Hop Graph Traversal & Conflict Invalidation: Source to Target
CREATE INDEX IF NOT EXISTS idx_entity_edges_src_rel
    ON entity_edges (namespace, source_entity_id, relation_type, valid_until);

-- 1-Hop Graph Traversal: Incoming Edges into Target
CREATE INDEX IF NOT EXISTS idx_entity_edges_tgt
    ON entity_edges (namespace, target_entity_id, valid_until);

-- ============================================================================
-- 4. RECIPROCAL RANK FUSION (RRF) + UTILITY SCORE SQL FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION hybrid_memory_search(
    query_text TEXT,
    query_embedding VECTOR(768),
    target_namespace TEXT,
    target_types TEXT[],
    match_threshold FLOAT DEFAULT 0.45,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    memory_id UUID,
    type TEXT,
    summary TEXT,
    payload JSONB,
    tags TEXT[],
    utility_score INT,
    confidence FLOAT,
    created_at TIMESTAMPTZ,
    rrf_score FLOAT
) AS $$
DECLARE
    clean_query TEXT := trim(query_text);
    has_text_query BOOLEAN := false;
    parsed_query TSQUERY;
BEGIN
    IF clean_query <> '' THEN
        BEGIN
            parsed_query := websearch_to_tsquery('english', clean_query);
            IF parsed_query IS NOT NULL AND parsed_query::TEXT <> '' THEN
                has_text_query := true;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            has_text_query := false;
        END;
    END IF;

    RETURN QUERY
    WITH vector_matches AS (
        SELECT
            m.memory_id,
            m.type,
            m.summary,
            m.payload,
            m.tags,
            m.utility_score,
            m.confidence,
            m.created_at,
            m.reaffirmed_at,
            ROW_NUMBER() OVER (ORDER BY (m.embedding <=> query_embedding) ASC) AS rank_vec
        FROM memories m
        WHERE m.namespace = target_namespace
          AND m.type = ANY(target_types)
          AND (m.valid_until IS NULL OR m.valid_until > NOW())
          AND (1.0 - (m.embedding <=> query_embedding)) >= match_threshold
        LIMIT 50
    ),
    text_matches AS (
        SELECT
            m.memory_id,
            m.type,
            m.summary,
            m.payload,
            m.tags,
            m.utility_score,
            m.confidence,
            m.created_at,
            m.reaffirmed_at,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector('english', m.summary),
                    parsed_query
                ) DESC
            ) AS rank_txt
        FROM memories m
        WHERE m.namespace = target_namespace
          AND m.type = ANY(target_types)
          AND (m.valid_until IS NULL OR m.valid_until > NOW())
          AND has_text_query
          AND to_tsvector('english', m.summary) @@ parsed_query
        LIMIT 50
    ),
    fused AS (
        SELECT
            COALESCE(v.memory_id, t.memory_id) AS memory_id,
            COALESCE(v.type, t.type) AS type,
            COALESCE(v.summary, t.summary) AS summary,
            COALESCE(v.payload, t.payload) AS payload,
            COALESCE(v.tags, t.tags) AS tags,
            COALESCE(v.utility_score, t.utility_score) AS utility_score,
            COALESCE(v.confidence, t.confidence) AS confidence,
            COALESCE(v.created_at, t.created_at) AS created_at,
            (
                (
                    COALESCE(1.0 / (60.0 + v.rank_vec), 0.0) +
                    COALESCE(1.0 / (60.0 + t.rank_txt), 0.0)
                ) * (
                    0.65 + 0.35 * POWER(0.5, (EXTRACT(EPOCH FROM (NOW() - COALESCE(COALESCE(v.reaffirmed_at, t.reaffirmed_at), COALESCE(v.created_at, t.created_at)))) / 86400.0) / 30.0)
                ) +
                (LEAST(GREATEST(COALESCE(v.utility_score, t.utility_score), -5), 20) * 0.001)
            )::FLOAT AS score
        FROM vector_matches v
        FULL OUTER JOIN text_matches t ON v.memory_id = t.memory_id
    )
    SELECT
        f.memory_id,
        f.type,
        f.summary,
        f.payload,
        f.tags,
        f.utility_score,
        f.confidence,
        f.created_at,
        f.score AS rrf_score
    FROM fused f
    ORDER BY f.score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
