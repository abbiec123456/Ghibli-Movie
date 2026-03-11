--
-- PostgreSQL database dump
--

\restrict 0dCE7iiJQzvDfsSqDHppEXpK2lcM5sovrOY2WfWo2WXFH9qXdkqKMZkntX0kyhn

-- Dumped from database version 16.12
-- Dumped by pg_dump version 16.12

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: admin_role; Type: TYPE; Schema: public; Owner: ghibli_adm
--

CREATE TYPE public.admin_role AS ENUM (
    'admin',
    'editor',
    'viewer'
);


ALTER TYPE public.admin_role OWNER TO ghibli_adm;

--
-- Name: booking_status; Type: TYPE; Schema: public; Owner: ghibli_adm
--

CREATE TYPE public.booking_status AS ENUM (
    'pending',
    'approved',
    'cancelled'
);


ALTER TYPE public.booking_status OWNER TO ghibli_adm;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admins; Type: TABLE; Schema: public; Owner: ghibli_adm
--

CREATE TABLE public.admins (
    admin_id bigint NOT NULL,
    name text NOT NULL,
    email text NOT NULL,
    role text NOT NULL,
    password character varying(6)
);


ALTER TABLE public.admins OWNER TO ghibli_adm;

--
-- Name: admins_admin_id_seq; Type: SEQUENCE; Schema: public; Owner: ghibli_adm
--

ALTER TABLE public.admins ALTER COLUMN admin_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.admins_admin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: booking_modules; Type: TABLE; Schema: public; Owner: ghibli_adm
--

CREATE TABLE public.booking_modules (
    booking_id bigint NOT NULL,
    module_id bigint NOT NULL
);


ALTER TABLE public.booking_modules OWNER TO ghibli_adm;

--
-- Name: bookings; Type: TABLE; Schema: public; Owner: ghibli_adm
--

CREATE TABLE public.bookings (
    booking_id bigint NOT NULL,
    customer_id bigint NOT NULL,
    course_id bigint NOT NULL,
    nice_to_have_requests text,
    status text NOT NULL,
    locked boolean DEFAULT false NOT NULL,
    submitted_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.bookings OWNER TO ghibli_adm;

--
-- Name: bookings_booking_id_seq; Type: SEQUENCE; Schema: public; Owner: ghibli_adm
--

ALTER TABLE public.bookings ALTER COLUMN booking_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.bookings_booking_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: course_modules; Type: TABLE; Schema: public; Owner: ghibli_adm
--

CREATE TABLE public.course_modules (
    module_id bigint NOT NULL,
    course_id bigint NOT NULL,
    module_name text NOT NULL,
    module_description text,
    module_order integer,
    active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.course_modules OWNER TO ghibli_adm;

--
-- Name: course_modules_module_id_seq; Type: SEQUENCE; Schema: public; Owner: ghibli_adm
--

ALTER TABLE public.course_modules ALTER COLUMN module_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.course_modules_module_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: courses; Type: TABLE; Schema: public; Owner: ghibli_adm
--

CREATE TABLE public.courses (
    course_id bigint NOT NULL,
    course_name text NOT NULL,
    description text NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.courses OWNER TO ghibli_adm;

--
-- Name: courses_course_id_seq; Type: SEQUENCE; Schema: public; Owner: ghibli_adm
--

ALTER TABLE public.courses ALTER COLUMN course_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.courses_course_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: customers; Type: TABLE; Schema: public; Owner: ghibli_adm
--

CREATE TABLE public.customers (
    customer_id bigint NOT NULL,
    name text NOT NULL,
    last_name text NOT NULL,
    email text NOT NULL,
    phone text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    password text,
    password_hash character varying(255)
);


ALTER TABLE public.customers OWNER TO ghibli_adm;

--
-- Name: customers_customer_id_seq; Type: SEQUENCE; Schema: public; Owner: ghibli_adm
--

ALTER TABLE public.customers ALTER COLUMN customer_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.customers_customer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (admin_id);


--
-- Name: booking_modules booking_modules_pkey; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.booking_modules
    ADD CONSTRAINT booking_modules_pkey PRIMARY KEY (booking_id, module_id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (booking_id);


--
-- Name: course_modules course_modules_pkey; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.course_modules
    ADD CONSTRAINT course_modules_pkey PRIMARY KEY (module_id);


--
-- Name: courses courses_course_name_key; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_course_name_key UNIQUE (course_name);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (course_id);


--
-- Name: customers customers_email_key; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_email_key UNIQUE (email);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (customer_id);


--
-- Name: booking_modules fk_booking_modules_booking; Type: FK CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.booking_modules
    ADD CONSTRAINT fk_booking_modules_booking FOREIGN KEY (booking_id) REFERENCES public.bookings(booking_id);


--
-- Name: booking_modules fk_booking_modules_module; Type: FK CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.booking_modules
    ADD CONSTRAINT fk_booking_modules_module FOREIGN KEY (module_id) REFERENCES public.course_modules(module_id);


--
-- Name: bookings fk_bookings_course; Type: FK CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT fk_bookings_course FOREIGN KEY (course_id) REFERENCES public.courses(course_id);


--
-- Name: bookings fk_bookings_customer; Type: FK CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT fk_bookings_customer FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id);


--
-- Name: course_modules fk_course_modules_course; Type: FK CONSTRAINT; Schema: public; Owner: ghibli_adm
--

ALTER TABLE ONLY public.course_modules
    ADD CONSTRAINT fk_course_modules_course FOREIGN KEY (course_id) REFERENCES public.courses(course_id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO ghibli_adm;


--
-- PostgreSQL database dump complete
--

\unrestrict 0dCE7iiJQzvDfsSqDHppEXpK2lcM5sovrOY2WfWo2WXFH9qXdkqKMZkntX0kyhn

