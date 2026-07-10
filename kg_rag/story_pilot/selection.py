from __future__ import annotations


PILOT12_IDS = [
    "biology_7a_rjb_cpt1",
    "biology_7a_rjb_cpt101",
    "biology_7a_rjb_cpt102",
    "chemistry_9a_rjb_cpt1",
    "chemistry_9a_rjb_cpt100",
    "chemistry_9a_rjb_cpt104",
    "math_1a_rjb_cpt1",
    "math_1a_rjb_cpt11",
    "math_1a_rjb_cpt14",
    "physics_8a_rjb_cpt1",
    "physics_8a_rjb_cpt10",
    "physics_8a_rjb_cpt103",
]


def subject_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for concept_id in PILOT12_IDS:
        subject = concept_id.split("_", 1)[0]
        counts[subject] = counts.get(subject, 0) + 1
    return counts
