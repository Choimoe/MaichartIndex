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

    def parse_chart_to_rhythm(self, chart_text: str, initial_bpm: float = 0.0) -> List[Dict]:
        """
        Converts Simai chart text to a list of note events.
        Returns List of dict: {'time': float, 'bpm': float, 'is_star': bool}
        """
        # Clean text: remove comments
        lines = [re.sub(r'//.*', '', line) for line in chart_text.splitlines()]
        text = ''.join(lines).replace(' ', '').replace('\t', '')
        
        current_time = 0.0
        current_bpm = initial_bpm
        resolution = 4.0 
        
        events = []
        
        # We need to track events in the current step to avoid duplicates if multiple notes valid
        # But now we need individual note attributes (is_star).
        
        step_has_star = False
        step_has_note = False
        step_start_idx = 0
        
        i = 0
        length = len(text)
        
        # Helper to check if a note at i is a star
        # A note starts at i (digit 1-8 or Touch A-E + digit).
        # We look ahead to see if it becomes a slide.
        def is_star_head(index):
            # Skip the note head itself
            # 1-8 (1 char), or A1-E8 (2 chars)
            pk = index
            if text[pk].isdigit():
                pk += 1
            elif text[pk] in 'ABCDE':
                pk += 2
            else:
                return False
            
            # Consume modifiers
            while pk < length and text[pk] in 'bxf':
                pk += 1
                
            if pk >= length:
                return False
                
            # Check for slide chars or star modifiers
            # Slide chars: - ^ < > v p q s z w V
            # Star modifiers: $ ! ? @ *
            c = text[pk]
            if c in '-^<>vpqszwV$!?@*':
                return True
            return False

        while i < length:
            char = text[i]
            
            if char == '{':
                end = text.find('}', i)
                if end != -1:
                    content = text[i+1:end]
                    if '#' not in content:
                        try:
                            resolution = float(content)
                        except:
                            pass
                    i = end + 1
                    continue
            
            elif char == '(':
                # BPM change
                end = text.find(')', i)
                if end != -1:
                    content = text[i+1:end]
                    try:
                        current_bpm = float(content)
                    except:
                        pass
                    i = end + 1
                    continue
                    
            elif char == ',':
                # Commit step
                # The text segment for this beat is from step_start_idx to i (inclusive of comma?)
                # Let's say we include the comma to be safe, or just up to i.
                # User wants "Simai code". `1,2,`
                if step_has_note:
                    events.append({
                        'time': round(current_time, 4),
                        'bpm': current_bpm,
                        'resolution': resolution,
                        'is_star': step_has_star,
                        'src_start': step_start_idx,
                        'src_end': i + 1 # Include the comma
                    })
                    step_has_note = False
                    step_has_star = False
                
                if resolution > 0:
                     current_time += 4.0 / resolution
                
                i += 1
                step_start_idx = i # Next step starts after comma
                continue
            
            elif char == 'E':
                if i + 1 >= length or not text[i+1].isdigit():
                    break 
                else: 
                     # Touch note E1..E8
                     step_has_note = True
                     if is_star_head(i):
                         step_has_star = True
                     i += 2
                     continue

            elif char in '/`':
                i += 1
                continue
                
            elif char.isspace():
                i += 1
                continue
                
            else:
                if char.isdigit() and '1' <= char <= '8':
                    step_has_note = True
                    if is_star_head(i):
                        step_has_star = True
                elif char in 'ABCD' and (i+1 < length and text[i+1].isdigit()):
                    step_has_note = True
                    if is_star_head(i):
                        step_has_star = True
                    i += 2
                    continue
                
                i += 1

        # Commit final step if exists (though usually ends with E or empty)
        if step_has_note:
             events.append({
                'time': round(current_time, 4),
                'bpm': current_bpm,
                'resolution': resolution,
                'is_star': step_has_star,
                'src_start': step_start_idx,
                'src_end': i # End of string
            })

        return events

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

