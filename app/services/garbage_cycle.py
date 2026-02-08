from datetime import date

REFERENCE_FRIDAY = date(2026, 2, 6)
REFERENCE_TYPE = "black"  # 2026-02-06 => black


def garbage_bin_type_for_pickup(pickup_date: date) -> str:
    """
    Returns: "black" or "blue"

    Rule:
    - 2026-02-06 => black
    - 2026-02-13 => blue
    - alternates weekly
    """
    weeks_since = (pickup_date - REFERENCE_FRIDAY).days // 7

    if weeks_since % 2 == 0:
        return "black"
    return "blue"


def garbage_bins_text(pickup_date: date) -> str:
    t = garbage_bin_type_for_pickup(pickup_date)

    if t == "black":
        return "🟩 Green Bin & ⬛ Garbage (Black bin)"
    return "🟩 Green Bin & 🟦 Recycling (Blue bin)"
