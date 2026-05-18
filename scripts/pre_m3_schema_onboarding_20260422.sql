BEGIN;

ALTER TABLE daily_bars
    ADD CONSTRAINT uq_daily_bars_ts_code_trade_date_dt
    UNIQUE (ts_code, trade_date_dt);
CREATE INDEX IF NOT EXISTS ix_daily_bars_trade_date_dt ON daily_bars (trade_date_dt);

ALTER TABLE fund_flows
    ADD CONSTRAINT uq_fund_flows_ts_code_trade_date_dt
    UNIQUE (ts_code, trade_date_dt);
CREATE INDEX IF NOT EXISTS ix_fund_flows_trade_date_dt ON fund_flows (trade_date_dt);

ALTER TABLE indicators
    ADD CONSTRAINT uq_indicators_ts_code_trade_date_dt_name
    UNIQUE (ts_code, trade_date_dt, indicator_name);
CREATE INDEX IF NOT EXISTS ix_indicators_trade_date_dt ON indicators (trade_date_dt);

ALTER TABLE daily_basic
    ALTER COLUMN trade_date_dt SET NOT NULL,
    ALTER COLUMN turnover_rate TYPE NUMERIC(20, 6) USING turnover_rate::NUMERIC(20, 6),
    ALTER COLUMN turnover_rate_f TYPE NUMERIC(20, 6) USING turnover_rate_f::NUMERIC(20, 6),
    ALTER COLUMN volume_ratio TYPE NUMERIC(20, 6) USING volume_ratio::NUMERIC(20, 6),
    ALTER COLUMN total_share TYPE NUMERIC(30, 6) USING total_share::NUMERIC(30, 6),
    ALTER COLUMN float_share TYPE NUMERIC(30, 6) USING float_share::NUMERIC(30, 6),
    ALTER COLUMN free_share TYPE NUMERIC(30, 6) USING free_share::NUMERIC(30, 6),
    ALTER COLUMN total_mv TYPE NUMERIC(30, 6) USING total_mv::NUMERIC(30, 6),
    ALTER COLUMN circ_mv TYPE NUMERIC(30, 6) USING circ_mv::NUMERIC(30, 6);
ALTER TABLE daily_basic
    ADD CONSTRAINT uq_daily_basic_ts_code_trade_date_dt
    UNIQUE (ts_code, trade_date_dt);
CREATE INDEX IF NOT EXISTS ix_daily_basic_trade_date_dt ON daily_basic (trade_date_dt);

CREATE INDEX IF NOT EXISTS ix_patterns_trade_date_dt ON patterns (trade_date_dt);

DELETE FROM user_events
WHERE user_id IS NULL OR page IS NULL;

ALTER TABLE user_events
    ALTER COLUMN user_id SET NOT NULL,
    ALTER COLUMN page SET NOT NULL;
ALTER TABLE user_events
    ADD CONSTRAINT fk_user_events_user_id_users
    FOREIGN KEY (user_id) REFERENCES users (id);

COMMIT;
