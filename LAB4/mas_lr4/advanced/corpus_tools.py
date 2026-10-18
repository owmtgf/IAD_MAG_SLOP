"""Public-only bounded literal corpus access for M04; never loads the oracle."""
import argparse
import json
from pathlib import Path


class Corpus:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.manifest = json.loads((self.folder / "manifest.json").read_text())
        self.paths = {f"shard_{i:02d}": self.folder / f"shard_{i:02d}.jsonl" for i in range(1, 5)}
        self.lines = {name: path.read_text(encoding="utf-8").splitlines() for name, path in self.paths.items()}

    def read_corpus(self, shard, start_line=1, max_lines=100):
        if shard not in self.lines or type(start_line) is not int or type(max_lines) is not int or not 1 <= max_lines <= 1000 or start_line < 1:
            raise ValueError("Known shard, start_line>=1 and max_lines in 1..1000 required")
        lines = self.lines[shard]
        if start_line > len(lines) + 1:
            raise ValueError("start_line is beyond EOF")
        selected = lines[start_line - 1:start_line - 1 + max_lines]
        return {"shard": shard, "start_line": start_line, "end_line": start_line + len(selected) - 1,
                "total_lines": len(lines), "has_more": start_line - 1 + len(selected) < len(lines),
                "records": [json.loads(line) for line in selected]}

    def search_corpus(self, query, shard=None, offset=0, limit=100):
        if not isinstance(query, str) or not 1 <= len(query) <= 500 or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Literal query 1..500 chars; offset>=0; limit 1..1000")
        if shard is not None and shard not in self.lines:
            raise ValueError("Unknown shard")
        matches = [{"shard": name, "line": number, "record": json.loads(line)}
                   for name in sorted(self.lines) if shard is None or shard == name
                   for number, line in enumerate(self.lines[name], 1) if query in line]
        selected = matches[offset:offset + limit]
        return {"query": query, "offset": offset, "total_matches": len(matches),
                "has_more": offset + len(selected) < len(matches), "matches": selected}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("read", "search"))
    parser.add_argument("--corpus", default=str(Path(__file__).resolve().parent / "tasks" / "M04" / "corpus"))
    parser.add_argument("--shard")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--query")
    args = parser.parse_args()
    corpus = Corpus(args.corpus)
    result = corpus.read_corpus(args.shard, args.start, args.limit) if args.command == "read" else corpus.search_corpus(args.query, args.shard, args.offset, args.limit)
    print(json.dumps(result, ensure_ascii=False))
