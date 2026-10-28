"""Fault-harness-only logical post-sync trigger; no admission-policy change."""


def parse_post_sync_target(value):
    if value is None:
        return None
    fields = value.split(':')
    if len(fields) != 2 or any(not x.isdecimal() for x in fields):
        raise ValueError('logical post-sync target must be session:positive_sample_frontier')
    sid, frontier = map(int, fields)
    if frontier <= 0:
        raise ValueError('logical fault frontier must be positive')
    return sid, frontier


def target_in_synced_group(transitions, target):
    """Call only AFTER actual commit_transitions succeeds, before installation."""
    if target is None:
        return False
    sid, frontier = target
    for transition in transitions:
        event = transition['event']
        if (transition['session_id'] == sid and
                event['event'] == 'canonical-segment-committed' and
                event['audio_end_sample'] == frontier):
            return True
    return False
