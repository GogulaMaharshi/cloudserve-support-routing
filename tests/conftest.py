import os

os.environ.setdefault("RETRIEVAL_BACKEND", "lexical")
os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/test_decisions.db")
