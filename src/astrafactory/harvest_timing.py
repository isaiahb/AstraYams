"""Elapsed simulation time, with partial skills kept separate from full harvests.

This is evaluation telemetry, not a change to rewards or acceptance criteria.
Rows describe intervals ending at sim_s; concurrent arms share one cell clock.
"""
import math


def summarize_timing(trace, result, start_time_s=0.0):
    previous = float(start_time_s)
    if not math.isfinite(previous):
        raise ValueError('Non-finite start time')
    phases = []
    invalid = bool(result.get('invalid', False))
    first_retention = first_placement = None
    for row in trace:
        end = float(row['sim_s'])
        if not math.isfinite(end) or end <= previous:
            raise ValueError('Trace times must be finite and strictly increasing')
        phase = row.get('coordinator_phase', row.get('stage', row.get('phase', 'unknown')))
        if not phases or phases[-1]['phase'] != phase:
            phases.append(dict(phase=phase, start_s=previous, end_s=end))
        else:
            phases[-1]['end_s'] = end
        invalid = invalid or bool(row.get('invalid', False))
        if first_retention is None and row.get('net_hold_steps', 0) >= 25:
            first_retention = end - start_time_s
        if first_placement is None and row.get('placement_success', False):
            first_placement = end - start_time_s
        previous = end
    for phase in phases:
        phase['duration_s'] = phase['end_s'] - phase['start_s']
    elapsed = previous - start_time_s
    full_success = bool(trace and result.get('full_harvest_success', False)
                        and result.get('placement_success', False) and not invalid
                        and first_placement is not None)
    # A pre-cut/reset-start placement and a support-only is_success cannot count.
    event = result.get('cut_event') or {}
    cut_time = event.get('time_s')
    cut_time = (float(cut_time) - start_time_s
                if cut_time is not None and start_time_s < float(cut_time) <= previous
                else None)
    return dict(
        clock='elapsed simulation seconds; both arms share the same clock',
        elapsed_s=elapsed, phases=phases, cut_s=cut_time,
        first_sustained_net_retention_s=first_retention,
        first_settled_placement_s=first_placement,
        accepted_harvest_to_placement_s=first_placement if full_success else None,
        full_harvest_completed=full_success, any_invalid=invalid,
        operational_good_fruit_per_hour=None,
        throughput_scope='Not measured: requires repeated complete cycles, ready-for-next, '
                         'failures/recovery, target selection and plant/basket handling time. '
                         'Never sum independently reset subtasks or double the rate for two arms.',
    )
