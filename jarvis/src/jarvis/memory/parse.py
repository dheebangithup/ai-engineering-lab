from unstructured.partition.md import partition_md
from pathlib import Path
from unstructured.chunking.title import chunk_by_title

filename = Path(__file__).parent / "runbook.md"
elements = partition_md(filename=filename)
chunks = chunk_by_title(elements)

for chunk in chunks:
    print(chunk.text)
    print("\n\n" + "-"*80)
    input()
