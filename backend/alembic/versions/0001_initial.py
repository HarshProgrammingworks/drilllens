"""Create DrillLens schema on PostgreSQL/PostGIS."""

from alembic import op

from app.core.database import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'postgis') THEN
                CREATE EXTENSION IF NOT EXISTS postgis;
            END IF;
        END $$;
        """
    )
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
                ALTER TABLE well_coordinates ADD COLUMN IF NOT EXISTS location geography(Point, 4326);
                ALTER TABLE well_trajectories ADD COLUMN IF NOT EXISTS location geography(Point, 4326);
                CREATE INDEX IF NOT EXISTS ix_well_coordinates_gix ON well_coordinates USING GIST (location);
                CREATE INDEX IF NOT EXISTS ix_well_trajectories_gix ON well_trajectories USING GIST (location);
            END IF;
        END $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_fts ON historical_reports USING GIN (search_vector)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pages_fts ON report_pages USING GIN (search_vector)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_fts ON drilling_events USING GIN (search_vector)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evidence_fts ON evidence USING GIN (search_vector)")


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
