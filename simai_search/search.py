from typing import List, Tuple
import json
from .db import SimaiDB
from .parser import SimaiParser

class RhythmSearcher:
    def __init__(self, db_path: str):
        self.db = SimaiDB(db_path)
        self.parser = SimaiParser()

    def search(self, query_simai: str, tolerance: float = 0.01) -> List[Tuple[str, str, str, str]]:
        """
        Searches for a rhythm pattern.
        query_simai: Simai formatted string, e.g. "{4}1,1,2,"
        Returns list of (SongTitle, Difficulty, Level, Designer)
        """
        # Parse query to rhythm events
        # We need to act as if the query is a chart to extract relative timing
        # We can wrap it in a dummy chart
        query_events = self.parser.parse_chart_to_rhythm(query_simai)
        
        if not query_events:
            return []
            
        # Normalize query: relative to first note
        start_time = query_events[0]
        query_deltas = [t - start_time for t in query_events]
        query_len = len(query_deltas)
        
        results = []
        
        # Fetch all charts
        # Optimization: In a real large DB, we wouldn't fetch all. 
        # But for hundreds of text files, it's fine.
        all_charts = self.db.get_all_charts()
        
        for chart_id, song_title, difficulty, level, note_data_json, raw_content in all_charts:
            try:
                chart_events = json.loads(note_data_json)
                
                if self._match_pattern(chart_events, query_deltas, tolerance):
                     # Map difficulty number to name
                     diff_names = {1: "Easy", 2: "Basic", 3: "Advanced", 4: "Expert", 5: "Master", 6: "ReMaster"}
                     diff_name = diff_names.get(difficulty, str(difficulty))
                     results.append((song_title, diff_name, level, chart_id))
            except Exception as e:
                print(f"Error searching chart {chart_id}: {e}")
                continue
                
        return results

    def _match_pattern(self, chart_events: List[float], query_deltas: List[float], tolerance: float) -> bool:
        """
        Checks if query_deltas sequence exists in chart_events.
        """
        if len(query_deltas) > len(chart_events):
            return False
            
        # Brute force sliding window
        # Optimized: Only check starting positions where chart_events[i] is a valid start
        # Since query_deltas[0] is 0, we treat every note in chart as a candidate start.
        
        # We can be smarter: 
        # For each note C in chart:
        #   Check if C + query_deltas[1] exists in chart (within tolerance)
        #   Check if C + query_deltas[2] exists...
        # This is O(N*M) where N is chart events, M is query length.
        # Since chart events are sorted, we can use binary search or two pointers.
        # Given M is small (pattern usually short), binary search is good.
        
        # Let's use bisect for existence check
        import bisect
        
        n_events = len(chart_events)
        
        for i in range(n_events):
            # Optimization: If remaining events are fewer than query, stop
            if n_events - i < len(query_deltas):
                break
                
            start_t = chart_events[i]
            match = True
            
            # Check subsequence
            for k in range(1, len(query_deltas)):
                target_t = start_t + query_deltas[k]
                
                # Check if target_t exists in chart_events (within tolerance)
                # Bisect left to find insertion point
                idx = bisect.bisect_left(chart_events, target_t - tolerance, lo=i)
                
                # Check if we found a candidate
                if idx < n_events and abs(chart_events[idx] - target_t) <= tolerance:
                    # Found match for this note
                    pass
                else:
                    # Try next element just in case of slight overlap? 
                    # bisect_left gives first element >= target - tol.
                    # so chart_events[idx] >= target - tol.
                    # We checked condition: chart_events[idx] - target <= tol (implicit if we check abs)
                    # Wait, abs(val - target) <= tol <=> -tol <= val - target <= tol
                    # <=> target - tol <= val <= target + tol.
                    # bisect_left finds first val >= target - tol.
                    # We just need to check if that val is also <= target + tol.
                    if idx < n_events and chart_events[idx] <= target_t + tolerance:
                        pass
                        # Note: we don't strictly require sequential indices in chart, just existence.
                        # The query {16}1,1 means "Two notes separated by 1/16". 
                        # If the chart has "Note, Note, Note" at 0, 0.25, 0.5.
                        # Query matches at 0 (0, 0.25 matched).
                        # Matches at 0.25 (0.25, 0.5 matched).
                        # Correct.
                    else:
                        match = False
                        break
            
            if match:
                return True
                
        return False
