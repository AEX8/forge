import os

# Tests use their own database and Redis db so pytest does not drop
# the tables the local stack is using. This must run before anything
# imports app.core.config, which is why it lives at the top of conftest.
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://forge:forge@localhost:5432/forge_test"
)
os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

# The fixtures call drop_all, so refuse to run against anything that is not a test db
assert os.environ["DATABASE_URL"].endswith("_test"), "tests must use a *_test database"