"""Validation shared by CLI, mention commands, slash commands, and workers."""


def achievement_parts(value):
    value = ' '.join((value or '').split())
    if len(value)>400:
        raise ValueError('Achievement text must be at most 400 characters.')
    parts = value.split(' ',1)
    if len(parts)<2 or not parts[1]:
        raise ValueError('Achievement needs a title and description: first word = title, remaining words = description.')
    return parts


def metal_parts(value):
    value = ' '.join((value or '').split())
    parts = value.split(' ', 1)
    if len(parts) != 2 or not all(parts):
        raise ValueError('Metal cover needs a title and subtitle: first word = title, remaining words = subtitle.')
    if '|' in value:
        raise ValueError('Use spaces instead of a pipe: first word = title, remaining words = subtitle.')
    if len(parts[0])>48 or len(parts[1])>100:
        raise ValueError('Title: at most 48 characters; subtitle: at most 100 characters.')
    return parts


TEXT_VALIDATORS = {'achievement':achievement_parts,
                   **{name:metal_parts for name in ('metalcover','blackmetalcover','deathmetalcover')}}
