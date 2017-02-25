-- llin Tables, Samuel Sekiwere, 2016-10-23
-- remeber to add indexes
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION "uuid-ossp";
CREATE EXTENSION plpythonu;
CREATE EXTENSION hstore;

-- webpy sessions
CREATE TABLE sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);

CREATE TABLE user_roles (
    id SERIAL NOT NULL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    descr text DEFAULT '',
    cdate TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX user_roles_idx1 ON user_roles(name);

CREATE TABLE user_role_permissions (
    id SERIAL NOT NULL PRIMARY KEY,
    user_role INTEGER NOT NULL REFERENCES user_roles ON DELETE CASCADE ON UPDATE CASCADE,
    Sys_module TEXT NOT NULL, -- the name of the module - defined above this level
    sys_perms VARCHAR(16) NOT NULL,
    unique(sys_module,user_role)
);

CREATE TABLE users (
    id bigserial NOT NULL PRIMARY KEY,
    user_role  INTEGER NOT NULL REFERENCES user_roles ON DELETE RESTRICT ON UPDATE CASCADE, --(call agents, admin, service providers)
    firstname TEXT NOT NULL DEFAULT '',
    lastname TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL UNIQUE,
    telephone TEXT NOT NULL UNIQUE, -- acts as the username
    password TEXT NOT NULL, -- blowfish hash of password
    email TEXT NOT NULL DEFAULT '',
    allowed_ips TEXT NOT NULL DEFAULT '127.0.0.1;::1', -- semi-colon separated list of allowed ip masks
    denied_ips TEXT NOT NULL DEFAULT '', -- semi-colon separated list of denied ip masks
    failed_attempts TEXT DEFAULT '0/'||to_char(now(),'yyyymmdd'),
    transaction_limit TEXT DEFAULT '0/'||to_char(now(),'yyyymmdd'),
    is_active BOOLEAN NOT NULL DEFAULT 't',
    is_system_user BOOLEAN NOT NULL DEFAULT 'f',
    last_login TIMESTAMPTZ,
    last_passwd_update TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX users_idx1 ON users(telephone);
CREATE INDEX users_idx2 ON users(username);

CREATE TABLE audit_log (
        id BIGSERIAL NOT NULL PRIMARY KEY,
        logtype VARCHAR(32) NOT NULL DEFAULT '',
        actor TEXT NOT NULL,
        action text NOT NULL DEFAULT '',
        remote_ip INET,
        detail TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id), -- like actor id
        created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX au_idx1 ON audit_log(cdate);
CREATE INDEX au_idx2 ON audit_log(logtype);
CREATE INDEX au_idx4 ON audit_log(action);

CREATE TABLE configs (
        id serial NOT NULL PRIMARY KEY,
        item TEXT NOT NULL UNIQUE,
        val TEXT NOT NULL,
        detail TEXT DEFAULT '',
        created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE countries(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT ''
);

CREATE TABLE locationtree(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP

);


CREATE TABLE locationtype(
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES locationtree(id),
    name TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL,
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE locations(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES locationtree(id),
    type_id INTEGER NOT NULL REFERENCES locationtype(id), --Cascade
    uuid TEXT NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    tree_parent_id INTEGER REFERENCES locations(id),
    lft INTEGER NOT NULL,
    rght INTEGER NOT NULL,
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX locations_idx4 ON locations(lft);
CREATE INDEX locations_idx5 ON locations(rght);
CREATE INDEX locations_idx6 ON locations(code);

CREATE VIEW locations_view AS
    SELECT a.*, b.level FROM locations a, locationtype
    WHERE a.type_id = b.id;

--FUNCTIONS
CREATE OR REPLACE FUNCTION public.get_children(loc_id integer)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
    BEGIN
        FOR r IN SELECT * FROM locations_view WHERE tree_parent_id = loc_id
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION public.get_descendants(loc_id bigint)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft > our_lft AND rght < our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.get_descendants_including_self(loc_id bigint)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft >= our_lft AND rght <= our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.get_ancestors(loc_id integer)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft <= our_lft AND rght >= our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION gen_code() RETURNS TEXT AS
$delim$
import string
import random
from uuid import uuid4


def id_generator(size=12, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

return id_generator()
$delim$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION add_node(treeid INT, node_name TEXT, p_id INT) RETURNS BOOLEAN AS --p_id = id of node where to add
$delim$
    DECLARE
    new_lft INTEGER;
    lvl INTEGER;
    dummy TEXT;
    node_type INTEGER;
    child_type INTEGER;
    BEGIN
        IF node_name = '' THEN
            RAISE NOTICE 'Node name cannot be empty string';
            RETURN FALSE;
        END IF;
        SELECT level INTO lvl FROM locationtype WHERE id = (SELECT type_id FROM locations WHERE id = p_id);
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Cannot add node: failed to find level';
        END IF;
        SELECT rght, type_id INTO new_lft, node_type FROM locations WHERE id =  p_id AND tree_id = treeid;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No such node id= % ', p_id;
        END IF;

        SELECT id INTO child_type FROM locationtype WHERE level = lvl + 1 AND tree_id = tree_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'You cannot add to root node';
        END IF;

        SELECT name INTO dummy FROM locations WHERE name = node_name
            AND tree_id = treeid AND type_id = child_type AND tree_parent_id = p_id;
        IF FOUND THEN
            RAISE NOTICE 'Node already exists : %', node_name;
            RETURN FALSE;
        END IF;

        UPDATE locations SET lft = lft + 2 WHERE lft > new_lft AND tree_id = treeid;
        UPDATE locations SET rght = rght + 2 WHERE rght >= new_lft AND tree_id = treeid;
        INSERT INTO locations (uuid, name, lft, rght, tree_id,type_id, tree_parent_id)
        VALUES (uuid_generate_v4(), node_name, new_lft, new_lft+1, treeid, child_type, p_id);
        RETURN TRUE;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION delete_node(treeid INT, node_id BIGINT)
    RETURNS boolean AS $delim$
    DECLARE
        node_lft INTEGER;
    BEGIN
        SELECT lft INTO node_lft FROM locations
            WHERE id = node_id AND tree_id = treeid;
        IF NOT FOUND THEN RETURN FALSE; END IF;
        UPDATE locations SET lft = lft - 2 WHERE lft > node_lft AND tree_id = treeid;
        UPDATE locations SET rght = rght - 2 WHERE rght > node_lft AND tree_id = treeid;
        DELETE FROM locations WHERE id = node_id;
        RETURN TRUE;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_node_with_code(treeid INT, node_name TEXT, p_id INT) RETURNS BOOLEAN AS --p_id = id of node where to add
$delim$
    DECLARE
    new_lft INTEGER;
    lvl INTEGER;
    dummy TEXT;
    node_type INTEGER;
    child_type INTEGER;
    BEGIN
        IF node_name = '' THEN
            RAISE NOTICE 'Node name cannot be empty string';
            RETURN FALSE;
        END IF;
        SELECT level INTO lvl FROM locationtype WHERE id = (SELECT type_id FROM locations WHERE id = p_id);
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Cannot add node: failed to find level';
        END IF;
        SELECT rght, type_id INTO new_lft, node_type FROM locations WHERE id =  p_id AND tree_id = treeid;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No such node id= % ', p_id;
        END IF;

        SELECT id INTO child_type FROM locationtype WHERE level = lvl + 1 AND tree_id = tree_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'You cannot add to root node';
        END IF;

        SELECT name INTO dummy FROM locations WHERE name = node_name
            AND tree_id = treeid AND type_id = child_type AND tree_parent_id = p_id;
        IF FOUND THEN
            RAISE NOTICE 'Node already exists : %', node_name;
            RETURN FALSE;
        END IF;

        UPDATE locations SET lft = lft + 2 WHERE lft > new_lft AND tree_id = treeid;
        UPDATE locations SET rght = rght + 2 WHERE rght >= new_lft AND tree_id = treeid;
        INSERT INTO locations (uuid, code, name, lft, rght, tree_id,type_id, tree_parent_id)
        VALUES (uuid_generate_v4(), gen_code(), node_name, new_lft, new_lft+1, treeid, child_type, p_id);
        RETURN TRUE;
    END;
$delim$ LANGUAGE plpgsql;

CREATE TABLE distribution_points(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '',
    uuid TEXT NOT NULL DEFAULT uuid_generate_v4(),
    subcounty BIGINT REFERENCES locations(id),
    district_id BIGINT REFERENCES locations(id),
    created_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE distribution_point_villages(
    id SERIAL PRIMARY KEY NOT NULL,
    distribution_point BIGINT NOT NULL REFERENCES distribution_points ON DELETE CASCADE ON UPDATE CASCADE,
    village_id BIGINT NOT NULL REFERENCES locations ON DELETE CASCADE,
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stores(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    location BIGINT NOT NULL REFERENCES locations ON DELETE CASCADE,
    district_id BIGINT REFERENCES locations,
    created_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reporters(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    firstname TEXT NOT NULL DEFAULT '',
    lastname TEXT NOT NULL DEFAULT '',
    telephone TEXT NOT NULL DEFAULT '',
    alternate_tel TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    reporting_location BIGINT REFERENCES locations(id), --village
    distribution_point BIGINT REFERENCES distribution_points(id),
    uuid TEXT NOT NULL DEFAULT uuid_generate_v4(),
    code TEXT NOT NULL DEFAULT '',
    district_id BIGINT REFERENCES locations,
    reporting_location_name text not null default '',
    created_by INTEGER REFERENCES users(id), -- like actor id
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX reporters_idx1 ON reporters(telephone);
CREATE INDEX reporters_idx2 ON reporters(alternate_tel);
CREATE INDEX reporters_idx3 ON reporters(created);

CREATE TABLE reporter_groups(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    descr TEXT NOT NULL DEFAULT '',
    uuid TEXT NOT NULL DEFAULT uuid_generate_v4(),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reporter_groups_reporters(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    group_id INTEGER REFERENCES reporter_groups(id),
    reporter_id BIGINT REFERENCES reporters(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE warehouses(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL UNIQUE,
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE warehouse_branches(
    id SERIAL PRIMARY KEY NOT NULL,
    warehouse_id INTEGER REFERENCES warehouses(id) ON DELETE CASCADE ON UPDATE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subwarehouse(
    id SERIAL PRIMARY KEY NOT NULL,
    warehous_branche_id INTEGER REFERENCES warehouse_branches(id) ON DELETE CASCADE ON UPDATE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE manufacturers(
    id SERIAL PRIMARY KEY,
    name text NOT NULL UNIQUE,
    created_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE funding_sources(
    id SERIAL PRIMARY KEY,
    name text NOT NULL UNIQUE,
    created_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- used for scheduling messages
CREATE TABLE schedules(
    id SERIAL PRIMARY KEY NOT NULL,
    type TEXT NOT NULL DEFAULT 'sms', -- also 'push_contact'
    params JSON NOT NULL DEFAULT '{}'::json,
    run_time TIMESTAMP NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'ready',
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX schedules_idx ON schedules(run_time);
CREATE INDEX schedules_idx1 ON schedules(type);
CREATE INDEX schedules_idx2 ON schedules(status);

CREATE TABLE national_delivery_log(
    id SERIAL PRIMARY KEY NOT NULL,
    po_number TEXT NOT NULL DEFAULT '',
    funding_source INTEGER NOT NULL REFERENCES funding_sources(id),
    manufacturer INTEGER NOT NULL REFERENCES manufacturers(id),
    made_in INTEGER REFERENCES countries(id),
    batch_number TEXT NOT NULL DEFAULT '',
    nets_type TEXT NOT NULL DEFAULT '',
    nets_size TEXT NOT NULL DEFAULT '',
    nets_color TEXT NOT NULL DEFAULT '',
    quantity_bales NUMERIC NOT NULL DEFAULT 0,
    quantity NUMERIC NOT NULL DEFAULT 0,
    entry_date DATE,
    waybill TEXT NOT NULL,
    goods_received_note TEXT NOT NULL,
    warehouse_branch INTEGER NOT NULL REFERENCES warehouse_branches(id),
    sub_warehouse TEXT NOT NULL DEFAULT '',
    nda_samples INTEGER NOT NULL DEFAULT 0,
    nda_sampling_date DATE,
    nda_conditional_release_date DATE,
    nda_testing_result_date DATE,
    unbs_samples INTEGER NOT NULL DEFAULT 0,
    unbs_sampling_date DATE,
    remarks TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(waybill, goods_received_note)
);
CREATE INDEX national_delivery_log_idx1 ON national_delivery_log(waybill);
CREATE INDEX national_delivery_log_idx2 ON national_delivery_log(goods_received_note);
CREATE INDEX national_delivery_log_idx3 ON national_delivery_log(entry_date);
CREATE INDEX national_delivery_log_idx4 ON national_delivery_log(funding_source);

CREATE TABLE distribution_log(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    source TEXT CHECK (source IN ('national', 'subcounty', 'dp', 'village')),
    dest TEXT CHECK (dest IN ('subcounty', 'dp', 'village', 'household')),
    release_order TEXT NOT NULL DEFAULT '',
    waybill TEXT NOT NULL DEFAULT '',
    quantity_bales NUMERIC NOT NULL DEFAULT 0, -- qty sent in bales
    quantity_nets NUMERIC NOT NULL DEFAULT 0, -- qty total nets
    warehouse_branch INTEGER REFERENCES warehouse_branches(id), --source warehouse branch
    departure_date DATE,
    departure_time TIME,
    delivered_by INTEGER REFERENCES reporters(id),
    received_by INTEGER REFERENCES reporters(id),
    destination BIGINT REFERENCES locations(id),
    district BIGINT REFERENCES locations(id),
    dest_distribution_point BIGINT REFERENCES distribution_points(id),
    track_no_plate TEXT NOT NULL DEFAULT '',
    remarks TEXT NOT NULL DEFAULT '',
    arrival_date DATE,
    arrival_time TIME,
    is_delivered BOOLEAN DEFAULT 'f',
    is_received BOOLEAN DEFAULT 'f',
    has_variance BOOLEAN DEFAULT 'f',
    quantity_received NUMERIC NOT NULL DEFAULT 0, -- qty received by reporter
    created_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX distribution_log_idx1 ON distribution_log(waybill);
CREATE INDEX distribution_log_idx2 ON distribution_log(source);
CREATE INDEX distribution_log_idx3 ON distribution_log(dest);
CREATE INDEX distribution_log_idx4 ON distribution_log(departure_date);
CREATE INDEX distribution_log_idx5 ON distribution_log(is_delivered);
CREATE INDEX distribution_log_idx6 ON distribution_log(warehouse_branch);

CREATE TABLE village_distribution_log(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    distribution_log_id BIGINT NOT NULL REFERENCES distribution_log(id) ON DELETE CASCADE ON UPDATE CASCADE,
    village_id BIGINT NOT NULL REFERENCES locations(id) ON DELETE CASCADE ON UPDATE CASCADE,
    quantity_received NUMERIC NOT NULL DEFAULT 0,
    date DATE,
    received_by INTEGER REFERENCES reporters(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(distribution_log_id, village_id)
);

CREATE TABLE household_distribution_log(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    vdist_id BIGINT REFERENCES village_distribution_log(id) ON DELETE CASCADE ON UPDATE CASCADE, -- helps to check if giving more than we have
    distribution_date DATE,
    quantity NUMERIC NOT NULL DEFAULT 0,
    reporter_id BIGINT REFERENCES reporters(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

);

CREATE TABLE distribution_log_schedules(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    distribution_log_id BIGINT REFERENCES distribution_log(id) ON DELETE CASCADE ON UPDATE CASCADE,
    schedule_id BIGINT REFERENCES schedules(id) ON DELETE CASCADE ON UPDATE CASCADE,
    level TEXT NOT NULL,
    triggered_by BIGINT REFERENCES locations(id), --which administrative level is the person triggering the notification
    --type TEXT NOT NULL DEFAULT '' -- one of 'REC' or 'DIST'
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(distribution_log_id, schedule_id, level)
);

CREATE TABLE alerts(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    district_id BIGINT REFERENCES locations(id),
    reporting_location BIGINT REFERENCES locations(id),
    alert TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP VIEW IF EXISTS distribution_log_w2sc_view;
CREATE VIEW distribution_log_w2sc_view AS
    -- view to show distribution from warehouse to subcounty
    SELECT a.id, a.release_order, a.waybill, a.quantity_bales,
        a.quantity_nets, b.name as warehouse, c.name as branch,
        a.departure_date, a.departure_time,
        get_location_name(a.destination) as destination,
        a.destination destination_id,
        a.district_id,
        get_location_name(a.district_id) as district, a.remarks,
        a.arrival_date, a.arrival_time, a.quantity_received,
        a.is_delivered, a.is_received, a.has_variance, a.created_by,
        d.firstname as delivered_by, d.telephone,
        to_char(a.created, 'YYYY-MM-DD') as created,
        to_char(a.updated, 'YYYY-MM-DD') as updated
    FROM
        distribution_log a, warehouses b, warehouse_branches c, reporters d
    WHERE
        a.source = 'national' AND a.dest = 'subcounty'
        AND a.warehouse_branch = c.id AND (b.id = c.warehouse_id)
        AND a.delivered_by = d.id;

DROP VIEW IF EXISTS distribution_log_sc2dp_view; -- subcounty to distribution point
CREATE VIEW distribution_log_sc2dp_view AS
    -- view to show distribution from subcounty to disribution point
    SELECT a.id, a.release_order, a.waybill, a.quantity_bales,
        a.quantity_nets,
        a.departure_date, a.departure_time,
        get_location_name(a.destination) as destination,
        get_location_name(a.district_id) as district, a.remarks,
        a.arrival_date, a.arrival_time, a.quantity_received,
        a.is_delivered, a.is_received, a.has_variance, a.created_by,
        d.firstname as delivered_by, d.telephone,
        d.id as reporter_id, d.reporting_location as subcounty,
        to_char(a.created, 'YYYY-MM-DD') as created,
        to_char(a.updated, 'YYYY-MM-DD') as updated
    FROM
        distribution_log a, reporters d
    WHERE
        a.source = 'subcounty' AND a.dest = 'dp'
        AND a.delivered_by = d.id;

CREATE TABLE registration_forms(
    id SERIAL PRIMARY KEY NOT NULL,
    reporter_id BIGINT REFERENCES reporters(id) ON DELETE CASCADE,
    serial_number TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE kannel_stats(
    id SERIAL PRIMARY KEY NOT NULL,
    month TEXT NOT NULL DEFAULT '',
    stats JSON NOT NULL DEFAULT '{}'::json,
    created TIMESTAMP NOT NULL DEFAULT NOW(),
    updated TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE VIEW sms_stats AS
    SELECT
        id,
        month,
        stats->>'mtn_in' as mtn_in,
        stats->>'mtn_out' as mtn_out,
        stats->>'airtel_in' as airtel_in,
        stats->>'airtel_out' as airtel_out,
        stats->>'africel_in' as africel_in,
        stats->>'africel_out' as africel_out,
        stats->>'utl_in' as utl_in,
        stats->>'utl_out' as utl_out,
        stats->>'others_in' as others_in,
        stats->>'others_out' as others_out,
        stats->>'total_in' as total_in,
        stats->>'total_out' as total_out,
        created,
        updated
    FROM kannel_stats;

--location stuff
--INSERT INTO locationtree (name)
--    VALUES ('Administrative');
--
--INSERT INTO locationtype (tree_id, name, level)
--    VALUES
--        ((SELECT id FROM locationtree WHERE name ='Administrative'), 'country', 0),
--        ((SELECT id FROM locationtree WHERE name ='Administrative'), 'region', 1),
--        ((SELECT id FROM locationtree WHERE name ='Administrative'), 'district', 2),
--        --((SELECT id FROM locationtree WHERE name ='Administrative'), 'county', 3),
--        ((SELECT id FROM locationtree WHERE name ='Administrative'), 'subcounty', 3),
--        ((SELECT id FROM locationtree WHERE name ='Administrative'), 'parish', 4),
--        ((SELECT id FROM locationtree WHERE name ='Administrative'), 'village', 5);
--
--INSERT INTO locations (tree_id, type_id, name, lft, rght)
--    VALUES
--        ((SELECT id FROM locationtree WHERE name = 'Administrative'),
--            (SELECT id FROM locationtype WHERE name = 'country'),
--            'Uganda', 1, 2);
--SELECT add_node(1, 'Central', 1);
--SELECT add_node(1, 'Eastern', 1);
--SELECT add_node(1, 'Western', 1);
--SELECT add_node(1, 'Northern', 1);
-- \i iva_ug_location_data.sql
INSERT INTO user_roles(name, descr)
VALUES('Administrator','For the Administrators'), ('Basic', 'For the basic users'), ('Warehouse Manager', 'The warehouse manager');

INSERT INTO user_role_permissions(user_role, sys_module,sys_perms)
VALUES
        ((SELECT id FROM user_roles WHERE name ='Administrator'),'Users','rw');

INSERT INTO users(firstname,lastname,username,telephone,password,email,user_role,is_system_user)
VALUES
        ('Samuel','Sekiwere','admin', '+256782820208', crypt('admin',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='Administrator'),'t'),
        ('Guest','User','guest', '+256753475676', crypt('guest',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='Basic'),'t'),
        ('Ivan','Muguya','ivan', '+256756253430', crypt('ivan',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='Warehouse Manager'),'f');

INSERT INTO reporter_groups (name, descr)
VALUES
    ('VHT', 'Village Health Team Members'),
    ('Subcounty Store Manager', ''),
    ('Subcounty Chief', ''),
    ('L3', 'Local council 3 Chairperson'),
    ('DHO', 'District Health Officer'),
    ('Driver', ''),
    ('Distribution Point Agent', ''),
    ('DSO', 'District Security Officer');
-- sample distribution points
insert into distribution_points (name, uuid, code, subcounty) values('Pece Stadium', uuid_generate_v4(), gen_code(), 407);

CREATE OR REPLACE FUNCTION public.get_district(loc_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r TEXT := '';
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT name into r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'district');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_district_id(loc_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r BIGINT;
        our_lft BIGINT;
        our_rght BIGINT;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT id INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'district');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_subcounty_id(loc_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r BIGINT;
        our_lft BIGINT;
        our_rght BIGINT;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT id INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'subcounty');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_ancestor_by_type(loc_id bigint, atype text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r TEXT := '';
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT name INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = atype);
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_location_name(loc_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
        xname TEXT;
    BEGIN
        SELECT INTO xname name FROM locations WHERE id = loc_id;
        IF xname IS NULL THEN
            RETURN '';
        END IF;
        RETURN xname;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_distributionpoint_name(loc_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
        xname TEXT;
    BEGIN
        SELECT INTO xname name FROM distribution_points WHERE id = loc_id;
        IF xname IS NULL THEN
            RETURN '';
        END IF;
        RETURN xname;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_distribution_point_locations(dpoint bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
    r TEXT;
    p TEXT;
    BEGIN
        r := '';
        FOR p IN SELECT name FROM locations WHERE id IN
            (SELECT village_id FROM distribution_point_villages WHERE distribution_point = dpoint) LOOP
            r := r || p || ', ';
        END LOOP;
        r := rtrim(r, ' ');
        RETURN rtrim(r,',');
    END;
$function$;


CREATE OR REPLACE FUNCTION public.get_reporter_groups(_reporter_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
    r TEXT;
    p TEXT;
    BEGIN
        r := '';
        FOR p IN SELECT name FROM reporter_groups WHERE id IN
            (SELECT group_id FROM reporter_groups_reporters WHERE reporter_id = _reporter_id) LOOP
            r := r || p || ',';
        END LOOP;
        RETURN rtrim(r,',');
    END;
$function$;

CREATE VIEW reporters_view AS
    SELECT a.id, a.firstname, a.lastname, a.telephone, a.alternate_tel, a.email, a.national_id,
        a.reporting_location, a.distribution_point, get_distributionpoint_name(a.distribution_point) as dpoint,
        get_district(a.reporting_location) as district, get_reporter_groups(a.id) as role, b.name as loc_name
    FROM reporters a, locations b
    WHERE a.reporting_location = b.id;

CREATE VIEW reporters_view2 AS
    SELECT a.id, a.firstname, a.lastname, a.telephone, a.alternate_tel, a.email, a.national_id,
        a.reporting_location, a.created_by,
        --get_district(a.reporting_location) as district,
        --get_district_id(a.reporting_location) as district_id,
        get_reporter_groups(a.id) as role, b.name as loc_name,
        b.code as location_code
    FROM reporters a, locations b
    WHERE a.reporting_location = b.id;

CREATE VIEW reporters_view4 AS
    SELECT a.id, a.firstname, a.lastname, a.telephone, a.alternate_tel, a.email, a.national_id,
        a.reporting_location, a.created_by, c.name as district, a.district_id,
        --get_district(a.reporting_location) as district,
        --get_district_id(a.reporting_location) as district_id,
        get_reporter_groups(a.id) as role, b.name as loc_name,
        b.code as location_code
    FROM reporters a, locations b, locations c
    WHERE a.reporting_location = b.id and (a.district_id = c.id);




DROP VIEW IF EXISTS registration_forms_view;
CREATE VIEW registration_forms_view AS
    SELECT
        a.firstname, a.lastname, a.email, a.uuid, a.telephone, a.alternate_tel, a.code as reporter_code,
        b.serial_number as form_serial, to_char(b.created, 'YYYY-MM-DD HH24:MI') as created,
        b.created as cdate, c.name as location_name, c.code as location_code,
        c.uuid as location_uuid, c.id as location_id
    FROM
        reporters a, registration_forms b, locations c
    WHERE
        a.id = b.reporter_id AND c.id = a.reporting_location;

DROP VIEW IF EXISTS national_delivery_log_view;
CREATE VIEW national_delivery_log_view AS
    SELECT a.id, a.po_number, d.name as made_in, a.batch_number,
    a.nets_type, a.nets_size, a.nets_color, a.quantity_bales, a.quantity,
    to_char(a.entry_date, 'YYYY-MM-DD') as entry_date, a.waybill,
    a.goods_received_note, a.warehouse_branch, a.sub_warehouse, a.nda_samples,
    to_char(a.nda_sampling_date, 'YYYY-MM-DD') as nda_sampling_date,
    to_char(a.nda_conditional_release_date, 'YYYY-MM-DD') as nda_conditional_release_date,
    to_char(a.nda_testing_result_date,'YYYY-MM-DD') as nda_testing_result_date,
    a.unbs_samples,
    to_char(a.unbs_sampling_date, 'YYYY-MM-DD') as unbs_sampling_date,
    a.remarks, a.created_by,
    to_char(a.created, 'YYYY-MM-DD') as created,
    to_char(a.updated, 'YYYY-MM-DD') as updated,
    b.name as manufacturer_name,
    c.name as funding_source_name,
    e.name as warehouse, f.name as branch_name
    FROM
        national_delivery_log a,
        manufacturers b,
        funding_sources c,
        countries d,
        warehouses e,
        warehouse_branches f
    WHERE
        a.manufacturer = b.id
    AND
        a.funding_source = c.id
    AND
        a.made_in = d.id
    AND
        (a.warehouse_branch = f.id AND f.warehouse_id = e.id);
