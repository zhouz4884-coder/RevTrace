"""Offline audits for the frozen checkpoint-20 submission evidence.

The functions in this module deliberately operate on serialized experiment
records.  They do not rerun a model and therefore cannot create new serving or
quality evidence.  Their purpose is to make provenance, dependence, resume,
and provisional-display accounting fail closed.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import unicodedata
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Iterable


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def distribution(values: Iterable[float]) -> dict[str, float]:
    rows = [float(value) for value in values]
    return {
        "mean": statistics.mean(rows) if rows else 0.0,
        "p50": percentile(rows, 0.50),
        "p95": percentile(rows, 0.95),
        "maximum": max(rows, default=0.0),
    }


def visible_units(text: str, language: str) -> list[str]:
    value = unicodedata.normalize("NFKC", text).lower()
    if language == "Chinese":
        return [
            character
            for character in value
            if not character.isspace()
            and not unicodedata.category(character).startswith("P")
        ]
    value = re.sub(r"[^\w\s']", " ", value)
    return " ".join(value.split()).split()


def provisional_overwrite_fraction(
    provisional: str,
    authoritative: str,
    language: str,
) -> float:
    """Fraction of displayed units no longer preserved as an exact prefix.

    An empty provisional display contains no user-visible units to overwrite,
    so its overwrite fraction is exactly zero.
    """

    left = visible_units(provisional, language)
    if not left:
        return 0.0
    right = visible_units(authoritative, language)
    common = 0
    for a, b in zip(left, right):
        if a != b:
            break
        common += 1
    return 1.0 - common / len(left)


def audit_provisional_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconstruct the actual P1 -> P2 -> ... -> authority display sequence."""

    grouped: dict[
        tuple[str, int, str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for event in events:
        key = (
            str(event["session_id"]),
            int(event["resolution_age_seconds"]),
            str(event["resolution"]),
            str(event["authoritative_text"]),
            str(event["language"]),
        )
        grouped[key].append(event)

    episodes: list[dict[str, Any]] = []
    transition_overwrites: list[float] = []
    provisional_transition_overwrites: list[float] = []
    authority_transition_overwrites: list[float] = []
    per_session: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "episodes": 0,
            "holdback_events": 0,
            "maximum_burst_length": 0,
            "cumulative_churn": 0.0,
            "maximum_single_visible_modification": 0.0,
        }
    )
    empty_provisional_events = 0

    for key, raw_rows in sorted(grouped.items()):
        session_id, resolution_age, resolution, authority, language = key
        rows = sorted(raw_rows, key=lambda row: int(row["start_age_seconds"]))
        provisional_texts = [str(row["provisional_text"]) for row in rows]
        empty_provisional_events += sum(
            not visible_units(text, language) for text in provisional_texts
        )
        transitions: list[dict[str, Any]] = []
        for index in range(len(provisional_texts) - 1):
            value = provisional_overwrite_fraction(
                provisional_texts[index],
                provisional_texts[index + 1],
                language,
            )
            provisional_transition_overwrites.append(value)
            transition_overwrites.append(value)
            transitions.append(
                {
                    "kind": "provisional_to_provisional",
                    "from_start_age_seconds": int(
                        rows[index]["start_age_seconds"]
                    ),
                    "to_start_age_seconds": int(
                        rows[index + 1]["start_age_seconds"]
                    ),
                    "overwrite_fraction": value,
                }
            )
        final_value = provisional_overwrite_fraction(
            provisional_texts[-1], authority, language
        )
        authority_transition_overwrites.append(final_value)
        transition_overwrites.append(final_value)
        transitions.append(
            {
                "kind": "provisional_to_authority",
                "from_start_age_seconds": int(rows[-1]["start_age_seconds"]),
                "to_resolution_age_seconds": resolution_age,
                "overwrite_fraction": final_value,
            }
        )
        cumulative_churn = sum(
            float(row["overwrite_fraction"]) for row in transitions
        )
        maximum_modification = max(
            (float(row["overwrite_fraction"]) for row in transitions),
            default=0.0,
        )
        episode = {
            "session_id": session_id,
            "language": language,
            "resolution_age_seconds": resolution_age,
            "resolution": resolution,
            "burst_length": len(rows),
            "start_ages_seconds": [
                int(row["start_age_seconds"]) for row in rows
            ],
            "cumulative_churn": cumulative_churn,
            "maximum_single_visible_modification": maximum_modification,
            "transitions": transitions,
        }
        episodes.append(episode)
        session = per_session[session_id]
        session["episodes"] += 1
        session["holdback_events"] += len(rows)
        session["maximum_burst_length"] = max(
            int(session["maximum_burst_length"]), len(rows)
        )
        session["cumulative_churn"] += cumulative_churn
        session["maximum_single_visible_modification"] = max(
            float(session["maximum_single_visible_modification"]),
            maximum_modification,
        )

    burst_lengths = [float(row["burst_length"]) for row in episodes]
    cumulative_churn = [float(row["cumulative_churn"]) for row in episodes]
    maximum_modifications = [
        float(row["maximum_single_visible_modification"]) for row in episodes
    ]
    return {
        "schema_version": 1,
        "definition": (
            "Actual display transitions are reconstructed per resolution "
            "episode as P1->P2->...->authority. Appended units are free; an "
            "empty provisional display has zero overwrite."
        ),
        "holdback_events": len(events),
        "resolution_episodes": len(episodes),
        "multi_holdback_episodes": sum(
            int(row["burst_length"]) > 1 for row in episodes
        ),
        "empty_provisional_events": empty_provisional_events,
        "empty_provisional_overwrite_boundary": 0.0,
        "transition_counts": {
            "all": len(transition_overwrites),
            "provisional_to_provisional": len(
                provisional_transition_overwrites
            ),
            "provisional_to_authority": len(
                authority_transition_overwrites
            ),
        },
        "transition_overwrite_fraction": distribution(
            transition_overwrites
        ),
        "provisional_to_provisional_overwrite_fraction": distribution(
            provisional_transition_overwrites
        ),
        "provisional_to_authority_overwrite_fraction": distribution(
            authority_transition_overwrites
        ),
        "episode_burst_length": distribution(burst_lengths),
        "episode_cumulative_churn": distribution(cumulative_churn),
        "episode_maximum_single_visible_modification": distribution(
            maximum_modifications
        ),
        "session_maximum_burst_length": distribution(
            float(row["maximum_burst_length"])
            for row in per_session.values()
        ),
        "sessions_with_holdback": len(per_session),
        "per_session": dict(sorted(per_session.items())),
        "episodes": episodes,
    }


def _connected_components(
    session_sources: dict[str, set[str]],
) -> list[list[str]]:
    source_sessions: dict[str, list[str]] = defaultdict(list)
    for session_id, sources in session_sources.items():
        for source in sources:
            source_sessions[source].append(session_id)
    adjacency = {session_id: set() for session_id in session_sources}
    for sessions in source_sessions.values():
        for session_id in sessions:
            adjacency[session_id].update(
                other for other in sessions if other != session_id
            )
    seen: set[str] = set()
    components: list[list[str]] = []
    for session_id in sorted(adjacency):
        if session_id in seen:
            continue
        stack = [session_id]
        seen.add(session_id)
        component: list[str] = []
        while stack:
            current = stack.pop()
            component.append(current)
            for other in adjacency[current]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        components.append(sorted(component))
    return sorted(components, key=lambda row: (-len(row), row))


def audit_quality_dependencies(
    paired_sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Describe source reuse without treating sessions as independent draws."""

    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in paired_sessions:
        by_language[str(row["language"])].append(row)
    languages: dict[str, Any] = {}
    cross_session_dependence = False
    for language, rows in sorted(by_language.items()):
        session_sources = {
            str(row["session_id"]): {
                str(value) for value in row["source_ids"]
            }
            for row in rows
        }
        assignments = [
            str(source)
            for row in rows
            for source in row["source_ids"]
        ]
        counts = Counter(assignments)
        pair_overlaps: list[int] = []
        pair_jaccards: list[float] = []
        for left, right in combinations(sorted(session_sources), 2):
            intersection = session_sources[left] & session_sources[right]
            union = session_sources[left] | session_sources[right]
            pair_overlaps.append(len(intersection))
            pair_jaccards.append(
                len(intersection) / len(union) if union else 0.0
            )
        components = _connected_components(session_sources)
        reused = sum(value > 1 for value in counts.values())
        cross_session_dependence |= reused > 0
        languages[language] = {
            "sessions": len(rows),
            "source_assignments": len(assignments),
            "unique_sources": len(counts),
            "within_session_duplicate_source_events": sum(
                len(row["source_ids"])
                - len({str(value) for value in row["source_ids"]})
                for row in rows
            ),
            "sources_reused_across_sessions": reused,
            "maximum_source_multiplicity": max(
                counts.values(), default=0
            ),
            "session_pairs": len(pair_overlaps),
            "session_pairs_with_any_overlap": sum(
                value > 0 for value in pair_overlaps
            ),
            "pair_overlap_count": distribution(
                float(value) for value in pair_overlaps
            ),
            "pair_source_jaccard": distribution(pair_jaccards),
            "source_overlap_connected_components": len(components),
            "component_sizes": [len(component) for component in components],
        }
    return {
        "schema_version": 1,
        "sessions": len(paired_sessions),
        "languages": languages,
        "cross_session_source_dependence": cross_session_dependence,
        "bootstrap_scope": (
            "The existing paired bootstrap resamples fixed constructed "
            "sessions. It is descriptive for this frozen sample and is not an "
            "independent-source population interval."
        ),
        "cluster_bootstrap_status": (
            "NOT_IDENTIFIABLE_FROM_THIS_DESIGN"
            if any(
                row["source_overlap_connected_components"] < 2
                for row in languages.values()
            )
            else "COMPONENT_BOOTSTRAP_AVAILABLE"
        ),
    }


def validate_resume_quality(
    *,
    resumed: dict[str, Any],
    expected_sessions: list[dict[str, Any]],
    mechanism_digest: str,
    contract_manifest_sha256: str,
    expected_deployment: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed before reusing frozen quality paths."""

    checks: dict[str, bool] = {}
    checks["mechanism_digest"] = (
        resumed.get("mechanism_digest") == mechanism_digest
    )
    checks["contract_manifest_sha256"] = (
        resumed.get("contract_manifest_sha256")
        == contract_manifest_sha256
    )
    deployment = resumed.get("deployment", {})
    checks["deployment"] = all(
        deployment.get(key) == value
        for key, value in expected_deployment.items()
    )
    rows = resumed.get("paired_sessions", [])
    session_ids = [str(row.get("session_id")) for row in rows]
    checks["unique_resume_sessions"] = (
        len(session_ids) == len(set(session_ids))
    )
    by_session = {str(row["session_id"]): row for row in rows}
    expected_ids = {str(row["session_id"]) for row in expected_sessions}
    checks["session_set"] = set(by_session) == expected_ids
    source_reference_rows: list[dict[str, Any]] = []
    transcripts_present = True
    source_reference_match = checks["session_set"]
    if checks["session_set"]:
        for expected in expected_sessions:
            session_id = str(expected["session_id"])
            observed = by_session[session_id]
            matched = bool(
                observed.get("language") == expected.get("language")
                and list(observed.get("source_ids", []))
                == list(expected.get("source_ids", []))
                and observed.get("reference") == expected.get("reference")
            )
            source_reference_match &= matched
            transcripts = observed.get("transcripts", {})
            transcripts_present &= all(
                isinstance(transcripts.get(mode), str)
                for mode in ("continuous", "checkpoint_verify")
            )
            source_reference_rows.append(
                {
                    "session_id": session_id,
                    "language": expected.get("language"),
                    "source_ids": list(expected.get("source_ids", [])),
                    "reference": expected.get("reference"),
                }
            )
    checks["source_ids_and_references"] = source_reference_match
    checks["reusable_transcripts_present"] = transcripts_present
    rounds = resumed.get("rounds", {})
    checks["reusable_rounds_present"] = all(
        isinstance(rounds.get(mode), list)
        for mode in ("continuous", "checkpoint_verify")
    )
    checks["reusable_wall_times_present"] = all(
        mode in resumed.get("mode_wall_seconds", {})
        for mode in ("continuous", "checkpoint_verify")
    )
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise ValueError(
            "resume quality artifact failed checks: " + ", ".join(failed)
        )
    return {
        "schema_version": 1,
        "decision": "RESUME_QUALITY_ATTESTATION_PASS",
        "checks": checks,
        "sessions": len(expected_sessions),
        "source_reference_digest": digest_value(source_reference_rows),
        "mechanism_digest": mechanism_digest,
        "contract_manifest_sha256": contract_manifest_sha256,
        "expected_deployment": expected_deployment,
    }
