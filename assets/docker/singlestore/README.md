# SingleStoreDB

## Prereqs

Per the [SingleStoreDB docker image](https://github.com/singlestore-labs/singlestoredb-dev-image),
running this image on Apple Silicon only works on macOS Tahoe (and up, presumably).

## Usage

Start the container:

```sh
docker compose up -d
```

This spins up two services:

1. **singlestore-db** — the SingleStoreDB instance (ports 3306 for SQL, 8080 for Studio UI)
2. **load-db** — creates the `test_ci` database, then exits. If the database already exists, it noops. This is normal.

You can override the root password via the `SINGLESTORE_ROOT_PASSWORD` env var (default: `test_superuser`).

## Running tests

```sh
pytest --singlestore
```

## Connecting manually

```sh
singlestore -h 127.0.0.1 -u root -p test_superuser
```

Or open the Studio UI at [http://localhost:8080](http://localhost:8080).
