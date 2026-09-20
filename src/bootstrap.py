"""Train the classifier and index the knowledge base.

    python -m src.bootstrap
"""

from __future__ import annotations

from src.classify import train_classifier
from src.retrieve import get_retriever


def main() -> None:
    path = train_classifier()
    print(f"classifier written to {path}")
    n = get_retriever().build()
    print(f"indexed {n} passages")


if __name__ == "__main__":
    main()
