"""Independent span forest/accounting. No primary summarizer is imported."""
from collections import Counter, defaultdict
import math
import statistics


class AuditError(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise AuditError(message)


def q(values, probability):
    if not values:
        return None
    values = sorted(values)
    at = (len(values) - 1) * probability
    low, high = int(at), min(int(at) + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (at - low)


def interval_union(intervals):
    end, total = None, 0
    for a, b in sorted(intervals):
        need(b >= a, 'reversed interval')
        total += b-a if end is None or a >= end else max(0, b-end)
        end = b if end is None else max(end, b)
    return total


def sid(row):
    return row['role'], row['pid'], row['thread_id'], row['span_id']


def forest(rows):
    """Preserve asymmetric timer brackets; CPU > wall is NOT an error."""
    by_id, pid_ids, children = {}, {}, defaultdict(list)
    for row in rows:
        key = sid(row)
        need(key not in by_id, 'duplicate complete span identity')
        need((row['role'], row['pid'], row['span_id']) not in pid_ids,
             'same process span ID reused across threads')
        pid_ids[row['role'], row['pid'], row['span_id']] = key
        for field in ('start_ns', 'end_ns', 'wall_ns', 'thread_cpu_ns', 'process_cpu_ns',
                      'exclusive_wall_ns', 'exclusive_thread_cpu_ns'):
            need(type(row[field]) is int and row[field] >= 0, 'invalid timing value: ' + field)
        need(row['end_ns'] >= row['start_ns'] and row['wall_ns'] == row['end_ns']-row['start_ns'],
             'span wall endpoints disagree')
        by_id[key] = row
    for key, row in by_id.items():
        parent_id = row.get('parent_span_id')
        if parent_id is None:
            continue
        pkey = row['role'], row['pid'], row['thread_id'], parent_id
        need(pkey in by_id, 'missing parent or cross-thread parent')
        parent = by_id[pkey]
        need(parent['start_ns'] <= row['start_ns'] <= row['end_ns'] <= parent['end_ns'],
             'child outside parent wall interval')
        children[pkey].append(key)
        seen, cursor = {key}, pkey
        while cursor is not None:
            need(cursor not in seen, 'span parent cycle')
            seen.add(cursor)
            ancestor = by_id[cursor]
            p = ancestor.get('parent_span_id')
            cursor = None if p is None else (ancestor['role'], ancestor['pid'], ancestor['thread_id'], p)
            need(cursor is None or cursor in by_id, 'missing ancestor')
    enriched = []
    for key, row in by_id.items():
        direct = sorted((by_id[c] for c in children[key]), key=lambda r: (r['start_ns'], r['end_ns']))
        need(all(a['end_ns'] <= b['start_ns'] for a, b in zip(direct, direct[1:])),
             'overlapping same-thread sibling spans')
        ew = row['wall_ns'] - sum(c['wall_ns'] for c in direct)
        ec = row['thread_cpu_ns'] - sum(c['thread_cpu_ns'] for c in direct)
        # This is parent-minus-children consistency, NOT wall-minus-CPU.
        need(ew >= 0 and ec >= 0, 'negative exclusive parent/child accounting')
        need(row['exclusive_wall_ns'] == ew and row['exclusive_thread_cpu_ns'] == ec,
             'reported exclusive time differs from independent forest')
        need(not row.get('exclusive_wall_negative_before_clamp', False)
             and not row.get('exclusive_thread_negative_before_clamp', False),
             'observer reported negative exclusive accounting before clamp')
        enriched.append(dict(row, independent_exclusive_wall_ns=ew,
                             independent_exclusive_thread_cpu_ns=ec,
                             wall_minus_thread_cpu_ns_signed=row['wall_ns']-row['thread_cpu_ns'],
                             timer_bracket_CPU_exceeds_wall=row['thread_cpu_ns'] > row['wall_ns']))
    return enriched


def window_accounts(rows, windows):
    """Whole containment only. Never invent partial CPU by proration."""
    results = {}
    for name, limits in windows.items():
        if limits is None:
            selected, boundary, outside = list(rows), [], []
        else:
            start, end = limits
            need(math.isfinite(start) and math.isfinite(end) and end >= start, 'invalid original window')
            selected = [r for r in rows if r['start_ns'] >= start*1e9 and r['end_ns'] <= end*1e9]
            chosen = {sid(r) for r in selected}
            boundary = [r for r in rows if r['start_ns'] < end*1e9 and r['end_ns'] > start*1e9
                        and sid(r) not in chosen]
            outside = [r for r in rows if sid(r) not in chosen and r not in boundary]
        groups, threads = defaultdict(list), defaultdict(list)
        chosen = {sid(r) for r in selected}
        for row in selected:
            groups[row['role'], row['label'].split('.', 1)[0]].append(row)
            parent = (row['role'], row['pid'], row['thread_id'], row['parent_span_id'])
            if parent not in chosen:
                threads[row['role'], row['pid'], row['thread_id']].append(row)
        families = []
        for (role, family), values in sorted(groups.items()):
            families.append(dict(role=role, family=family, count=len(values),
                inclusive_wall_ns_DO_NOT_ADD=sum(r['wall_ns'] for r in values),
                exclusive_wall_ns=sum(r['independent_exclusive_wall_ns'] for r in values),
                exclusive_thread_cpu_ns=sum(r['independent_exclusive_thread_cpu_ns'] for r in values),
                wall_ns_median=statistics.median(r['wall_ns'] for r in values),
                wall_ns_p95=q([r['wall_ns'] for r in values], .95),
                thread_cpu_ns_median=statistics.median(r['thread_cpu_ns'] for r in values),
                CPU_exceeds_wall_bracket_count=sum(r['timer_bracket_CPU_exceeds_wall'] for r in values),
                signed_wall_minus_thread_cpu_ns=sum(r['wall_minus_thread_cpu_ns_signed'] for r in values),
                signed_difference_is_not_blocking_or_lock_wait=True))
        roots = []
        for (role, pid, thread), values in sorted(threads.items()):
            intervals = sorted((r['start_ns'], r['end_ns']) for r in values)
            need(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), 'same-thread root overlap')
            roots.append(dict(role=role, pid=pid, thread_id=thread,
                wall_interval_union_ns=interval_union(intervals),
                root_thread_cpu_ns=sum(r['thread_cpu_ns'] for r in values)))
        results[name] = dict(limits_perf_seconds=limits, fully_contained=len(selected),
                             boundary_not_prorated=len(boundary), outside=len(outside),
                             coarse_families_by_role=families, thread_root_accounts=roots,
                             cross_role_or_parallel_wall_total_NOT_COMPUTED=True)
    return results


def export_metadata_check(rows, metadata, phase, observation, windows):
    expected_roles = {'cpu_real_trace'} if phase == 'cpu' else {'owner', 'supervisor_consumer'}
    need({m['role'] for m in metadata} == expected_roles and len(metadata) == len(expected_roles),
         'missing/duplicate process role export')
    results = []
    for meta in metadata:
        own = [r for r in rows if r['role'] == meta['role'] and r['pid'] == meta['pid']]
        need(meta['enabled'] is observation and not meta['overflow'], 'observer mode/overflow differs')
        need(len(own) == meta['span_count'], 'span export count mismatch')
        need(meta.get('negative_exclusive_wall_before_clamp', 0) == 0
             and meta.get('negative_exclusive_thread_before_clamp', 0) == 0, 'negative exclusive export')
        if not observation:
            need(not own and not meta['families'], 'off control captured protocol spans')
        family = defaultdict(list)
        for row in own:
            family[row['label']].append(row)
        need(set(family) == set(meta['families']), 'family label coverage differs')
        for label, values in family.items():
            declared = meta['families'][label]
            checks = dict(count=len(values), inclusive_wall_ns=sum(r['wall_ns'] for r in values),
                inclusive_thread_cpu_ns=sum(r['thread_cpu_ns'] for r in values),
                exclusive_wall_ns=sum(r['independent_exclusive_wall_ns'] for r in values),
                exclusive_thread_cpu_ns=sum(r['independent_exclusive_thread_cpu_ns'] for r in values),
                exceptions=sum(r['exception'] for r in values))
            need(all(declared[k] == v for k, v in checks.items()), 'family summary changed: ' + label)
        need(meta['export_after_original_entry_return'] is True, 'export/entry scope changed')
        start, end = meta['export_start_ns']/1e9, meta['export_end_ns_before_summary_write']/1e9
        need(end >= start and all(r['end_ns']/1e9 <= start for r in own), 'export precedes completed span')
        if phase == 'nn':
            service_end = windows['origin_to_service_end'][1]
            if meta['role'] == 'owner':
                need(meta['owner_export_precedes_supervisor_service_end'] is True and end <= service_end,
                     'Owner export is not before actual SERVICE_END')
            else:
                need(start >= service_end and meta['owner_export_precedes_supervisor_service_end'] is False,
                     'Supervisor export scope changed')
        results.append(dict(role=meta['role'], pid=meta['pid'], span_count=len(own),
            export_start_perf=start, export_end_before_summary_write_perf=end,
            timer_bracket_CPU_exceeds_wall_count=sum(r['timer_bracket_CPU_exceeds_wall'] for r in own),
            signed_wall_minus_thread_cpu_is_not_a_validated_blocking_estimate=True))
    need(sum(len([r for r in rows if r['role'] == m['role'] and r['pid'] == m['pid']]) for m in metadata)
         == len(rows), 'span rows absent from role exports')
    return results
