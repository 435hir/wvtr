-- ============================================
-- WVTR Database Schema v2
-- Women's & Men's Volleyball Team Rating
-- ============================================

-- Команды: свой внутренний ID, каноническое название
CREATE TABLE teams (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(200) NOT NULL,
    country  VARCHAR(3),               -- ISO код страны клуба (TUR, ITA, FRA...)
    gender   VARCHAR(1) NOT NULL        -- 'M' или 'W'
);

-- Алиасы команд: связь внешних источников с нашими командами
-- Одна команда может иметь сколько угодно алиасов
CREATE TABLE team_aliases (
    id          SERIAL PRIMARY KEY,
    team_id     INTEGER NOT NULL REFERENCES teams(id),
    source      VARCHAR(20) NOT NULL,   -- 'fivb', 'cev', 'dataproject'
    external_id VARCHAR(50),            -- ID команды на внешнем ресурсе
    name        VARCHAR(200) NOT NULL,  -- название как написано на ресурсе
    code        VARCHAR(20),            -- аббревиатура на ресурсе
    UNIQUE(source, external_id)
);

-- Турниры: свой ID, сезон и вес для рейтинга
CREATE TABLE tournaments (
    id          SERIAL PRIMARY KEY,
    source      VARCHAR(20) NOT NULL,   -- 'fivb', 'cev', 'dataproject'
    external_id VARCHAR(50),            -- ID турнира на ресурсе
    name        VARCHAR(200) NOT NULL,  -- человекочитаемое название
    season      VARCHAR(9) NOT NULL,    -- '2024/2025' или '2025'
    type        VARCHAR(50),            -- 'champions_league', 'cev_cup', 'challenge_cup'
    gender      VARCHAR(1) NOT NULL,    -- 'M' или 'W'
    weight      NUMERIC(2,1),           -- вес для рейтинга: 1.0 / 0.7 / 0.4
    UNIQUE(source, external_id)
);

-- Матчи: ссылаются на внутренние ID команд и турниров
CREATE TABLE matches (
    id            SERIAL PRIMARY KEY,
    source        VARCHAR(20) NOT NULL,   -- 'fivb', 'cev'
    external_id   VARCHAR(50),            -- ID матча на ресурсе
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    team_a_id     INTEGER NOT NULL REFERENCES teams(id),
    team_b_id     INTEGER NOT NULL REFERENCES teams(id),
    score_a       INTEGER,                -- сеты выиграны командой A
    score_b       INTEGER,                -- сеты выиграны командой B
    match_date    DATE,
    status        VARCHAR(20),
    UNIQUE(source, external_id)
);

-- Сеты: составной первичный ключ
CREATE TABLE sets (
    match_id    INTEGER NOT NULL REFERENCES matches(id),
    set_number  INTEGER NOT NULL,
    points_a    INTEGER NOT NULL,          -- очки команды A в сете
    points_b    INTEGER NOT NULL,          -- очки команды B в сете
    PRIMARY KEY (match_id, set_number)
);
