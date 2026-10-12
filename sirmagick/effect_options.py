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
    parts = [part.strip() for part in value.split('|')]
    if len(parts)!=2 or not all(parts):
        raise ValueError('Metal cover text: BAND NAME | Album title')
    if len(parts[0])>48 or len(parts[1])>100:
        raise ValueError('Band name: at most 48 characters; album title: at most 100 characters.')
    return parts


TEXT_VALIDATORS = {'achievement':achievement_parts,
                   **{name:metal_parts for name in ('metalcover','blackmetalcover','deathmetalcover')}}
