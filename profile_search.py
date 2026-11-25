from findex.store import load; from findex.ranking import search; index = load("index.bin"); [search(index, "python asyncio search") for _ in range(3000)]
