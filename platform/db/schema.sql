-- =============================================================================
-- TAP control-plane schema (PostgreSQL 16)
-- System of record with row-level security on tenant_id (ARCHITECTURE.md §6).
--
-- Conventions:
--   * UUID primary keys (gen_random_uuid()), created_at timestamptz DEFAULT now()
--   * tenant_id FK on every tenant-scoped table + RLS policy `tenant_isolation`
--     USING (tenant_id = current_setting('app.tenant_id')::uuid)
--   * The application sets `SET app.tenant_id = '<uuid>'` per session/txn.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- -----------------------------------------------------------------------------
-- tenants (root of the hierarchy; NOT RLS-protected — admin plane only)
-- -----------------------------------------------------------------------------
CREATE TABLE tenants (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,
    isolation_tier  text NOT NULL DEFAULT 'pooled'
                    CHECK (isolation_tier IN ('pooled', 'siloed_runners', 'dedicated')),
    kms_key_arn     text,                       -- per-tenant state encryption key
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- projects
-- -----------------------------------------------------------------------------
CREATE TABLE projects (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        text NOT NULL,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

-- -----------------------------------------------------------------------------
-- workspaces — unit of state + variables + RBAC
-- -----------------------------------------------------------------------------
CREATE TABLE workspaces (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id                uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name                      text NOT NULL,
    environment               text NOT NULL DEFAULT 'dev',
    engine                    text NOT NULL DEFAULT 'terraform'
                              CHECK (engine IN ('terraform', 'opentofu')),
    engine_version            text NOT NULL DEFAULT '1.9.0',
    vcs_repo                  text,
    working_directory         text NOT NULL DEFAULT '.',
    variables                 jsonb NOT NULL DEFAULT '{}'::jsonb,
    auto_apply                boolean NOT NULL DEFAULT false,
    locked                    boolean NOT NULL DEFAULT false,
    current_state_version_id  uuid,   -- FK added after state_versions exists
    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, name)
);

-- -----------------------------------------------------------------------------
-- runs — governed executions
-- -----------------------------------------------------------------------------
CREATE TABLE runs (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    action             text NOT NULL
                       CHECK (action IN ('plan', 'apply', 'destroy', 'drift', 'cost', 'compliance')),
    status             text NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'planning', 'policy_check',
                                         'awaiting_approval', 'applying', 'verifying',
                                         'succeeded', 'failed', 'cancelled', 'compensated')),
    engine             text NOT NULL DEFAULT 'terraform'
                       CHECK (engine IN ('terraform', 'opentofu')),
    message            text,
    requested_by       text NOT NULL,            -- OIDC subject or agent identity
    auto_apply         boolean NOT NULL DEFAULT false,
    plan_artifact_uri  text,                     -- the evaluated artifact apply reuses
    cost_delta_usd     numeric(14, 4),
    temporal_workflow_id text,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- run_events — immutable run timeline
-- -----------------------------------------------------------------------------
CREATE TABLE run_events (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_id      uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sequence    bigint NOT NULL,
    event_type  text NOT NULL,                   -- run.created, run.plan_finished, ...
    payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, sequence)
);

-- -----------------------------------------------------------------------------
-- approvals — human gates signalled into Temporal
-- -----------------------------------------------------------------------------
CREATE TABLE approvals (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_id           uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    status           text NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    reason           text,
    requested_at     timestamptz NOT NULL DEFAULT now(),
    expires_at       timestamptz NOT NULL,
    decided_by       text,
    decided_at       timestamptz,
    decision_comment text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    CHECK (decided_at IS NULL OR decided_at >= requested_at)
);

-- -----------------------------------------------------------------------------
-- policy_sets — OPA bundles bound to workspaces
-- -----------------------------------------------------------------------------
CREATE TABLE policy_sets (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name               text NOT NULL,
    enforcement_level  text NOT NULL DEFAULT 'hard_fail'
                       CHECK (enforcement_level IN ('hard_fail', 'soft_fail', 'advisory')),
    bundle_uri         text NOT NULL,
    description        text,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE policy_set_workspaces (
    policy_set_id uuid NOT NULL REFERENCES policy_sets(id) ON DELETE CASCADE,
    workspace_id  uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tenant_id     uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    PRIMARY KEY (policy_set_id, workspace_id)
);

-- -----------------------------------------------------------------------------
-- policy_results — one row per policy-set evaluation of a run's plan
-- -----------------------------------------------------------------------------
CREATE TABLE policy_results (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_id             uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    policy_set_id      uuid REFERENCES policy_sets(id) ON DELETE SET NULL,
    allowed            boolean NOT NULL,
    enforcement_level  text NOT NULL
                       CHECK (enforcement_level IN ('hard_fail', 'soft_fail', 'advisory')),
    violations         jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at         timestamptz NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- agents / agent_versions / agent_executions / checkpoints
-- -----------------------------------------------------------------------------
CREATE TABLE agents (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        text NOT NULL,
    domain      text NOT NULL
                CHECK (domain IN ('appops', 'devops', 'secops', 'netops',
                                  'dataops', 'llmops', 'identity', 'costops')),
    enabled     boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE agent_versions (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_id            uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version             text NOT NULL,            -- semver
    manifest            jsonb NOT NULL,           -- full agent.yaml
    artifact_uri        text,                     -- signed OCI reference
    signature_verified  boolean NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (agent_id, version)
);

CREATE TABLE agent_executions (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_version_id  uuid NOT NULL REFERENCES agent_versions(id) ON DELETE CASCADE,
    run_id            uuid REFERENCES runs(id) ON DELETE SET NULL,
    task              text NOT NULL,
    outcome           text NOT NULL DEFAULT 'running'
                      CHECK (outcome IN ('running', 'succeeded', 'failed', 'cancelled')),
    summary           text,
    token_usage       jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE checkpoints (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_execution_id  uuid NOT NULL REFERENCES agent_executions(id) ON DELETE CASCADE,
    sequence            bigint NOT NULL,
    state               jsonb NOT NULL,           -- serialized AgentState snapshot
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (agent_execution_id, sequence)
);

-- -----------------------------------------------------------------------------
-- state_versions — versioned, encrypted Terraform state references
-- -----------------------------------------------------------------------------
CREATE TABLE state_versions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workspace_id  uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    run_id        uuid REFERENCES runs(id) ON DELETE SET NULL,
    serial        bigint NOT NULL,
    storage_uri   text NOT NULL,                  -- object-store URI (encrypted blob)
    checksum      text NOT NULL,                  -- sha256 of ciphertext
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, serial)
);

ALTER TABLE workspaces
    ADD CONSTRAINT workspaces_current_state_version_fk
    FOREIGN KEY (current_state_version_id) REFERENCES state_versions(id)
    ON DELETE SET NULL;

-- -----------------------------------------------------------------------------
-- audit_log — append-only (no UPDATE/DELETE granted to app role)
-- -----------------------------------------------------------------------------
CREATE TABLE audit_log (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    actor          text NOT NULL,                 -- OIDC subject / agent identity
    actor_type     text NOT NULL DEFAULT 'user'
                   CHECK (actor_type IN ('user', 'agent', 'system')),
    action         text NOT NULL,                 -- run.apply.approved, ...
    resource_type  text NOT NULL,
    resource_id    uuid,
    payload        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- Indexes
-- =============================================================================
CREATE INDEX idx_projects_tenant            ON projects (tenant_id);
CREATE INDEX idx_workspaces_tenant          ON workspaces (tenant_id);
CREATE INDEX idx_workspaces_project         ON workspaces (project_id);
CREATE INDEX idx_runs_tenant_created        ON runs (tenant_id, created_at DESC);
CREATE INDEX idx_runs_workspace_created     ON runs (workspace_id, created_at DESC);
CREATE INDEX idx_runs_status                ON runs (tenant_id, status)
    WHERE status NOT IN ('succeeded', 'failed', 'cancelled', 'compensated');
CREATE INDEX idx_run_events_run_seq         ON run_events (run_id, sequence);
CREATE INDEX idx_approvals_tenant_status    ON approvals (tenant_id, status);
CREATE INDEX idx_approvals_run              ON approvals (run_id);
CREATE INDEX idx_policy_results_run         ON policy_results (run_id);
CREATE INDEX idx_agents_tenant_domain       ON agents (tenant_id, domain);
CREATE INDEX idx_agent_versions_agent       ON agent_versions (agent_id);
CREATE INDEX idx_agent_versions_manifest    ON agent_versions USING gin (manifest jsonb_path_ops);
CREATE INDEX idx_agent_executions_version   ON agent_executions (agent_version_id, started_at DESC);
CREATE INDEX idx_checkpoints_execution      ON checkpoints (agent_execution_id, sequence DESC);
CREATE INDEX idx_state_versions_workspace   ON state_versions (workspace_id, serial DESC);
CREATE INDEX idx_audit_tenant_created       ON audit_log (tenant_id, created_at DESC);
CREATE INDEX idx_audit_action               ON audit_log (tenant_id, action);

-- =============================================================================
-- Row-level security: tenant isolation on every tenant-scoped table.
-- App connects as role `tap_app` and runs `SET app.tenant_id = '<uuid>'`.
-- =============================================================================
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'projects', 'workspaces', 'runs', 'run_events', 'approvals',
        'policy_sets', 'policy_set_workspaces', 'policy_results',
        'agents', 'agent_versions', 'agent_executions', 'checkpoints',
        'state_versions', 'audit_log'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I '
            'USING (tenant_id = current_setting(''app.tenant_id'')::uuid) '
            'WITH CHECK (tenant_id = current_setting(''app.tenant_id'')::uuid)',
            t
        );
    END LOOP;
END
$$;

-- Application role: full DML except audit_log is append-only.
-- CREATE ROLE tap_app LOGIN;  -- created by provisioning tooling
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tap_app;
-- REVOKE UPDATE, DELETE ON audit_log FROM tap_app;
-- REVOKE UPDATE, DELETE ON run_events FROM tap_app;

-- updated_at maintenance
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['tenants', 'projects', 'workspaces', 'runs', 'policy_sets', 'agents']
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION set_updated_at()', t, t
        );
    END LOOP;
END
$$;
