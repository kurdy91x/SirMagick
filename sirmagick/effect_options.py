"""Validation shared by CLI, mention commands, slash commands, and workers."""


def achievement_parts(value):
    value = ' '.join((value or '').split())
    if len(value)>400:
        raise ValueError('Achievement text must be at most 400 characters.')
    parts = value.split(' ',1)
    if len(parts)<2 or not parts[1]:
        raise ValueError('Achievement needs a title and description: first word = title, remaining words = description.')
    return parts
