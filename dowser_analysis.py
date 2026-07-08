import json
import re
from pathlib import Path
# File Paths

BASE_DIR = Path(__file__).resolve().parent

KEYWORDS_FILE = BASE_DIR / "keywords.txt"
AIRLINE_VARIANTS_FILE = BASE_DIR / "airline_variants.json"

with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
    KEYWORDS = [k.strip().lower() for k in f.read().split(",") if k.strip()]

with open(AIRLINE_VARIANTS_FILE, "r", encoding="utf-8") as f:
    AIRLINE_VARIANTS = json.load(f)

def remove_repeated_sentence_words(text, separators):
    """
    Removes duplicated words/sentences.

    Example:
    --------
    hello hello hello -> hello

    Thank you.
    Thank you.
    -> Thank you.
    """

    if len(separators) == 0:
        return text

    if len(separators) == 4:
        text = text.replace(". ", ".")

    parts = text.split(separators[-1])

    cleaned = []

    for part in parts:

        if not cleaned:
            cleaned.append(part)

        elif cleaned[-1] != part:
            cleaned.append(part)

    if separators[-1] == ".":
        joiner = ". "

    elif separators[-1] == ",":
        joiner = ","

    elif separators[-1] == "?":
        joiner = "?"

    else:
        joiner = " "

    separators.pop()

    return remove_repeated_sentence_words(
        joiner.join(cleaned),
        separators
    )

# Keyword Search

def search_keywords(text):
    """
    Finds keywords and monetary / numeric values
    from transcript.
    """

    text = text.lower()

    keywords_found = []

    for keyword in KEYWORDS:

        matches = re.findall(
            rf"\b{re.escape(keyword)}\b",
            text
        )

        if matches:

            if matches[0] not in keywords_found:
                keywords_found.append(matches[0])

    keywords_found = ",".join(keywords_found)

    numbers_found = re.findall(
        r"\$?\s*[0-9]+\.*\s*[0-9]+\s*[0-9]+",
        text
    )

    numbers_found = ",".join(numbers_found)

    return keywords_found, numbers_found

# Airline Detection


def find_airlines(text):
    """
    Detect airline names from transcript using airline_variants.json.

    Returns:
        "Delta"
        "Delta|United"
        "None"
    """

    text_lower = text.lower()

    airlines_found = []
    airline_variant_mapper = {}

    def airline_checker(airline, variant, false_positives):

        false_positives = false_positives + [
            f"{variant[0]} for {variant}",
            f"{variant[0]} like in {variant}",
            f"{variant[0]} as {variant}",
            f"{variant[0]} as in {variant}",
            f"{variant[0]} of {variant}",
            f"{variant[0]} like {variant}",
        ]

        true_positives = [
            "what airline",
            "which airline",
            "airline name",
            "name of airline",
            "which flight",
            "flight with",
            "flight of",
            "booked with",
            "looking for",
            "flying with",
            "airline",
            "which airway",
            "airline do you prefer",
            "cheaper",
            "economical",
            "bought it directly with",
            "sky directly",
            "from which",
            f"{variant} flight",
            f"we are not {variant}",
            f"talking to {variant}",
        ]

        pattern = re.compile(
            rf"\b{re.escape(variant)}\b",
            re.IGNORECASE
        )

        indices = [m.start() for m in pattern.finditer(text_lower)]

        for index in indices:

            start = max(0, index - 200)
            end = min(len(text_lower), index + 200)

            window = text_lower[start:end]

            if any(fp in window for fp in false_positives):
                continue

            if any(tp in window for tp in true_positives):

                airlines_found.append(airline.lower())

                airline_variant_mapper[airline.lower()] = variant

                break

    # ------------------------------------------------------

    for airline, variants in AIRLINE_VARIANTS.items():

        airline_lower = airline.lower()

        if airline_lower in text_lower:

            airlines_found.append(airline_lower)
            continue

        for variant in map(str.lower, variants):

            if variant not in text_lower:
                continue

            if variant == "united":

                airline_checker(
                    airline,
                    variant,
                    [
                        "united state",
                        "united states",
                        "united dollar",
                        "united dollars",
                    ],
                )

            elif variant == "american":

                airline_checker(
                    airline,
                    variant,
                    [
                        "latin american",
                        "american express",
                        "native american",
                        "american republic",
                        "american embassy",
                        "american card",
                        "american visa",
                        "americano",
                        "american people",
                        "american dollar",
                        "american consulate",
                    ],
                )

            elif variant == "sky":

                airline_checker(
                    airline,
                    variant,
                    [
                        "skyscanner",
                        "skype",
                    ],
                )

            elif variant == "france":

                airline_checker(
                    airline,
                    variant,
                    [
                        "trip to france",
                        "it's in france",
                    ],
                )

            elif variant == "portugal":

                airline_checker(
                    airline,
                    variant,
                    [
                        "trip to portugal",
                        "trips to portugal",
                        "it's in portugal",
                    ],
                )

            elif variant == "emirates":

                airline_checker(
                    airline,
                    variant,
                    [
                        "e like emirates",
                    ],
                )

            elif variant == "wiser":

                airline_checker(
                    airline,
                    variant,
                    [
                        "i am not wiser",
                        "i'm not wiser",
                        "more wiser",
                        "wiser than",
                        "wiser enough",
                        "wiser mind",
                    ],
                )

            else:

                airline_checker(
                    airline,
                    variant,
                    [],
                )

            break

    # ------------------------------------------------------

    if not airlines_found:
        return "None"

    variant_to_airline = {
        v: k
        for k, v in airline_variant_mapper.items()
    }

    ordered_variants = []

    for airline in airlines_found:

        ordered_variants.append(
            airline_variant_mapper.get(
                airline,
                airline
            )
        )

    ordered_variants = sorted(
        ordered_variants,
        key=lambda x: text_lower.find(x)
    )

    ordered_airlines = []

    for variant in ordered_variants:

        ordered_airlines.append(
            variant_to_airline.get(
                variant,
                variant
            ).title()
        )

    # remove duplicates while preserving order

    ordered_airlines = list(dict.fromkeys(ordered_airlines))

    print("AIRLINES FOUND:", ordered_airlines)

    return "|".join(ordered_airlines)

# Route Detection

def find_route(text):
    """
    Detects routes like:
    'from New York to London'
    """

    try:

        pattern = r"\bfrom\s+([A-Za-z ]+?)\s+to\s+([A-Za-z ]+)"

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            source = match.group(1).strip().title()
            destination = match.group(2).strip().title()

            return f"{source} -> {destination}"

        return None

    except Exception:

        return None

# Call Nature Helpers

NEW_BOOKING_KEYWORDS = {
    "a new booking",
    "a new reservation",
    "buy a flight",
    "new ticket",
    "book a flight",
    "i want to travel",
    "make a booking",
    "the new booking department",
}

SALES_KEYWORDS = {
    "penalty",
    "pay",
    "have to pay",
    "price",
    "refund",
    "credit",
    "debit",
    "pet reservation",
    "card number",
    "digit number of your card",
    "receive your tickets",
    "add a pet",
    "infant reservation",
    "payment has been received",
    "is it a debit or a credit card",
    "card holder name",
    "payment link",
    "window",
    "calling to get a quote",
    "group reservation",
    "what's the price",
    "i want to change the reservation",
}

POTENTIAL_KEYWORDS = {
    "change the day of my flight",
    "change",
    "cancellation",
    "cancel",
    "pet",
    "animal",
    "cat",
    "dog",
    "change the date",
    "change date",
    "correction",
    "is not correct",
    "incorrect",
    "missspelled",
    "change the destination",
    "want to fly from",
}


def find_mode(labels):

    if "New Booking" in labels:
        return "New Booking"

    sales_count = labels.count("Sales")
    potential_count = labels.count("Potential")
    nonsales_count = labels.count("Non-Sales")

    if sales_count + potential_count >= nonsales_count:

        if sales_count >= potential_count:
            return "Sales"

        return "Potential"

    return "Non-Sales"


def predict_callnature(keyword_string):

    labels = []

    for keyword in keyword_string.split(","):

        keyword = keyword.strip().lower()

        if not keyword:
            continue

        if keyword in NEW_BOOKING_KEYWORDS:
            labels.append("New Booking")

        elif keyword in SALES_KEYWORDS:
            labels.append("Sales")

        elif keyword in POTENTIAL_KEYWORDS:
            labels.append("Potential")

        else:
            labels.append("Non-Sales")

    if not labels:
        return "Non-Sales"

    return find_mode(labels)

# Main Analyzer

def analyze_text(result):
    """
    Parameters
    ----------
    result = {
        "text": transcript,
        "language": detected_language
    }

    Returns
    -------
    dict
    """

    try:

        text = remove_repeated_sentence_words(
            result["text"],
            [" ", ",", "?", "."]
        )

        airline = find_airlines(text)

        keywords_found, numbers_found = search_keywords(text)

        route = find_route(text)

        callnature = predict_callnature(
            keywords_found
        )

        language = result.get(
            "language",
            "unknown"
        )

        return {
            "status": "success",
            "text": text,
            "language": language,
            "airline": airline,
            "route": route,
            "keywords": keywords_found,
            "numbers": numbers_found,
            "callnature": callnature,
        }

    except Exception as e:

        print("Analysis Error:", e)

        return {
            "status": "failed",
            "text": None,
            "language": None,
            "airline": None,
            "route": None,
            "keywords": None,
            "numbers": None,
            "callnature": None,
            "error": str(e),
        }
