"""Print the current authored combination matrix; developer-only, reveals all tiers."""

from drugstory.career.content import COMBINATIONS, MODALITIES, TARGETS

if __name__ == "__main__":
    pairs = {(p["target_id"], p["modality_id"]): p["tier"] for p in COMBINATIONS["combinations"]}
    print("target".ljust(14) + "".join(k[:6].rjust(8) for k in MODALITIES))
    for target in TARGETS:
        print(target.ljust(14) + "".join(str(pairs[target, modality]).rjust(8) for modality in MODALITIES))
