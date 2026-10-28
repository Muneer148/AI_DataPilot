"""Run a small local demo of the deterministic AI_DataPilot agent MVP.

From the repository root: python -m examples.agent_mvp_demo
"""
import json

import pandas as pd

from src.agent import ask


def main() -> None:
    sales = pd.DataFrame({
        "region": ["East", "West", "East", "West"],
        "sales": [100, 80, 120, 200],
        "units": [2, 2, 3, 5],
    })
    questions = [
        "What is the total sales?",
        "What is the average sales by region?",
        "What is the correlation between sales and units?",
        "What is the total profit?",
    ]
    for question in questions:
        response = ask(sales, question)
        print(f"\nQUESTION: {question}")
        print(json.dumps(response.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
