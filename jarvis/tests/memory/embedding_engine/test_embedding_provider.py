from jarvis.memory.embedding_engine import (
    EmbeddingProvider,
)



def main():

    provider = EmbeddingProvider()

    text = (
        "Payment API connection pool "
        "was exhausted during peak traffic."
    )

    embedding = provider.embed(text)

    print()
    print("Embedding successful!")
    print("--------------------")
    print("Dimensions:", len(embedding))
    print("First 10 values:")
    print(embedding[:10])


if __name__ == "__main__":
    main()