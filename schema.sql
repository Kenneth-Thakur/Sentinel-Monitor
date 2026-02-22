-- Sentinel Intel Storage Schema
-- SQLite database for persisting processed intelligence data

DROP TABLE IF EXISTS live_intel;

CREATE TABLE live_intel (
    name    TEXT    NOT NULL,
    country TEXT    NOT NULL,
    intel   TEXT    NOT NULL,
    source  TEXT    NOT NULL,
    risk    INTEGER NOT NULL,
    status  TEXT    NOT NULL,
    color   TEXT    NOT NULL,
    lat     TEXT    NOT NULL,
    lon     TEXT    NOT NULL
);
