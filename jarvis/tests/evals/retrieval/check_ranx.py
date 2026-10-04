import ranx


def main() -> None:
    print("ranx import: OK")

    print("\nQrels:", ranx.Qrels)
    print("Run:", ranx.Run)
    print("evaluate:", ranx.evaluate)

    print("\nRequired retrieval API: OK")


if __name__ == "__main__":
    main()