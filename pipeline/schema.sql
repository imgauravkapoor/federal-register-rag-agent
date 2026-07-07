-- schema.sql
-- Ek hi table rakhi hai demo ke liye - simple aur samajhne mein easy.
-- document_number ko PRIMARY KEY banaya hai kyunki Federal Register ka har
-- document unique number rakhta hai - isse duplicate rows insert hone se bach jayenge.

CREATE DATABASE IF NOT EXISTS rag_agent_db;
USE rag_agent_db;

CREATE TABLE IF NOT EXISTS documents (
    document_number VARCHAR(50) PRIMARY KEY,
    title           TEXT,
    abstract        TEXT,
    publication_date DATE,
    agencies        VARCHAR(500),
    doc_type        VARCHAR(100),
    html_url        VARCHAR(500),
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
