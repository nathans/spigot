PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE items (feed text, link text, title text, hash text, date timestamp, posted timestamp);
INSERT INTO "items" VALUES('http://example.com/feed.xml','http://example.com/post/99','Post 99','DEADBEEF',NULL,NULL);
