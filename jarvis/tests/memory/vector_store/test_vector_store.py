from jarvis.memory.vector_store import (
    VectorStoreFactory,
    VectorStoreType,
)
from jarvis.workspace import default_workspace


def main():
    workspace = default_workspace()
    workspace.initialize()

    store = VectorStoreFactory.create(
        VectorStoreType.QDRANT,
        workspace=workspace,
        collection_name="memories",
        vector_size=1024,
    )

    print("Workspace:")
    print(workspace.root)

    print()
    print("Qdrant path:")
    print(workspace.qdrant_dir)

    print()
    print("Vector store:")
    print(type(store))


if __name__ == "__main__":
    main()