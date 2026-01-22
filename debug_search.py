from simai_search.search import RhythmSearcher
from simai_search.parser import SimaiParser
import json

def debug_search():
    db_path = "maichart.db"
    searcher = RhythmSearcher(db_path)
    
    query = "{8}1*,1,1,," # The one user tried last? Or the one that returned 0?
    # User tried "{8}1*,1,1,,1*,1,1," first (found 0).
    # Then "{8}1*,1,1,," (found 0).
    
    query1 = "{8}1*,1,1,,1*,1,1,"
    print(f"Query: {query1}")
    
    parser = SimaiParser()
    q_events = parser.parse_chart_to_rhythm(query1)
    print("Query Events:")
    for e in q_events:
        print(e)
        
    print("\nRunning Search...")
    # Add print inside search logic? No, just call it.
    results = searcher.search(query1, bpm_min=190, bpm_max=200)
    print(f"Results: {len(results)}")
    
    if len(results) == 0:
        # manual inspect one chart
        charts = searcher.db.get_charts(level_min=13.0)
        found_target = False
        
        # Normalize query manually for _match_pattern check
        start_time = q_events[0]['time']
        for q in q_events:
            q['delta'] = q['time'] - start_time

        for c in charts:
             chart_id, song_title = c[0], c[1]
             if "Axeria" in song_title:
                 print(f"Checking Axeria chart {chart_id}...")
                 note_data = json.loads(c[4])
                 if not note_data:
                     print("Empty note data!")
                     continue
                 
                 # Print first few notes to check BPM and keys
                 print(f"Note Data sample: {note_data[:3]}")
                 
                 match = searcher._match_pattern(note_data, q_events, tolerance=0.01, bpm_min=190, bpm_max=200)
                 print(f"Match result: {match}")
                 break

if __name__ == "__main__":
    debug_search()
