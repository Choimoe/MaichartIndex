from typing import List, Tuple, Dict, Optional
import json
import re
from .db import SimaiDB
from .parser import SimaiParser
from bisect import bisect_left

class RhythmSearcher:
    def __init__(self, db_path: str):
        self.db = SimaiDB(db_path)
        self.parser = SimaiParser()
        self.chart_cache = None

    def _ensure_cache(self):
        """Lazy load charts into memory (Metadata + Events only, NO raw content)."""
        if self.chart_cache is not None:
            return

        print("Loading charts into memory...")
        # Fetch light-weight data from DB
        raw_rows = self.db.get_search_cache_data()
        
        cache = []
        for chart_id, song_title, difficulty, level, note_data_json, designer in raw_rows:
            try:
                # Pre-parse event data
                events_list = json.loads(note_data_json)
                
                # OPTIMIZATION: Convert dicts to tuples to save memory
                # Tuple structure: (time, bpm, is_star, resolution, src_start, src_end)
                events_tuple = []
                for e in events_list:
                    # resolution might be missing in older dbs? valid default is 4
                    # src_start/end might be missing?
                    events_tuple.append((
                        e.get('time', 0.0),
                        e.get('bpm', 0.0),
                        1 if e.get('is_star', False) else 0,
                        e.get('resolution', 4.0),
                        e.get('src_start', 0),
                        e.get('src_end', 0)
                    ))

                # Pre-calculate numeric level for faster filtering
                numeric_level = 0.0
                try:
                    if '+' in level:
                        base = float(level.replace('+', ''))
                        numeric_level = base + 0.6 
                    else:
                        numeric_level = float(level)
                except ValueError:
                    pass

                cache.append({
                    'id': chart_id,
                    'title': song_title,
                    'difficulty': difficulty,
                    'level_str': level,
                    'level_num': numeric_level,
                    'events': events_tuple, # Stored as tuples
                    # 'raw_content': raw_content, # EXCLUDED to save RAM
                    'designer': designer or ""
                })
            except Exception as e:
                print(f"Skipping chart {chart_id} due to error: {e}")
                continue
        
        self.chart_cache = cache
        print(f"Loaded {len(self.chart_cache)} charts.")

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
        Searches for a rhythm pattern using in-memory cache.
        Returns: (SongTitle, Difficulty, Level, ID, Snippet, MatchDegree)
        """
        self._ensure_cache()
        
        # Parse query to rhythm events
        query_events = self.parser.parse_chart_to_rhythm(query_simai)
        
        if not query_events:
            return []
            
        # Normalize query: relative to first note
        start_time = query_events[0]['time']
        for q in query_events:
            q['delta'] = q['time'] - start_time
        
        results = []
        
        # In-memory filtering and matching
        for chart in self.chart_cache:
            # 1. Filter Check
            if level_min is not None and chart['level_num'] < level_min:
                continue
            if level_max is not None and chart['level_num'] > level_max:
                continue
            if difficulties and chart['difficulty'] not in difficulties:
                continue
            if designer and designer.lower() not in chart['designer'].lower():
                continue
                
            # 2. Pattern Match
            try:
                # chart['events'] is now List[Tuple]
                match_result = self._match_pattern(chart['events'], query_events, tolerance, bpm_min, bpm_max)
                if match_result:
                     match_indices, degree = match_result
                     
                     # Check if it beats existing results or just append? 
                     # We need to fetch raw content NOW to slice snippet
                     
                     # Fetch raw content on-demand
                     raw_content = self.db.get_chart_raw_data(chart['id'])
                     if raw_content is None:
                         continue

                     # start_evt and end_evt are Tuples now
                     start_evt = chart['events'][match_indices[0]]
                     end_evt = chart['events'][match_indices[1]]
                     
                     # Re-clean raw content to extract snippet
                     lines = [re.sub(r'//.*', '', line) for line in raw_content.splitlines()]
                     cleaned_text = ''.join(lines).replace(' ', '').replace('\t', '')
                     
                     # tuple index 4 is src_start, 5 is src_end
                     raw_snippet = cleaned_text[start_evt[4] : end_evt[5]]
                     
                     # Prepend resolution
                     if not re.match(r'^\{[\d\.]+\}', raw_snippet):
                        res = start_evt[3] # Index 3 is resolution
                        # Handle float vs int formatting
                        if isinstance(res, (int, float)) and int(res) == res:
                            res_str = str(int(res))
                        else:
                            res_str = str(res)
                        snippet = f"{{{res_str}}}{raw_snippet}"
                     else:
                        snippet = raw_snippet
                     
                     # Map difficulty number to name
                     diff_names = {1: "Easy", 2: "Basic", 3: "Advanced", 4: "Expert", 5: "Master", 6: "ReMaster"}
                     diff_name = diff_names.get(chart['difficulty'], str(chart['difficulty']))
                     
                     results.append((chart['title'], diff_name, chart['level_str'], chart['id'], snippet, degree))
                     
            except Exception:
                continue
        
        # Sort by degree (descending)
        results.sort(key=lambda x: x[5], reverse=True)
                
        return results

    def _match_pattern(self, 
                       chart_events: List[Tuple], # Changed to List[Tuple]
                       query_events: List[Dict], 
                       tolerance: float,
                       bpm_min: Optional[float] = None,
                       bpm_max: Optional[float] = None) -> Optional[Tuple[Tuple[int, int], float]]:
        """
        Matches query pattern against chart events.
        chart_events: List of (time, bpm, is_star, resolution, src_start, src_end)
        Returns: ((start_idx, end_idx), match_degree) or None
        """
        if not chart_events or not query_events:
            return None
            
        n_chart = len(chart_events)
        n_query = len(query_events)
        
        # Pre-extract chart times for binary search
        # chart_events[i][0] is time
        # DEBUG
        if len(chart_events) > 0 and isinstance(chart_events[0], dict):
             print(f"ERROR: Chart events are still dicts! Type: {type(chart_events[0])}")
        
        chart_times = [e[0] for e in chart_events]
        
        best_match = None # ((start, end), degree)
        best_degree = -1.0
        
        # Iterate through possible start points in the chart
        for i in range(n_chart):
            # Optimization: If remaining notes < query length, impossible to full match (simple heuristic)
            if i + n_query > n_chart:
                break

            # 1. BPM Check (if strict range)
            current_bpm = chart_events[i][1]
            if bpm_min and current_bpm < bpm_min:
                continue
            if bpm_max and current_bpm > bpm_max:
                continue
                
            # 2. Star Check (First note)
            if query_events[0]['is_star'] and not chart_events[i][2]:
                continue
                
            # 3. Sequence Match
            start_time = chart_events[i][0]
            current_match_count = 0
            
            # Start index in chart for subsequence
            curr_chart_idx = i
            
            possible_match = True
            
            for j in range(n_query):
                target_delta = query_events[j]['delta']
                target_time = start_time + target_delta
                
                required_is_star = query_events[j]['is_star']
                
                # Find event in chart closest to target_time
                idx = bisect_left(chart_times, target_time - tolerance, lo=curr_chart_idx, hi=n_chart)
                
                found_note = False
                for k in range(idx, min(idx + 5, n_chart)):
                    t = chart_times[k]
                    if abs(t - target_time) <= tolerance:
                        if required_is_star and not chart_events[k][2]:
                            continue 
                        if bpm_min and chart_events[k][1] < bpm_min:
                             continue
                        if bpm_max and chart_events[k][1] > bpm_max:
                             continue
                        
                        found_note = True
                        curr_chart_idx = k + 1 
                        current_match_count += 1
                        break
                    if t > target_time + tolerance:
                        break 
                
                if not found_note:
                    possible_match = False
                    break
            
            if possible_match:
                match_end_idx = curr_chart_idx - 1
                chart_segment_len = match_end_idx - i + 1
                degree = n_query / chart_segment_len if chart_segment_len > 0 else 0
                
                if degree > best_degree:
                    best_degree = degree
                    best_match = ((i, match_end_idx), degree)
                    
                if degree >= 1.0:
                    return best_match
                
        return best_match
