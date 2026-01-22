import sys
import argparse
from simai_search.indexer import Indexer
from simai_search.search import RhythmSearcher

# Hardcoded paths for now, relative to project root
DB_PATH = "maichart.db"
DATA_ROOT = "data/Maichart-Converts"

def cmd_build(args):
    print("Building index...")
    indexer = Indexer(DB_PATH, DATA_ROOT)
    indexer.run()

def cmd_search(args):
    query = args.query
    print(f"Searching for pattern: {query}")
    searcher = RhythmSearcher(DB_PATH)
    results = searcher.search(query)
    
    print(f"Found {len(results)} matches:")
    for title, diff, level, _ in results:
        print(f"[{diff} {level}] {title}")

def main():
    parser = argparse.ArgumentParser(description="Simai Chart Search")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    parser_build = subparsers.add_parser("build", help="Build the database index")
    
    parser_search = subparsers.add_parser("search", help="Search for a rhythm pattern")
    parser_search.add_argument("query", type=str, help="Simai rhythm string (e.g. {4}1,1,)")
    
    args = parser.parse_args()
    
    if args.command == "build":
        cmd_build(args)
    elif args.command == "search":
        cmd_search(args)

if __name__ == "__main__":
    main()
