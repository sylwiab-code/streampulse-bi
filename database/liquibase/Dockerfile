# Liquibase with the Snowflake JDBC driver (ADR-003). Built and run by run.py.
FROM liquibase/liquibase:5.0.4@sha256:060f96efff4811ccf03957ff3160f21ea04139b89940640f8ad54a065cdc6906

ADD --checksum=sha256:cb225d78ac10336669797dfef8588cffb7e3dae689f14120935831b1f6ba2709 \
    https://repo1.maven.org/maven2/net/snowflake/snowflake-jdbc/4.4.1/snowflake-jdbc-4.4.1.jar \
    /liquibase/lib/snowflake-jdbc-4.4.1.jar
