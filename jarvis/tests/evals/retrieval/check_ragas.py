import inspect

import ragas
import ragas.metrics as metrics


def main() -> None:
    print("Ragas version:", ragas.__version__)

    print("\nRanking module:")
    print(metrics.ranking)

    print("\nAvailable ranking objects:")

    for name in dir(metrics.ranking):
        if name.startswith("_"):
            continue

        obj = getattr(metrics.ranking, name)

        if inspect.isclass(obj) or inspect.isfunction(obj):
            print(f"  - {name}")

    print("\nRankingMetric:")
    print(inspect.signature(metrics.RankingMetric))

    print("\nRankingMetric source:")
    print(inspect.getsource(metrics.RankingMetric))


if __name__ == "__main__":
    main()