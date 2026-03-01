import difflib
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, List

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


def get_research_topic(messages: List[AnyMessage]) -> str:
    """
    Derive a single research topic string from a sequence of chat messages.
    
    When given a single message, returns that message's content. When given multiple messages,
    concatenates each message's content into a single string, prefixing HumanMessage entries
    with "User: " and AIMessage entries with "Assistant: ", each followed by a newline.
    
    Parameters:
        messages (List[AnyMessage]): Sequence of chat messages (e.g., HumanMessage and AIMessage).
    
    Returns:
        str: The resulting research topic string assembled from the provided messages.
    """
    # check if request has a history and combine the messages into a single string
    if len(messages) == 1:
        research_topic = messages[-1].content
    else:
        research_topic = ""
        for message in messages:
            if isinstance(message, HumanMessage):
                research_topic += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                research_topic += f"Assistant: {message.content}\n"
    return research_topic


def resolve_urls(urls_to_resolve: List[Any], id: int) -> Dict[str, str]:
    """
    Create stable short URLs for a list of Vertex AI Search results.
    
    Each unique original URL is mapped to a shortened form that includes the provided `id`
    and the index of the URL's first occurrence. Duplicate original URLs receive the same
    shortened value.
    
    Parameters:
        urls_to_resolve (List[Any]): Sequence of result objects from which the original URL
            is taken via `site.web.uri`.
        id (int): Identifier to include in every shortened URL to provide contextual grouping.
    
    Returns:
        Dict[str, str]: Mapping from each original long URL to its shortened URL.
    """
    prefix = "https://vertexaisearch.cloud.google.com/id/"
    urls = [site.web.uri for site in urls_to_resolve]

    # Create a dictionary that maps each unique URL to its first occurrence index
    resolved_map = {}
    for idx, url in enumerate(urls):
        if url not in resolved_map:
            resolved_map[url] = f"{prefix}{id}-{idx}"

    return resolved_map


def insert_citation_markers(text, citations_list):
    """
    Insert citation markers into text at the citations' end positions.
    
    Each citation in `citations_list` must include `start_index`, `end_index`, and `segments`. Each segment is a mapping with `label` and `short_url`. For a citation, this function appends a marker composed of its segments in order, where each segment is formatted as " [label](short_url)" and placed immediately after `end_index` in the original `text`. Citations that overlap or are out of order are handled by placing markers according to ascending `end_index`.
    
    Parameters:
        text (str): The original text to annotate.
        citations_list (List[dict]): List of citation dictionaries. Required keys:
            - start_index (int): Start index of the cited span in `text`.
            - end_index (int): End index of the cited span in `text`; marker is placed after this index.
            - segments (List[dict]): Segment entries for the citation; each segment must contain:
                - label (str): Display label for the segment.
                - short_url (str): Shortened URL used in the marker.
    
    Returns:
        str: The input text with citation markers inserted at the specified end positions.
    """
    # ⚡ Bolt Optimization: Sort by end_index ascending for linear O(N) pass.
    # This replaces O(N^2) string concatenation loop with O(N) list construction.
    sorted_citations = sorted(
        citations_list, key=lambda c: (c["end_index"], c.get("start_index", 0))
    )

    parts = []
    last_idx = 0

    for citation in sorted_citations:
        end_idx = citation["end_index"]

        # Append text chunk from last position to current citation position
        if end_idx > last_idx:
            parts.append(text[last_idx:end_idx])
            last_idx = end_idx

        # Build marker
        marker_to_insert = ""
        for segment in citation["segments"]:
            marker_to_insert += f" [{segment['label']}]({segment['short_url']})"

        parts.append(marker_to_insert)

    # Append remaining text
    if last_idx < len(text):
        parts.append(text[last_idx:])

    return "".join(parts)


def get_citations(response, resolved_urls_map):
    """
    Builds a list of citation entries extracted from a Gemini model response's grounding metadata.
    
    Parameters:
        response: The Gemini response object expected to contain `candidates[0].grounding_metadata`
            with `grounding_supports` and `grounding_chunks`.
        resolved_urls_map (dict): Mapping from original chunk URIs to resolved or shortened URLs.
    
    Returns:
        list: A list of citation dictionaries. Each dictionary contains:
            - "start_index" (int): Starting character index of the cited segment (defaults to 0 when missing).
            - "end_index" (int): Ending character index of the cited segment (must be present for a citation to be included).
            - "segments" (list[dict]): List of segment objects for the grounding chunks; each segment dict has:
                - "label" (str or None): A trimmed title used as the segment label (file extension removed when present).
                - "short_url" (str or None): The resolved/shortened URL from `resolved_urls_map` for the chunk's URI.
                - "value" (str): The original chunk URI.
        Returns an empty list if the response lacks valid candidates, grounding supports, or if no valid citations are found.
    
    Notes:
        - Malformed or incomplete grounding supports/chunks are skipped rather than raising errors.
    """
    citations = []

    # Ensure response and necessary nested structures are present
    if not response or not response.candidates:
        return citations

    candidate = response.candidates[0]
    if (
        not hasattr(candidate, "grounding_metadata")
        or not candidate.grounding_metadata
        or not hasattr(candidate.grounding_metadata, "grounding_supports")
    ):
        return citations

    for support in candidate.grounding_metadata.grounding_supports:
        citation = {}

        # Ensure segment information is present
        if not hasattr(support, "segment") or support.segment is None:
            continue  # Skip this support if segment info is missing

        start_index = (
            support.segment.start_index
            if support.segment.start_index is not None
            else 0
        )

        # Ensure end_index is present to form a valid segment
        if support.segment.end_index is None:
            continue  # Skip if end_index is missing, as it's crucial

        # Add 1 to end_index to make it an exclusive end for slicing/range purposes
        # (assuming the API provides an inclusive end_index)
        # However, check if the end_index is already exclusive or inclusive based on observation.
        # Typically Gemini API returns exclusive end index for text segments.
        # If experimental observation shows off-by-one, adjust here.
        citation["start_index"] = start_index
        citation["end_index"] = support.segment.end_index

        citation["segments"] = []
        if (
            hasattr(support, "grounding_chunk_indices")
            and support.grounding_chunk_indices
        ):
            for ind in support.grounding_chunk_indices:
                try:
                    chunk = candidate.grounding_metadata.grounding_chunks[ind]
                    resolved_url = resolved_urls_map.get(chunk.web.uri, None)
                    title = chunk.web.title
                    # Remove file extension if present (e.g. "Doc.pdf" -> "Doc")
                    # If no dot, use full title.
                    label = title.split(".")[0] if title and "." in title else title
                    citation["segments"].append(
                        {
                            "label": label,
                            "short_url": resolved_url,
                            "value": chunk.web.uri,
                        }
                    )
                except (IndexError, AttributeError, NameError):
                    # Skip malformed grounding chunk — chunk, web, or uri attribute missing
                    continue
        citations.append(citation)
    return citations


def join_and_truncate(
    strings: List[str], max_length: int, separator: str = "\n\n"
) -> str:
    """
    Join a list of strings into one string, stopping and truncating when adding another segment would exceed max_length.
    
    Parameters:
        strings (List[str]): Strings to join in order.
        max_length (int): Maximum allowed length of the returned string.
        separator (str): Separator placed between joined strings.
    
    Returns:
        str: Joined string with length <= max_length; the final appended segment may be truncated to fit.
    """
    if not strings:
        return ""

    result_parts = []
    current_length = 0
    sep_len = len(separator)

    for i, s in enumerate(strings):
        # Determine overhead for separator
        overhead = sep_len if i > 0 else 0

        # Check if we can fit the full string
        if current_length + overhead + len(s) <= max_length:
            result_parts.append(s)
            current_length += overhead + len(s)
        else:
            # Truncate
            remaining = max_length - (current_length + overhead)
            if remaining > 0:
                result_parts.append(s[:remaining])
            break

    return separator.join(result_parts)


# ⚡ Bolt Optimization: Cache LLM instance creation
# Creating ChatGoogleGenerativeAI objects involves some overhead.
# Since config (model, temp) is usually stable within a session, we can reuse instances.
@lru_cache(maxsize=16)
def get_cached_llm(model: str, temperature: float) -> Any:
    """
    Selects and returns a configured LLM client implementation based on the model name.
    
    If the model name contains the substring "gemma" (case-insensitive), returns a GemmaAdapter wrapping a Gemma client; otherwise returns a ChatGoogleGenerativeAI configured with the provided model and temperature.
    
    Parameters:
        model (str): Model identifier string; the presence of "gemma" (case-insensitive) selects the Gemma adapter path.
        temperature (float): Sampling temperature to configure on the returned client.
    
    Returns:
        An LLM client instance: a `GemmaAdapter` when `model` indicates Gemma, or a `ChatGoogleGenerativeAI` otherwise.
    """
    is_gemma = "gemma" in model.lower()

    if is_gemma:
        from agent.gemma_client import get_gemma_client
        from agent.llm_client import GemmaAdapter

        # Instantiate the correct provider (Vertex or Ollama) from app_config
        client = get_gemma_client()
        # Return an adapter that mimics LangChain's invoke interface
        return GemmaAdapter(client=client, temperature=temperature)

    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        api_key=os.getenv("GEMINI_API_KEY"),
    )


def has_fuzzy_match(
    keyword: str, candidates: Iterable[str], cutoff: float = 0.8
) -> bool:
    """
    Determine whether any candidate string fuzzy-matches the keyword at or above the given similarity cutoff.
    
    Parameters:
        keyword (str): The string to compare against.
        candidates (Iterable[str]): Iterable of candidate strings to test.
        cutoff (float): Minimum similarity ratio between 0.0 and 1.0 required to count as a match.
    
    Returns:
        True if a candidate meets or exceeds the cutoff, False otherwise.
    """
    # Reuse SequenceMatcher instance for efficiency
    matcher = difflib.SequenceMatcher(b=keyword)

    for candidate in candidates:
        matcher.set_seq1(candidate)
        # ⚡ Bolt Optimization: Check real_quick_ratio first as an O(1) upper bound based on length
        if (
            matcher.real_quick_ratio() >= cutoff
            and matcher.quick_ratio() >= cutoff
            and matcher.ratio() >= cutoff
        ):
            return True
    return False
