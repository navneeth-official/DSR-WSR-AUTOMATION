-- Reference schema for jira_stories (managed by Alembic migrations)
-- Run: alembic upgrade head

CREATE TABLE IF NOT EXISTS jira_stories (
    jira_key            VARCHAR(50)   PRIMARY KEY,
    project_key         VARCHAR(50),
    project_name        VARCHAR(200)  NOT NULL,
    sprint_name         VARCHAR(200),
    sprint_start_date   DATE,
    sprint_end_date     DATE,
    summary             VARCHAR(500)  NOT NULL,
    description         TEXT,
    issue_type          VARCHAR(100),
    priority            VARCHAR(50),
    assignee            VARCHAR(200),
    reporter            VARCHAR(200),
    status              VARCHAR(100)  NOT NULL,
    story_points        NUMERIC(5, 2),
    created_date        DATE,
    updated_date        DATE,
    resolved_date       DATE,
    snapshot_date       DATE,
    title               VARCHAR(500),  -- populated later by AI team from summary + description
    completion          NUMERIC(5, 2), -- percentage 0-100 (inferred from status)
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_jira_stories_assignee      ON jira_stories (assignee);
CREATE INDEX IF NOT EXISTS ix_jira_stories_sprint_name   ON jira_stories (sprint_name);
CREATE INDEX IF NOT EXISTS ix_jira_stories_status        ON jira_stories (status);
CREATE INDEX IF NOT EXISTS ix_jira_stories_project_name  ON jira_stories (project_name);
CREATE INDEX IF NOT EXISTS ix_jira_stories_project_key   ON jira_stories (project_key);

COMMENT ON TABLE jira_stories IS 'Jira story details from Rovo AI for DSR/WSR reporting';
COMMENT ON COLUMN jira_stories.title IS 'AI-generated title from summary and description (filled later)';
COMMENT ON COLUMN jira_stories.completion IS 'Story completion percentage (0-100), inferred from status';
