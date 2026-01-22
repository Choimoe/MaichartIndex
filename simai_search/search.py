from typing import List, Tuple, Dict, Optional
import json
import re
from .db import SimaiDB
from .parser import SimaiParser

class RhythmSearcher:
    def __init__(self, db_path: str):
        self.db = SimaiDB(db_path)
        self.parser = SimaiParser()
        self.chart_cache = None

    def _ensure_cache(self):
        """Lazy load all charts into memory and pre-parse JSON."""
        if self.chart_cache is not None:
            return

        print("Loading charts into memory...")
        # Fetch ALL charts from DB
        raw_rows = self.db.get_charts()
        
        cache = []
        for chart_id, song_title, difficulty, level, note_data_json, raw_content, designer in raw_rows:
            try:
                # Pre-parse event data
                events = json.loads(note_data_json)
                
                # Pre-calculate numeric level for faster filtering
                # Simai levels: "13", "13+", "12.5"
                # If it's "13+", treated as 13.7 (approx) or just let's try to parse
                numeric_level = 0.0
                try:
                    if '+' in level:
                        base = float(level.replace('+', ''))
                        numeric_level = base + 0.5 # Standard mapping usually + is .7 but let's say .5 for sorting/range? 
                        # Actually standard convention: 13+ is 13.7-13.9. 
                        # But user inputs 13.5. 
                        # Let's just use simple parsing:
                        numeric_level = base + 0.6 # slightly more than .5
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
                    'events': events,
                    'raw_content': raw_content,
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
                match_result = self._match_pattern(chart['events'], query_events, tolerance, bpm_min, bpm_max)
                if match_result:
                     match_indices, degree = match_result
                     
                     start_evt = chart['events'][match_indices[0]]
                     end_evt = chart['events'][match_indices[1]]
                     
                     # Re-clean raw content to extract snippet
                     lines = [re.sub(r'//.*', '', line) for line in chart['raw_content'].splitlines()]
                     cleaned_text = ''.join(lines).replace(' ', '').replace('\t', '')
                     
                     raw_snippet = cleaned_text[start_evt.get('src_start', 0) : end_evt.get('src_end', 0)]
                     
                     # Prepend resolution
                     if not re.match(r'^\{[\d\.]+\}', raw_snippet):
                        res = start_evt.get('resolution', 4)
                        if isinstance(res, (int, float)) and hasattr(res, 'is_integer') and res.is_integer():
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
