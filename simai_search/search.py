from typing import List, Tuple, Dict, Optional
import json
import re
from .db import SimaiDB
from .parser import SimaiParser

class RhythmSearcher:
    def __init__(self, db_path: str):
        self.db = SimaiDB(db_path)
        self.parser = SimaiParser()

    def search(self, 
               query_simai: str, 
               tolerance: float = 0.01,
               level_min: float = None,
               level_max: float = None,
               difficulties: List[int] = None,
               designer: str = None,
               bpm_min: float = None,
               bpm_max: float = None) -> List[Tuple[str, str, str, str, str]]:
        """
        Searches for a rhythm pattern with optional filters.
        Returns: (SongTitle, Difficulty, Level, ID, Snippet)
        """
        # Parse query to rhythm events
        query_events = self.parser.parse_chart_to_rhythm(query_simai)
        
        if not query_events:
            return []
            
        # Normalize query: relative to first note
        # query_events is now List[Dict]
        start_time = query_events[0]['time']
        
        # We store relative time in the query dicts for easier matching
        for q in query_events:
            q['delta'] = q['time'] - start_time
        
        results = []
        
                
                # Fetch charts matching criteria
        filtered_charts = self.db.get_charts(
            level_min=level_min,
            level_max=level_max,
            difficulties=difficulties,
            designer=designer
        )
        
        for chart_id, song_title, difficulty, level, note_data_json, raw_content, designer in filtered_charts:
            try:
                chart_events = json.loads(note_data_json)
                
                # chart_events is list of dicts: {'time', 'bpm', 'is_star', 'src_start', 'src_end'}
                
                match_result = self._match_pattern(chart_events, query_events, tolerance, bpm_min, bpm_max)
                if match_result:
                     match_indices, degree = match_result
                     # Reconstruct snippet
                     # match_indices is (start_event_idx, end_event_idx)
                     # Snip from chart_events[start].start to chart_events[end].end
                     start_evt = chart_events[match_indices[0]]
                     end_evt = chart_events[match_indices[1]]
                     
                     # We need the "cleaned" text to use these indices?
                     # The indices in `parser.py` are based on the *cleaned* text.
                     # `raw_content` in DB is the *original* text (with comments/newlines).
                     # IMPORTANT: We need to re-clean the raw_content to match the indices.
                     # Or `parser.py` logic implies we need the cleaned text.
                     
                     # Re-clean raw content
                     lines = [re.sub(r'//.*', '', line) for line in raw_content.splitlines()]
                     cleaned_text = ''.join(lines).replace(' ', '').replace('\t', '')
                     
                     raw_snippet = cleaned_text[start_evt.get('src_start', 0) : end_evt.get('src_end', 0)]
                     
                     # Prepend resolution if not already present at start
                     # Check if raw_snippet starts with {number}
                     if not re.match(r'^\{[\d\.]+\}', raw_snippet):
                        # Resolution is stored in start_evt['resolution'] (float)
                        # Convert to int if whole number
                        res = start_evt.get('resolution', 4)
                        if res.is_integer():
                            res_str = str(int(res))
                        else:
                            res_str = str(res)
                            
                        snippet = f"{{{res_str}}}{raw_snippet}"
                     else:
                        snippet = raw_snippet
                     
                     # Map difficulty number to name
                     diff_names = {1: "Easy", 2: "Basic", 3: "Advanced", 4: "Expert", 5: "Master", 6: "ReMaster"}
                     diff_name = diff_names.get(difficulty, str(difficulty))
                     results.append((song_title, diff_name, level, chart_id, snippet, degree))
            except Exception as e:
                # print(f"Error searching chart {chart_id}: {e}")
                continue
        
        # Sort by degree (descending)
        results.sort(key=lambda x: x[5], reverse=True)
                
        return results

    def _match_pattern(self, chart_events: List[dict], query_events: List[dict], tolerance: float, bpm_min: float = None, bpm_max: float = None) -> Optional[Tuple[Tuple[int, int], float]]:
        """
        Checks if query sequence exists in chart_events.
        Returns ((start_idx, end_idx), match_degree) of the BEST match in chart_events, or None.
        """
        n_query = len(query_events)
        n_chart = len(chart_events)
        
        if n_query > n_chart:
            return None
            
        best_match = None
        best_degree = -1.0

        for i in range(n_chart):
            # Optimization: If remaining events are fewer than query, stop
            if n_chart - i < n_query:
                break
                
            start_event = chart_events[i]
            base_time = start_event['time']
            
            # Check Start Event Constraints
            if bpm_min is not None and start_event['bpm'] < bpm_min:
                continue
            if bpm_max is not None and start_event['bpm'] > bpm_max:
                continue
            if query_events[0]['is_star'] and not start_event['is_star']:
                continue
            
            match = True
            
            current_chart_idx = i
            last_match_idx = i
            
            for k in range(1, n_query):
                q_evt = query_events[k]
                target_time = base_time + q_evt['delta']
                
                found_k = False
                
                while current_chart_idx < n_chart:
                    c_evt = chart_events[current_chart_idx]
                    t_diff = c_evt['time'] - target_time
                    
                    if t_diff < -tolerance:
                        current_chart_idx += 1
                        continue
                    elif t_diff > tolerance:
                        break
                    else:
                        valid_note = True
                        if bpm_min is not None and c_evt['bpm'] < bpm_min:
                            valid_note = False
                        if bpm_max is not None and c_evt['bpm'] > bpm_max:
                            valid_note = False
                        if q_evt['is_star'] and not c_evt['is_star']:
                            valid_note = False
                            
                        if valid_note:
                            found_k = True
                            last_match_idx = current_chart_idx
                            current_chart_idx += 1 
                            break 
                        
                        current_chart_idx += 1
                
                if not found_k:
                    match = False
                    break
            
            if match:
                # Calculate degree
                # Range is [i, last_match_idx] (inclusive)
                chart_notes_count = last_match_idx - i + 1
                degree = n_query / chart_notes_count
                
                if degree > best_degree:
                    best_degree = degree
                    best_match = (i, last_match_idx)
                
                # Optimization: If we found a 100% match, we can just return it immediately if we don't care about finding ALL?
                # Actually, the user might want a specific region, but for "Best Match found in chart", 1.0 is max.
                # However, there might be multiple 1.0 matches, does it matter which one?
                # Let's say we just keep looking to be safe or break on 1.0. 
                if degree >= 1.0:
                    return ((i, last_match_idx), degree)

        if best_match:
            return (best_match, best_degree)
                
        return None
