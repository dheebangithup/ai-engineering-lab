from jarvis.memory.vector_store.qdrant import QdrantVectorStore


def main():
    store = QdrantVectorStore()

    print("Qdrant vector store initialized.")
    print("Workspace:", store.workspace.root)
    print("Qdrant path:", store.workspace.qdrant_dir)
    print("Collection:", store.collection_name)


if __name__ == "__main__":
    main()