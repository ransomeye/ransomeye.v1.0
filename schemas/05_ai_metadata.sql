-- RansomEye v1.0 AI Metadata Tables
-- AUTHORITATIVE: Read-only AI/ML metadata tables
-- PostgreSQL 14+ compatible
-- AI NEVER writes facts. AI NEVER mutates incidents. Metadata only, versioned.

-- AI model type enumeration
CREATE TYPE ai_model_type AS ENUM (
    'ANOMALY_DETECTION',
    'BEHAVIORAL_ANALYSIS',
    'THREAT_CLASSIFICATION',
    'CLUSTERING',
    'NOVELTY_DETECTION',
    'EXPLAINABILITY'
);

-- Feature vector status enumeration
CREATE TYPE feature_vector_status AS ENUM (
    'PENDING',
    'PROCESSED',
    'ERROR'
);

-- Cluster status enumeration
CREATE TYPE cluster_status AS ENUM (
    'ACTIVE',
    'ARCHIVED',
    'MERGED'
);

-- ============================================================================
-- AI MODEL VERSIONS
-- ============================================================================
-- Registry of AI model versions
-- Immutable log of model deployments

CREATE TABLE ai_model_versions (
    model_version_id UUID NOT NULL PRIMARY KEY,
    -- UUID v4 for model version identifier (immutable, never reused)
    
    model_type ai_model_type NOT NULL,
    -- Type of AI model (ANOMALY_DETECTION, BEHAVIORAL_ANALYSIS, etc.)
    
    model_version_string VARCHAR(255) NOT NULL,
    -- Model version string (e.g., "1.0.0", "v2.3.1")
    -- VARCHAR(255) sufficient for version strings
    
    model_hash_sha256 CHAR(64),
    -- PHASE 3: SHA256 hash of model artifact (weights, configuration, etc.)
    -- NULL if hash not computed
    -- CHAR(64) for exactly 64 hex characters
    
    training_data_hash_sha256 CHAR(64),
    -- PHASE 3: SHA256 hash of training data (for replay support)
    -- NULL if hash not computed
    -- CHAR(64) for exactly 64 hex characters
    -- Same training data → same model (deterministic)
    
    model_storage_path TEXT,
    -- PHASE 3: External storage path where model is persisted
    -- NULL if model is not stored externally
    -- TEXT for unlimited length (paths can be long)
    -- NOTE: This is a reference, not the actual model
    
    deployed_at TIMESTAMPTZ NOT NULL,
    -- PHASE 3: Deterministic timestamp - must be provided explicitly
    -- When model was deployed
    
    deprecated_at TIMESTAMPTZ,
    -- When model was deprecated (NULL if still active)
    -- Deprecated models are still readable but not used for new inferences
    
    description TEXT,
    -- Human-readable model description
    -- NULL if not provided
    -- TEXT for unlimited length
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT ai_model_versions_version_string_not_empty CHECK (LENGTH(TRIM(model_version_string)) > 0),
    CONSTRAINT ai_model_versions_hash_format CHECK (model_hash_sha256 IS NULL OR model_hash_sha256 ~ '^[a-fA-F0-9]{64}$'),
    CONSTRAINT ai_model_versions_deployed_before_deprecated CHECK (deprecated_at IS NULL OR deployed_at <= deprecated_at)
);

COMMENT ON TABLE ai_model_versions IS 'Registry of AI model versions. Immutable log of model deployments. AI models are versioned for reproducibility and auditability.';
COMMENT ON COLUMN ai_model_versions.model_version_id IS 'UUID v4 for model version identifier. Immutable, never reused.';
COMMENT ON COLUMN ai_model_versions.model_type IS 'Type of AI model (ANOMALY_DETECTION, BEHAVIORAL_ANALYSIS, THREAT_CLASSIFICATION, CLUSTERING, NOVELTY_DETECTION, EXPLAINABILITY).';
COMMENT ON COLUMN ai_model_versions.model_hash_sha256 IS 'SHA256 hash of model artifact (weights, configuration, etc.). Used for model integrity verification. NULL if hash not computed.';
COMMENT ON COLUMN ai_model_versions.deprecated_at IS 'When model was deprecated (NULL if still active). Deprecated models are still readable but not used for new inferences.';

-- ============================================================================
-- FEATURE VECTORS (REFERENCES ONLY)
-- ============================================================================
-- Feature vectors computed from events (references only, not blobs)
-- AI metadata for machine learning features

CREATE TABLE feature_vectors (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events
    -- Feature vector is computed from a specific event
    
    model_version_id UUID NOT NULL REFERENCES ai_model_versions(model_version_id) ON DELETE RESTRICT,
    -- Foreign key to ai_model_versions
    -- Feature vector is computed using a specific model version
    
    feature_vector_hash_sha256 CHAR(64) NOT NULL,
    -- SHA256 hash of feature vector (for reference)
    -- Feature vector itself is stored externally (not in database)
    -- CHAR(64) for exactly 64 hex characters
    
    feature_vector_size INTEGER NOT NULL,
    -- Size of feature vector (number of features)
    -- INTEGER sufficient for feature vector sizes (typically < 10000)
    
    feature_vector_storage_path TEXT,
    -- External storage path where feature vector is stored
    -- NULL if feature vector is not stored externally
    -- TEXT for unlimited length (paths can be long)
    -- NOTE: This is a reference, not the actual feature vector
    
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When feature vector was computed
    
    status feature_vector_status NOT NULL DEFAULT 'PENDING',
    -- Feature vector processing status (PENDING, PROCESSED, ERROR)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT feature_vectors_hash_format CHECK (feature_vector_hash_sha256 ~ '^[a-fA-F0-9]{64}$'),
    CONSTRAINT feature_vectors_size_positive CHECK (feature_vector_size > 0),
    CONSTRAINT feature_vectors_unique_event_model UNIQUE (event_id, model_version_id)
    -- One feature vector per event per model version
);

COMMENT ON TABLE feature_vectors IS 'Feature vectors computed from events (references only, not blobs). AI metadata for machine learning features. Feature vectors are stored externally, not in database.';
COMMENT ON COLUMN feature_vectors.event_id IS 'Foreign key to raw_events. Feature vector is computed from a specific event.';
COMMENT ON COLUMN feature_vectors.model_version_id IS 'Foreign key to ai_model_versions. Feature vector is computed using a specific model version.';
COMMENT ON COLUMN feature_vectors.feature_vector_hash_sha256 IS 'SHA256 hash of feature vector (for reference). Feature vector itself is stored externally (not in database). Used for feature vector integrity verification.';
COMMENT ON COLUMN feature_vectors.feature_vector_storage_path IS 'External storage path where feature vector is stored. NULL if feature vector is not stored externally. This is a reference, not the actual feature vector.';
COMMENT ON COLUMN feature_vectors.status IS 'Feature vector processing status (PENDING, PROCESSED, ERROR). Used for tracking feature vector computation pipeline.';

-- ============================================================================
-- CLUSTERS
-- ============================================================================
-- Clusters identified by AI/ML algorithms
-- Clusters group similar events/behaviors together

CREATE TABLE clusters (
    cluster_id UUID NOT NULL PRIMARY KEY,
    -- UUID v4 for cluster identifier (immutable, never reused)
    
    model_version_id UUID NOT NULL REFERENCES ai_model_versions(model_version_id) ON DELETE RESTRICT,
    -- Foreign key to ai_model_versions
    -- Cluster was identified using a specific model version
    
    cluster_label VARCHAR(255) NOT NULL,
    -- Cluster label/identifier (e.g., "CLUSTER_001", "SUSPICIOUS_BEHAVIOR_1")
    -- VARCHAR(255) sufficient for cluster labels
    
    cluster_type VARCHAR(64),
    -- Cluster type/classification (e.g., "RANSOMWARE_BEHAVIOR", "LATERAL_MOVEMENT")
    -- NULL if not classified
    -- VARCHAR(64) sufficient for cluster types
    
    cluster_size INTEGER NOT NULL,
    -- Number of events/items in this cluster
    -- INTEGER sufficient for cluster sizes (typically < 1000000)
    
    cluster_centroid_hash_sha256 CHAR(64),
    -- SHA256 hash of cluster centroid (for reference)
    -- Cluster centroid is stored externally (not in database)
    -- NULL if centroid not computed
    -- CHAR(64) for exactly 64 hex characters
    
    cluster_created_at TIMESTAMPTZ NOT NULL,
    -- When cluster was first identified (timestamp of first event in cluster)
    
    cluster_updated_at TIMESTAMPTZ NOT NULL,
    -- When cluster was last updated (timestamp of last event added to cluster)
    
    status cluster_status NOT NULL DEFAULT 'ACTIVE',
    -- Cluster status (ACTIVE, ARCHIVED, MERGED)
    
    archived_at TIMESTAMPTZ,
    -- When cluster was archived (NULL if still ACTIVE)
    
    merged_into_cluster_id UUID REFERENCES clusters(cluster_id) ON DELETE SET NULL,
    -- Cluster ID that this cluster was merged into (NULL if not merged)
    -- Used for cluster merge tracking
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    -- When cluster was created in database
    
    CONSTRAINT clusters_cluster_label_not_empty CHECK (LENGTH(TRIM(cluster_label)) > 0),
    CONSTRAINT clusters_size_positive CHECK (cluster_size > 0),
    CONSTRAINT clusters_centroid_hash_format CHECK (cluster_centroid_hash_sha256 IS NULL OR cluster_centroid_hash_sha256 ~ '^[a-fA-F0-9]{64}$'),
    CONSTRAINT clusters_created_before_updated CHECK (cluster_created_at <= cluster_updated_at),
    CONSTRAINT clusters_archived_check CHECK (
        (status = 'ACTIVE' AND archived_at IS NULL AND merged_into_cluster_id IS NULL) OR
        (status = 'ARCHIVED' AND archived_at IS NOT NULL AND merged_into_cluster_id IS NULL) OR
        (status = 'MERGED' AND merged_into_cluster_id IS NOT NULL)
    )
    -- Status consistency checks:
    -- ACTIVE: archived_at = NULL, merged_into_cluster_id = NULL
    -- ARCHIVED: archived_at != NULL, merged_into_cluster_id = NULL
    -- MERGED: merged_into_cluster_id != NULL
);

COMMENT ON TABLE clusters IS 'Clusters identified by AI/ML algorithms. Clusters group similar events/behaviors together. Metadata only, versioned.';
COMMENT ON COLUMN clusters.cluster_id IS 'UUID v4 for cluster identifier. Immutable, never reused.';
COMMENT ON COLUMN clusters.model_version_id IS 'Foreign key to ai_model_versions. Cluster was identified using a specific model version.';
COMMENT ON COLUMN clusters.cluster_label IS 'Cluster label/identifier (e.g., "CLUSTER_001", "SUSPICIOUS_BEHAVIOR_1"). Always present.';
COMMENT ON COLUMN clusters.cluster_size IS 'Number of events/items in this cluster. Always present. Updated when events are added to cluster.';
COMMENT ON COLUMN clusters.cluster_centroid_hash_sha256 IS 'SHA256 hash of cluster centroid (for reference). Cluster centroid is stored externally (not in database). NULL if centroid not computed.';
COMMENT ON COLUMN clusters.merged_into_cluster_id IS 'Cluster ID that this cluster was merged into (NULL if not merged). Used for cluster merge tracking.';

-- ============================================================================
-- CLUSTER MEMBERSHIPS
-- ============================================================================
-- Many-to-many relationship: events belong to clusters
-- One event can belong to multiple clusters (one per model version)

CREATE TABLE cluster_memberships (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    cluster_id UUID NOT NULL REFERENCES clusters(cluster_id) ON DELETE RESTRICT,
    -- Foreign key to clusters
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events
    -- Event that belongs to this cluster
    
    membership_score NUMERIC(5,4),
    -- Membership score (0.0000 to 1.0000) indicating confidence in cluster membership
    -- NULL if score not computed
    -- NUMERIC(5,4) for precise decimal scoring
    
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When event was added to cluster
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT cluster_memberships_score_range CHECK (membership_score IS NULL OR (membership_score >= 0.0000 AND membership_score <= 1.0000)),
    CONSTRAINT cluster_memberships_unique_cluster_event UNIQUE (cluster_id, event_id)
    -- One event can belong to a cluster only once
    -- But same event can belong to different clusters (different model versions)
);

COMMENT ON TABLE cluster_memberships IS 'Many-to-many relationship: events belong to clusters. One event can belong to multiple clusters (one per model version).';
COMMENT ON COLUMN cluster_memberships.cluster_id IS 'Foreign key to clusters. Event belongs to this cluster.';
COMMENT ON COLUMN cluster_memberships.event_id IS 'Foreign key to raw_events. Event that belongs to this cluster.';
COMMENT ON COLUMN cluster_memberships.membership_score IS 'Membership score (0.0000 to 1.0000) indicating confidence in cluster membership. NULL if score not computed.';

-- ============================================================================
-- NOVELTY SCORES
-- ============================================================================
-- Novelty scores computed by AI for events
-- Indicates how novel/unusual an event is compared to historical patterns

CREATE TABLE novelty_scores (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events
    -- Novelty score is computed for a specific event
    
    model_version_id UUID NOT NULL REFERENCES ai_model_versions(model_version_id) ON DELETE RESTRICT,
    -- Foreign key to ai_model_versions
    -- Novelty score is computed using a specific model version
    
    novelty_score NUMERIC(5,4) NOT NULL,
    -- Novelty score (0.0000 to 1.0000)
    -- 0.0000 = very common, 1.0000 = very novel/unusual
    -- NUMERIC(5,4) for precise decimal scoring
    
    percentile_rank INTEGER,
    -- Percentile rank (0 to 100) of novelty score in historical distribution
    -- NULL if percentile not computed
    -- INTEGER sufficient for percentile ranks (0 to 100)
    
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When novelty score was computed
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT novelty_scores_score_range CHECK (novelty_score >= 0.0000 AND novelty_score <= 1.0000),
    CONSTRAINT novelty_scores_percentile_range CHECK (percentile_rank IS NULL OR (percentile_rank >= 0 AND percentile_rank <= 100)),
    CONSTRAINT novelty_scores_unique_event_model UNIQUE (event_id, model_version_id)
    -- One novelty score per event per model version
);

COMMENT ON TABLE novelty_scores IS 'Novelty scores computed by AI for events. Indicates how novel/unusual an event is compared to historical patterns. Metadata only, versioned.';
COMMENT ON COLUMN novelty_scores.event_id IS 'Foreign key to raw_events. Novelty score is computed for a specific event.';
COMMENT ON COLUMN novelty_scores.model_version_id IS 'Foreign key to ai_model_versions. Novelty score is computed using a specific model version.';
COMMENT ON COLUMN novelty_scores.novelty_score IS 'Novelty score (0.0000 to 1.0000). 0.0000 = very common, 1.0000 = very novel/unusual.';
COMMENT ON COLUMN novelty_scores.percentile_rank IS 'Percentile rank (0 to 100) of novelty score in historical distribution. NULL if percentile not computed.';

-- ============================================================================
-- SHAP EXPLANATIONS (REFERENCES, NOT BLOBS)
-- ============================================================================
-- SHAP (SHapley Additive exPlanations) explanations for AI predictions
-- References only, not blobs

CREATE TABLE shap_explanations (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events
    -- SHAP explanation is for a specific event
    
    model_version_id UUID NOT NULL REFERENCES ai_model_versions(model_version_id) ON DELETE RESTRICT,
    -- Foreign key to ai_model_versions
    -- SHAP explanation is for a specific model version
    
    prediction_value NUMERIC(10,6),
    -- AI prediction value (if applicable)
    -- NULL if prediction value not stored
    -- NUMERIC(10,6) for precise decimal values
    
    shap_explanation_hash_sha256 CHAR(64) NOT NULL,
    -- SHA256 hash of SHAP explanation (for reference)
    -- SHAP explanation itself is stored externally (not in database)
    -- CHAR(64) for exactly 64 hex characters
    
    shap_explanation_size INTEGER NOT NULL,
    -- Size of SHAP explanation (number of feature contributions)
    -- INTEGER sufficient for SHAP explanation sizes (typically < 10000)
    
    shap_explanation_storage_path TEXT,
    -- External storage path where SHAP explanation is stored
    -- NULL if SHAP explanation is not stored externally
    -- TEXT for unlimited length (paths can be long)
    -- NOTE: This is a reference, not the actual SHAP explanation
    
    top_features_contributions JSONB,
    -- Top N feature contributions as JSONB (for quick access)
    -- Example: [{"feature": "file_path", "contribution": 0.123}, ...]
    -- NULL if not extracted
    -- JSONB for efficient querying and indexing
    -- Limited to top N features (not full explanation)
    
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When SHAP explanation was computed
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT shap_explanations_hash_format CHECK (shap_explanation_hash_sha256 ~ '^[a-fA-F0-9]{64}$'),
    CONSTRAINT shap_explanations_size_positive CHECK (shap_explanation_size > 0),
    CONSTRAINT shap_explanations_unique_event_model UNIQUE (event_id, model_version_id)
    -- One SHAP explanation per event per model version
);

COMMENT ON TABLE shap_explanations IS 'SHAP (SHapley Additive exPlanations) explanations for AI predictions. References only, not blobs. SHAP explanations are stored externally, not in database.';
COMMENT ON COLUMN shap_explanations.event_id IS 'Foreign key to raw_events. SHAP explanation is for a specific event.';
COMMENT ON COLUMN shap_explanations.model_version_id IS 'Foreign key to ai_model_versions. SHAP explanation is for a specific model version.';
COMMENT ON COLUMN shap_explanations.shap_explanation_hash_sha256 IS 'SHA256 hash of SHAP explanation (for reference). SHAP explanation itself is stored externally (not in database). Used for SHAP explanation integrity verification.';
COMMENT ON COLUMN shap_explanations.shap_explanation_storage_path IS 'External storage path where SHAP explanation is stored. NULL if SHAP explanation is not stored externally. This is a reference, not the actual SHAP explanation.';
COMMENT ON COLUMN shap_explanations.top_features_contributions IS 'Top N feature contributions as JSONB (for quick access). Limited to top N features (not full explanation). Example: [{"feature": "file_path", "contribution": 0.123}, ...]. NULL if not extracted.';

-- ============================================================================
-- INDEXES (AI METADATA)
-- ============================================================================

-- AI model versions: Find models by type
CREATE INDEX idx_ai_model_versions_model_type 
    ON ai_model_versions(model_type);

-- AI model versions: Find active models (not deprecated)
CREATE INDEX idx_ai_model_versions_deprecated 
    ON ai_model_versions(deprecated_at) 
    WHERE deprecated_at IS NULL;

-- AI model versions: Find models by deployment time
CREATE INDEX idx_ai_model_versions_deployed_at 
    ON ai_model_versions(deployed_at DESC);

-- Feature vectors: Find feature vectors by event
CREATE INDEX idx_feature_vectors_event_id 
    ON feature_vectors(event_id);

-- Feature vectors: Find feature vectors by model version
CREATE INDEX idx_feature_vectors_model_version_id 
    ON feature_vectors(model_version_id);

-- Feature vectors: Find feature vectors by status
CREATE INDEX idx_feature_vectors_status 
    ON feature_vectors(status);

-- Feature vectors: Find feature vectors by hash (for integrity verification)
CREATE INDEX idx_feature_vectors_hash 
    ON feature_vectors(feature_vector_hash_sha256);

-- Clusters: Find clusters by model version
CREATE INDEX idx_clusters_model_version_id 
    ON clusters(model_version_id);

-- Clusters: Find clusters by status
CREATE INDEX idx_clusters_status 
    ON clusters(status);

-- Clusters: Find active clusters
CREATE INDEX idx_clusters_active 
    ON clusters(status) 
    WHERE status = 'ACTIVE';

-- Clusters: Find clusters by type
CREATE INDEX idx_clusters_cluster_type 
    ON clusters(cluster_type) 
    WHERE cluster_type IS NOT NULL;

-- Clusters: Find clusters by creation time
CREATE INDEX idx_clusters_cluster_created_at 
    ON clusters(cluster_created_at DESC);

-- Clusters: Find merged clusters
CREATE INDEX idx_clusters_merged 
    ON clusters(merged_into_cluster_id) 
    WHERE merged_into_cluster_id IS NOT NULL;

-- Cluster memberships: Find memberships by cluster
CREATE INDEX idx_cluster_memberships_cluster_id 
    ON cluster_memberships(cluster_id);

-- Cluster memberships: Find memberships by event
CREATE INDEX idx_cluster_memberships_event_id 
    ON cluster_memberships(event_id);

-- Cluster memberships: Find memberships by score (high-confidence memberships)
CREATE INDEX idx_cluster_memberships_score 
    ON cluster_memberships(membership_score DESC) 
    WHERE membership_score IS NOT NULL AND membership_score >= 0.7;

-- Novelty scores: Find novelty scores by event
CREATE INDEX idx_novelty_scores_event_id 
    ON novelty_scores(event_id);

-- Novelty scores: Find novelty scores by model version
CREATE INDEX idx_novelty_scores_model_version_id 
    ON novelty_scores(model_version_id);

-- Novelty scores: Find high novelty events (novelty >= 0.8)
CREATE INDEX idx_novelty_scores_high_novelty 
    ON novelty_scores(novelty_score DESC) 
    WHERE novelty_score >= 0.8;

-- Novelty scores: Find novelty scores by percentile (high percentile = novel)
CREATE INDEX idx_novelty_scores_percentile 
    ON novelty_scores(percentile_rank DESC) 
    WHERE percentile_rank IS NOT NULL AND percentile_rank >= 90;

-- SHAP explanations: Find SHAP explanations by event
CREATE INDEX idx_shap_explanations_event_id 
    ON shap_explanations(event_id);

-- SHAP explanations: Find SHAP explanations by model version
CREATE INDEX idx_shap_explanations_model_version_id 
    ON shap_explanations(model_version_id);

-- SHAP explanations: Find SHAP explanations by hash (for integrity verification)
CREATE INDEX idx_shap_explanations_hash 
    ON shap_explanations(shap_explanation_hash_sha256);

-- SHAP explanations: Find SHAP explanations by computation time
CREATE INDEX idx_shap_explanations_computed_at 
    ON shap_explanations(computed_at DESC);

-- SHAP explanations: Query top features contributions (if indexed)
-- Note: JSONB GIN index may be added if top_features_contributions queries are frequent
