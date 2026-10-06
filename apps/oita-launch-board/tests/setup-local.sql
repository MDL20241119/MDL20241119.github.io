-- LOCAL TEST DATABASE ONLY. Never apply these identities to production.
INSERT OR IGNORE INTO members (user_id,email,role) VALUES ('qa-owner','qa-owner@example.test','owner');
INSERT OR IGNORE INTO members (user_id,email,role) VALUES ('local_seedy','seedy@sites.test','owner');
