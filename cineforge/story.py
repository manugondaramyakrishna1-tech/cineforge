"""Rule-based cinematic story expansion helpers; no external API dependency."""
def expand_story(prompt, scene_count=4, style='cinematic', character=''):
    prompt=prompt.strip()
    if not prompt: return prompt
    return (f'Create a coherent {style} short film from this premise: {prompt}. '
            f'Use {scene_count} story beats with a clear opening, escalation, meaningful turning point and resolution. '
            f'Keep visuals consistent, show actions rather than abstract descriptions, avoid abrupt jumps, '
            f'and maintain character continuity: {character}. Each scene should have a distinct cinematic composition, '
            f'believable motion, lighting and atmosphere. Avoid on-screen text and watermarks.')
