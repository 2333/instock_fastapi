from pathlib import Path

from app.models.stock_model import Stock

MIGRATION_PATH = Path("alembic/versions/2026_04_16_0003-stock_classification_metadata.py")


def test_stock_model_exposes_classification_provenance_columns():
    for column in (
        "industry_label",
        "industry_taxonomy",
        "industry_source",
        "industry_updated_at",
    ):
        assert column in Stock.__table__.columns


def test_stock_classification_migration_adds_and_removes_columns():
    migration = MIGRATION_PATH.read_text()

    assert 'down_revision: Union[str, None] = "m1_required_fact_tables"' in migration
    for column in (
        "industry_label",
        "industry_taxonomy",
        "industry_source",
        "industry_updated_at",
    ):
        assert f'op.add_column("stocks", sa.Column("{column}"' in migration
        assert f'op.drop_column("stocks", "{column}")' in migration
