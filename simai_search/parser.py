import re
from typing import List, Dict, Tuple

class SimaiParser:
    def __init__(self):
        pass

    def parse_maidata(self, content: str) -> Dict:
        """
        Parses full maidata.txt content.
        Returns dict with metadata and list of charts.
        """
        metadata = {}
        charts = {}
        
        lines = content.splitlines()
        current_chart_difficulty = None
        current_chart_content = []
        
        # Difficulty mapping keys in maidata
        # &inote_1=Easy, 2=Basic, 3=Advanced, 4=Expert, 5=Master, 6=ReMaster
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('&'):
                # Check for inote start
                inote_match = re.match(r'&inote_(\d)=', line)
                if inote_match:
                    # Save previous chart if exists
                    if current_chart_difficulty is not None:
                        charts[current_chart_difficulty] = '\n'.join(current_chart_content)
                    
                    current_chart_difficulty = int(inote_match.group(1))
                    current_chart_content = []
                    # Handle content on the same line after =
                    content_part = line.split('=', 1)[1]
                    if content_part:
                        current_chart_content.append(content_part)
                elif current_chart_difficulty is not None:
                    # Check if it's another tag which might end the chart (though usually inote is at the end block)
                    # But Simai files are messy. If we see another known tag, treat it as metadata
                    # However, tags like &des_1 might appear anywhere? 
                    # Usually tags are at top. &inote is definitely chart content. 
                    # If we see &title=..., it's metadata. 
                    # If we are inside a chart, lines starting with & might be part of metadata sect again?
                    # Generally inote sections are the last parts. 
                    # Let's assume & starts a metadata line unless we are in parsing.
                    # Actually Simai standard: &inote_X= starts the chart. 
                    # The chart ends when another & tag appears or file ends? 
                    # Or does it end at 'E'? Simai uses 'E' to end chart.
                    
                    # Let's collect metadata
                    key_val = line.split('=', 1)
                    if len(key_val) == 2:
                        key = key_val[0][1:]
                        val = key_val[1]
                        metadata[key] = val
                    
                    # If we hit a new tag while in chart mode, and it's NOT an inote tag, 
                    # it might be safest to just append it to chart if it doesn't look like valid metadata?
                    # But standard format separates them. 
                    # Let's stick to: if it starts with &, it is a tag.
                    if current_chart_content:
                         # If we were reading a chart, and found a tag (that is not inote), 
                         # we assume the chart ended.
                         if not inote_match:
                             # Wait, the logic above: inote_match logic handles switching charts.
                             # If it's a DIFFERENT tag, we also save the previous chart.
                             charts[current_chart_difficulty] = '\n'.join(current_chart_content)
                             current_chart_difficulty = None
                else:
                    # Normal metadata line
                    key_val = line.split('=', 1)
                    if len(key_val) == 2:
                        key = key_val[0][1:]
                        val = key_val[1]
                        metadata[key] = val

            else:
                # Content line
                if current_chart_difficulty is not None:
                    current_chart_content.append(line)

        # End of loop
        if current_chart_difficulty is not None:
            charts[current_chart_difficulty] = '\n'.join(current_chart_content)
            
        return {'metadata': metadata, 'charts': charts}

    def parse_chart_to_rhythm(self, chart_text: str) -> List[float]:
        """
        Converts Simai chart text to a list of beat offsets.
        Ignores actual note types, just cares about WHEN a note happens.
        
        Logic:
        - Track current resolution (default 4? or just 1?). Simai default is usually 4 (quarter note).
        - Scan tokens.
        - {X} -> resolution = X.
        - , -> time += 4/resolution.
        - Notes (digits, touch, etc) -> if not seen in this beat step yet, add time to list.
        - (bpm) -> ignore for rhythm grid.
        - E -> End.
        """
        
        # Clean text: remove comments
        # Simai comments: // 
        # But allow urls in metadata? chart_text shouldn't have URLs.
        # Just remove // to end of line
        lines = [re.sub(r'//.*', '', line) for line in chart_text.splitlines()]
        text = ''.join(lines).replace(' ', '').replace('\t', '')
        
        # Tokenizer regex
        # Tokens: 
        # {(\d+)} -> Resolution change
        # \((\d+(?:\.\d+)?)\) -> BPM change
        # , -> Break
        # [0-9]+ -> Tap/Hold start
        # [A-E][0-9]+ -> Touch
        # Various modifiers (h, x, b, s, /, *, f, <, >, ^, p, q, v, z, w) -> Ignore mostly, but / indicates simultaneous
        # But wait, Simai is structured as:
        # Note Note / Note Note , 
        # Notes between commas are simultaneous? 
        # No. `1/2,` means 1 and 2 are simultaneous, then wait.
        # `1` (wait) `2` (wait) is `1,2,`
        # `1` (no wait) `2` (wait) -> `12,` ?? No, Simai doesn't allow implicit sequence without commas usually.
        # Subdivisions: `12` is invalid unless `1` and `2` are simultaneous (written `1/2`).
        # Wait, if I write `12,` in Simai, is it 1 and 2 simultaneous? 
        # No, typical simai uses `/` for simultaneous notes at the same timing.
        # `1` by itself is a note.
        # `1,` is a note then a wait.
        # `1` followed immediately by `2` without separator? 
        # Simai.md says: `键号` ... 
        # Actually Simai is very loose. 
        # Usually: `{4}1,2,` -> Note 1, wait 1/4 bar. Note 2, wait 1/4 bar.
        # `{4}1/2,` -> Note 1 and 2 simultaneous, wait 1/4 bar.
        # What about `{4}1` (EOF)? Note 1. match.
        
        # NOTE: We want to capture the simplified event: "One or more notes happen at time T".
        
        current_time = 0.0
        resolution = 4.0 # Default to 4 (quarter notes)
        
        note_events = set() # Set of times where notes occur
        
        # We process the string linearly.
        # We need to distinguish between:
        # - Control tokens: {}, (), ,
        # - Note tokens: Anything else?
        # - Separator for simultaneous: /
        
        # Regex to find control tokens or commas
        # The rest are notes.
        
        # Pattern:
        # \{([\d\.]+)\}  -> Resolution
        # \(([\d\.]+)\)  -> BPM
        # \,             -> Step
        # [A-E0-9]+      -> Note basics (simplification)
        
        # We can iterate through the string.
        # But `1h[2:1]` is a note. `A1b` is a note.
        # We just need to know if there is a NOTE in the current buffer before the comma.
        
        i = 0
        length = len(text)
        
        has_note_in_current_step = False
        
        while i < length:
            char = text[i]
            
            if char == '{':
                # Find closing }
                end = text.find('}', i)
                if end != -1:
                    content = text[i+1:end]
                    # Check if it is a resolution change (just numbers/hashes)
                    # {4} or {4#2} -> 4 is resolution
                    # {#12.5} -> seconds? Ignore seconds-based for rhythm search if possible, 
                    # or better yet, if we want fuzzy grid search, maybe we skip charts with absolute seconds?
                    # Most charts use grid.
                    # content might be "4" or "234"
                    # ignoring complex # syntax for now or trying to parse float
                    if '#' not in content:
                        try:
                            resolution = float(content)
                        except:
                            pass
                    i = end + 1
                    continue
            
            elif char == '(':
                # BPM change, ignore for grid
                end = text.find(')', i)
                if end != -1:
                    i = end + 1
                    continue
                    
            elif char == ',':
                if has_note_in_current_step:
                    note_events.add(current_time)
                    has_note_in_current_step = False
                
                # Advance time
                if resolution > 0:
                     # 1 whole note = 4 beats
                     # resolution X -> step is 1/X whole note = 4/X beats
                     current_time += 4.0 / resolution
                i += 1
                continue
            
            elif char == 'E':
                # End of chart usually
                # But 'E' can be a touch sensor 'E'. 
                # Touch sensors are A, B, C, D, E.
                # If 'E' follows a number or is part of a touch note 'E1', it's a note.
                # If 'E' is alone on a line? We removed newlines.
                # 'E' is usually the last char.
                # Let's peek ahead. If it's `E` and followed by nothing or just newlines/end, it's End.
                # Or check if it looks like a note format.
                # Touch format: [A-E][1-8] e.g. E1.
                # If just 'E', it's likely End.
                if i + 1 >= length:
                    break # End
                    
                # Lookahead for digit
                if text[i+1].isdigit():
                    has_note_in_current_step = True
                    i += 1
                else: 
                    # Could be End. Or garbage.
                    # If it's 'E' valid note? No, 'E' must be followed by digit for Touch.
                    # Wait, 'Ex' button? No, Buttons are 1-8. Touch is A1-E8.
                    i += 1
                    continue

            elif char in '/`':
                # Simultaneous separator/Pseudo-multi separator
                # Just continue, it doesn't advance time.
                i += 1
                continue
                
            elif char.isspace():
                i += 1
                continue
                
            else:
                # Likely a note or modifier
                # If we see a digit (1-8) or Touch char (A-E) followed by digit
                if char.isdigit() and '1' <= char <= '8':
                    has_note_in_current_step = True
                elif char in 'ABCD' and (i+1 < length and text[i+1].isdigit()):
                    has_note_in_current_step = True
                    i += 2 # Skip letter and digit
                    continue
                elif char == 'E' and (i+1 < length and text[i+1].isdigit()):
                     # Handled above but just in case
                     has_note_in_current_step = True
                     i += 2
                     continue
                
                # Modifiers (h, x, b, s, etc) just pass
                i += 1

        # Sort events
        return sorted(list(note_events))

    def normalize_pattern(self, events: List[float]) -> str:
        """
        Converts a list of absolute beat times into a delta string for fuzzy matching.
        e.g. [0.0, 1.0, 1.5] -> Delta: 1.0, 0.5
        Format: comma separated string of quantized deltas?
        Or json list?
        For database search, maybe a string like "1.00,0.50," is easy to query with LIMIT?
        Actually, we can just store the full list of absolute times (normalized to start at 0) in JSON.
        Then in python we load and search.
        """
        if not events:
            return ""
        
        # Normalize to start at 0
        start = events[0]
        norm = [round(t - start, 3) for t in events] # Round to 3 decimal places (0.001 beat)
        return norm

