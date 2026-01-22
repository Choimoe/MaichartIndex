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
    if args.level_min: print(f"Min Level: {args.level_min}")
    if args.level_max: print(f"Max Level: {args.level_max}")
    if args.diff: print(f"Difficulties: {args.diff}")
    if args.designer: print(f"Designer: {args.designer}")
    if args.bpm_min or args.bpm_max: print(f"BPM Range: {args.bpm_min} - {args.bpm_max}")

    # Map difficulty strings to ints
    diff_map = {"easy": 1, "basic": 2, "advanced": 3, "expert": 4, "master": 5, "remaster": 6}
    diff_ids = None
    if args.diff:
        diff_ids = []
        for d in args.diff:
            d_lower = d.lower()
            if d_lower in diff_map:
                diff_ids.append(diff_map[d_lower])
    
    searcher = RhythmSearcher(DB_PATH)
    results = searcher.search(
        query, 
        level_min=args.level_min,
        level_max=args.level_max,
        difficulties=diff_ids,
        designer=args.designer,
        bpm_min=args.bpm_min,
        bpm_max=args.bpm_max
    )
    
    print(f"Found {len(results)} matches:")
    print(f"Found {len(results)} matches:")
    for title, diff, level, _, snippet, degree in results:
        print(f"[{diff} {level}] {title} (Match: {degree:.0%})")
        print(f"    Match: {snippet}")

        print(f"    Match: {snippet}")

def cmd_serve(args):
    import uvicorn
    import server
    
    port = args.port
    if port is None or port == 0:
        # Use random port from server.py logic
        port = server.get_random_port()
        if port == 0:
            print("Error: Could not find an available port.")
            return

    print(f"Starting server at http://{args.host}:{port}")
    # We pass the app object directly
    uvicorn.run(server.app, host=args.host, port=port)

def main():
    parser = argparse.ArgumentParser(description="Simai Chart Search")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    parser_build = subparsers.add_parser("build", help="Build the database index")
    
    parser_search = subparsers.add_parser("search", help="Search for a rhythm pattern")
    parser_search.add_argument("query", type=str, help="Simai rhythm string (e.g. {4}1,1,)")
    parser_search.add_argument("--level-min", type=float, help="Minimum level (e.g. 12.0)")
    parser_search.add_argument("--level-max", type=float, help="Maximum level (e.g. 14.9)")
    parser_search.add_argument("--diff", nargs="+", help="Difficulties (Easy, Basic, Advanced, Expert, Master, ReMaster)")
    parser_search.add_argument("--designer", type=str, help="Chart designer name (partial match)")
    parser_search.add_argument("--bpm-min", type=float, help="Minimum BPM for the pattern")
    parser_search.add_argument("--bpm-max", type=float, help="Maximum BPM for the pattern")
    
    parser_serve = subparsers.add_parser("serve", help="Run the web server")
    parser_serve.add_argument("--port", type=int, default=0, help="Port to run server on (0 for random)")
    parser_serve.add_argument("--host", type=str, default="0.0.0.0", help="Host interface")
    
    args = parser.parse_args()
    
    if args.command == "build":
        cmd_build(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "serve":
        cmd_serve(args)

if __name__ == "__main__":
    main()
