def normalize_name(name: str) -> str:
    # Collapse multiple spaces and title-case the result
    words = name.strip().split()
    return ' '.join(words).title()



def get_item_variant_type(name: str):
    name_clean = name.strip()
    lowered = name_clean.lower()

    if lowered.startswith("double "):
        return "double", normalize_name(name_clean[7:])
    elif lowered.startswith("triple "):
        return "triple", normalize_name(name_clean[7:])
    else:
        return "single", normalize_name(name_clean)
    

