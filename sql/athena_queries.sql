-- =============================================================================
-- athena_queries.sql
-- BMW Capstone P11 — Analytical Queries
--
-- These queries demonstrate the four required window metrics:
--   1. Average Speed
--   2. Average Battery Level
--   3. Maximum Temperature
--   4. Fault Count
--
-- Run in the AWS Athena Query Editor or via the AWS CLI:
--   aws athena start-query-execution \
--     --query-string "$(cat sql/athena_queries.sql)" \
--     --query-execution-context Database=bmw_capstone_p11 \
--     --result-configuration OutputLocation=s3://<YOUR_BUCKET>/athena-results/
-- =============================================================================

-- Q1: All aggregated windows — most recent first
--     Demonstrates the four required window metrics per vehicle
SELECT
    vehicle_id,
    window_start,
    window_end,
    ROUND(average_speed,         2) AS avg_speed_kmh,
    ROUND(average_battery_level, 2) AS avg_battery_pct,
    ROUND(maximum_temperature,   2) AS max_temp_celsius,
    fault_count,
    event_count
FROM bmw_capstone_p11.telemetry_aggregates
ORDER BY window_start DESC, vehicle_id
LIMIT 50;


-- Q2: Vehicle-level summary — average speed across all windows
SELECT
    vehicle_id,
    ROUND(AVG(average_speed), 2)         AS overall_avg_speed_kmh,
    COUNT(*)                              AS total_windows,
    SUM(event_count)                      AS total_events
FROM bmw_capstone_p11.telemetry_aggregates
GROUP BY vehicle_id
ORDER BY overall_avg_speed_kmh DESC;


-- Q3: Vehicle-level summary — average battery level
SELECT
    vehicle_id,
    ROUND(AVG(average_battery_level), 2)  AS overall_avg_battery_pct,
    MIN(average_battery_level)            AS min_battery_pct,
    MAX(average_battery_level)            AS max_battery_pct
FROM bmw_capstone_p11.telemetry_aggregates
GROUP BY vehicle_id
ORDER BY overall_avg_battery_pct ASC;


-- Q4: Vehicle-level summary — maximum temperature recorded
SELECT
    vehicle_id,
    MAX(maximum_temperature)              AS all_time_max_temp_celsius
FROM bmw_capstone_p11.telemetry_aggregates
GROUP BY vehicle_id
ORDER BY all_time_max_temp_celsius DESC;


-- Q5: Fault distribution — total fault events per vehicle
SELECT
    vehicle_id,
    SUM(fault_count)                      AS total_faults,
    SUM(event_count)                      AS total_events,
    ROUND(
        100.0 * SUM(fault_count) / NULLIF(SUM(event_count), 0), 2
    )                                     AS fault_rate_pct
FROM bmw_capstone_p11.telemetry_aggregates
GROUP BY vehicle_id
ORDER BY total_faults DESC;


-- Q6: Latest window per vehicle
--     Proves that newly arriving events produce new output windows
--     (run this query before and after the telemetry generator produces events)
SELECT
    vehicle_id,
    MAX(window_end)                       AS latest_window_end,
    MAX(window_start)                     AS latest_window_start
FROM bmw_capstone_p11.telemetry_aggregates
GROUP BY vehicle_id
ORDER BY latest_window_end DESC;


-- Q7: Windows processed in the last 30 minutes
--     Demonstrates real-time data arrival
SELECT
    vehicle_id,
    window_start,
    window_end,
    ROUND(average_speed,         2) AS avg_speed_kmh,
    ROUND(average_battery_level, 2) AS avg_battery_pct,
    fault_count,
    event_count
FROM bmw_capstone_p11.telemetry_aggregates
WHERE window_end >= (CURRENT_TIMESTAMP - INTERVAL '30' MINUTE)
ORDER BY window_end DESC;


-- Q8: High-temperature events — vehicles that exceeded 90°C
SELECT
    vehicle_id,
    window_start,
    window_end,
    maximum_temperature
FROM bmw_capstone_p11.telemetry_aggregates
WHERE maximum_temperature > 90.0
ORDER BY maximum_temperature DESC;


-- Q9: Critical fault windows — fault_count > 0
SELECT
    vehicle_id,
    window_start,
    window_end,
    fault_count,
    event_count,
    ROUND(100.0 * fault_count / NULLIF(event_count, 0), 1) AS fault_rate_pct
FROM bmw_capstone_p11.telemetry_aggregates
WHERE fault_count > 0
ORDER BY fault_count DESC;


-- Q10: Total records loaded — sanity check for Athena / S3 connectivity
SELECT COUNT(*)  AS total_windows,
       MIN(window_start) AS earliest_window,
       MAX(window_end)   AS latest_window
FROM bmw_capstone_p11.telemetry_aggregates;
