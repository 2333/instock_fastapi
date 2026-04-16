from scripts.m1_backfill_rehearsal import build_rehearsal_plan, plan_to_dict, render_plan


def test_backfill_rehearsal_plan_includes_daily_bars_daily_basic_and_technical_factors():
    plan = build_rehearsal_plan("2024-01-02", "2024-01-05", code_limit=7)
    data = plan_to_dict(plan)

    assert data["dry_run"] is True
    assert data["start_date"] == "20240102"
    assert data["end_date"] == "20240105"
    assert data["code_limit"] == 7
    assert [step["table"] for step in data["steps"]] == [
        "daily_bars",
        "daily_basic",
        "technical_factors",
    ]

    bars_step, basic_step, technical_step = data["steps"]
    assert bars_step["mode"] == "bounded-job-dry-run"
    assert "scripts/run_m1_daily_bars_rehearsal.py" in bars_step["command"]
    assert "--code-limit 7" in bars_step["command"]
    assert "--source prefer_tushare" in bars_step["command"]
    assert bars_step["verification_queries"][0]["name"] == "row_count"
    assert "daily_bars" in bars_step["verification_queries"][0]["sql"]

    assert basic_step["mode"] == "bounded-job-dry-run"
    assert "scripts/run_m1_daily_basic_backfill.py" in basic_step["command"]
    assert "daily_basic" in basic_step["verification_queries"][0]["sql"]
    assert "curl -s" in basic_step["smoke_command"]

    assert technical_step["mode"] == "bounded-local-calculation-dry-run"
    assert "scripts/run_m1_technical_factors_backfill.py" in technical_step["command"]
    assert "technical_factors" in technical_step["verification_queries"][0]["sql"]
    assert "daily_bars_local" in technical_step["notes"][1]

    assert any("technical_factors" in query["sql"] for query in data["shared_verification_queries"])


def test_backfill_rehearsal_render_mentions_manual_gates():
    plan = build_rehearsal_plan("2024-01-02", "2024-01-05", code_limit=3)
    rendered = render_plan(plan)

    assert "# M1 Backfill Rehearsal Plan" in rendered
    assert "daily_bars" in rendered
    assert "daily_basic" in rendered
    assert "technical_factors" in rendered
    assert "Manual Gates" in rendered
    assert "duplicate_keys" in rendered
