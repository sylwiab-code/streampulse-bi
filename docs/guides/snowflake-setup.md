# Snowflake setup (DEV)

One-time steps to connect a developer machine to the Snowflake DEV environment ([ADR-003](../adr/003-snowflake-environments-and-liquibase-boundary.md)). You need a Snowflake account on **Enterprise** edition (masking policies), `ACCOUNTADMIN` access in Snowsight, Docker Desktop, and OpenSSL (included in Git for Windows).

## 1. Create a key pair

In Git Bash:

```bash
mkdir -p ~/.snowflake/keys
```

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -inform PEM -out ~/.snowflake/keys/svc_deployer_dev.p8
```

```bash
openssl rsa -in ~/.snowflake/keys/svc_deployer_dev.p8 -pubout -out ~/.snowflake/keys/svc_deployer_dev.pub
```

The `.p8` file is the private key: keep it in this folder, never copy it into the repository, and never paste it anywhere. Print the public key as one line for the next step:

```bash
grep -v "PUBLIC KEY" ~/.snowflake/keys/svc_deployer_dev.pub | tr -d '\n'; echo
```

## 2. Run the bootstrap script

1. In Snowsight, open a new SQL worksheet and switch to the `ACCOUNTADMIN` role.
2. Paste the contents of [`database/bootstrap/bootstrap_dev.sql`](../../database/bootstrap/bootstrap_dev.sql).
3. Replace `<DEPLOYER_DEV_PUBLIC_KEY>` with the one-line public key from step 1 (in the worksheet only; do not edit the file in the repository).
4. Run all statements.

It creates the resource monitor (25 credits per month), the `WH_DEPLOY` warehouse, the `STREAMPULSE_ADMIN.LIQUIBASE` schema, the `DEPLOYER_DEV` role, and the `SVC_DEPLOYER_DEV` service user.

## 3. Fill in `.env`

Copy `.env.example` to `.env` in the repository root and set:

```
SNOWFLAKE_ACCOUNT=<orgname>-<accountname>
SNOWFLAKE_USER=SVC_DEPLOYER_DEV
SNOWFLAKE_PRIVATE_KEY_PATH=~/.snowflake/keys/svc_deployer_dev.p8
```

The account identifier is shown in Snowsight under your account menu (Account > View account details), in the format `orgname-accountname`.

## 4. Build DEV, load data, verify

Start Docker Desktop, then from the repository root:

```bash
uv run python database/liquibase/run.py --env dev update-sql
```

```bash
uv run python database/liquibase/run.py --env dev update
```

```bash
uv run generate backfill
```

```bash
uv run load --env dev
```

```bash
STREAMPULSE_SNOWFLAKE_TESTS=1 uv run pytest loader/tests/test_snowflake_dev.py
```

`update-sql` previews the SQL without changing anything. `update` creates the DEV environment from zero; rerunning it applies only new changesets. The loader is idempotent: rerunning it loads only new files. The last command verifies masking per role and that every local file was loaded.

Daily batches: `uv run generate daily --days 1`, then `uv run load --env dev`.

## Notes

- TEST and PROD are created only by the CD workflow (Phase 7); the runner and the loader refuse them locally.
- Rollback the last changeset: `uv run python database/liquibase/run.py --env dev rollback-count 1`.
- Warehouses suspend after 60 seconds idle; the resource monitor suspends everything at 25 credits per month.
