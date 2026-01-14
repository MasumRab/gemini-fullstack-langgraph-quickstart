from typing import List

def join_and_truncate(strings: List[str], separator: str = "\n\n", max_length: int = 50000) -> str:
    """
    Joins strings with a separator, stopping before the total length exceeds max_length.
    This is memory-efficient for large lists as it avoids constructing the full joined string.

    Args:
        strings (List[str]): List of strings to join.
        separator (str): Separator to use between strings. Defaults to "\n\n".
        max_length (int): Maximum character length of the result. Defaults to 50000.

    Returns:
        str: The joined string, truncated to fit within max_length.
    """
    if not strings:
        return ""

    current_length = 0
    parts = []
    sep_len = len(separator)

    for i, s in enumerate(strings):
        s_len = len(s)
        # Check if adding this string (and separator if not first) exceeds limit
        # For the first item, no separator
        added_len = s_len if i == 0 else sep_len + s_len

        if current_length + added_len > max_length:
            # If even the first item is too big, truncate it
            if i == 0:
                parts.append(s[:max_length])
                return "".join(parts)

            # If adding the separator + next item exceeds, we check if we can add a partial
            remaining = max_length - current_length
            if remaining > sep_len:
                # Add separator and partial string
                parts.append(separator)
                parts.append(s[:remaining - sep_len])
            elif remaining > 0 and i == 0:
                 # Should be covered by first item check, but for safety
                 parts.append(s[:remaining])
            break

        if i > 0:
            parts.append(separator)
        parts.append(s)
        current_length += added_len

    return "".join(parts)
