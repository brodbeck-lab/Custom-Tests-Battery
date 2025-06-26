import os
import pandas as pd

def load_sentences():
    # Get the absolute path to the CSV relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "Sentence_Dictionary.csv")

    # Load the CSV
    df = pd.read_csv(csv_path)
    sentence_map = dict(zip(df["Name"], df["Text"]))

    # Manually defined flow (from Object0)
    flow_items = [
        "Instruction1", "Ex1", "Ex2", "Recall1", "Ex3", "Ex4", "Ex5", "Recall2",
        "Instruction2", "Sen111", "Sen112", "Recallexp1", "Sen121", "Sen122", "Sen123", "Sen124", "Recallexp2",
        "Sen131", "Sen132", "Sen133", "Recallexp3", "Sen141", "Sen142", "Sen143", "Sen144", "Sen145", "Recallexp4",
        "Sen151", "Sen152", "Sen153", "Sen154", "Sen155", "Sen156", "Recallexp5", "Sen211", "Sen212", "Sen213",
        "Sen214", "Sen215", "Recallexp6", "Sen221", "Sen222", "Recallexp7", "Sen231", "Sen232", "Sen233", "Sen234",
        "Recallexp8", "Sen241", "Sen242", "Sen243", "Sen244", "Sen245", "Sen246", "Recallexp9", "Sen251", "Sen252",
        "Sen253", "Recallexp10", "Sen311", "Sen312", "Sen313", "Sen314", "Sen315", "Sen316", "Recallexp11", "Sen321",
        "Sen322", "Sen323", "Recallexp12", "Sen331", "Sen332", "Sen333", "Sen334", "Sen335", "Recallexp13", "Sen341",
        "Sen342", "Sen343", "Sen344", "Recallexp14", "Sen351", "Sen352", "Recallexp15", "Sen411", "Sen412", "Sen413",
        "Sen414", "Recallexp16", "Sen421", "Sen422", "Sen423", "Sen424", "Sen425", "Sen426", "Recallexp17", "Sen431",
        "Sen432", "Recallexp18", "Sen441", "Sen442", "Sen443", "Recallexp19", "Sen451", "Sen452", "Sen453", "Sen454",
        "Sen455", "Recallexp20", "Sen511", "Sen512", "Sen513", "Recallexp21", "Sen521", "Sen522", "Sen523", "Sen524",
        "Sen525", "Recallexp22", "Sen531", "Sen532", "Sen533", "Sen534", "Sen535", "Sen536", "Recallexp23", "Sen541",
        "Sen542", "Recallexp24", "Sen551", "Sen552", "Sen553", "Sen554", "Recallexp25"
    ]

    # Group sentences into blocks, each ending with Recallexp
    blocks = []
    current_block = []
    for item in flow_items:
        if item.startswith("Recall"):
            blocks.append(current_block)
            current_block = []
        else:
            current_block.append(item)

    # Convert sentence IDs to actual texts
    sentence_blocks = [
        [sentence_map[sid] for sid in block if sid in sentence_map]
        for block in blocks
    ]

    return sentence_blocks
