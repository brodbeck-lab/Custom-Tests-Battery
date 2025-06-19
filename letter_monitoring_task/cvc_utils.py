def load_cvc_sequence(filepath, list_id=1):
    """
    Parses the vmtcvc.seq file and returns a list of (char, is_cvc) tuples.
    list_id is 1-based.
    """
    sequence = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= list_id * 2:
                    char = parts[(list_id - 1) * 2].strip()
                    label = parts[(list_id * 2) - 1].strip()
                    is_cvc = label == "-1"
                    sequence.append((char, is_cvc))
    except Exception as e:
        print(f"Failed to read {filepath}: {e}")
    return sequence
