-- =====================================================================
-- Seed data (run AFTER schema.sql). Passwords are placeholders:
-- create real hashes from the backend (passlib/bcrypt) and update users.
-- =====================================================================
BEGIN;

INSERT INTO departments (name, description) VALUES
 ('Electrical',  'Wiring, lighting, power outlets'),
 ('HVAC',        'Air conditioning, heating, ventilation'),
 ('Plumbing',    'Leaks, pipes, toilets, water supply'),
 ('IT',          'Network, computers, projectors'),
 ('Other',       'Furniture, doors, general facilities');

INSERT INTO buildings (name) VALUES
 ('Engineering Building'), ('Building A'), ('Building B'), ('Library');

INSERT INTO locations (building_id, floor, room) VALUES
 (1, 3, '301'), (1, 3, '302'), (1, 2, '204'),
 (2, 3, '301'), (2, 1, '101'),
 (3, 2, '204'), (3, 1, '105'),
 (4, 1, 'Reading Hall');

INSERT INTO users (name, student_id, email, role, department_id, password_hash) VALUES
 ('Admin User',      NULL,       'admin@campus.test',     'admin',   NULL, 'REPLACE_WITH_BCRYPT_HASH'),
 ('Electrical Staff',NULL,       'electrical@campus.test','staff',   1,    'REPLACE_WITH_BCRYPT_HASH'),
 ('HVAC Staff',      NULL,       'hvac@campus.test',      'staff',   2,    'REPLACE_WITH_BCRYPT_HASH'),
 ('Plumbing Staff',  NULL,       'plumbing@campus.test',  'staff',   3,    'REPLACE_WITH_BCRYPT_HASH'),
 ('IT Staff',        NULL,       'it@campus.test',        'staff',   4,    'REPLACE_WITH_BCRYPT_HASH'),
 ('Test Student 1',  'S0000001', 'student1@campus.test',  'student', NULL, 'REPLACE_WITH_BCRYPT_HASH'),
 ('Test Student 2',  'S0000002', 'student2@campus.test',  'student', NULL, 'REPLACE_WITH_BCRYPT_HASH'),
 ('Test Student 3',  'S0000003', 'student3@campus.test',  'student', NULL, 'REPLACE_WITH_BCRYPT_HASH');

COMMIT;
