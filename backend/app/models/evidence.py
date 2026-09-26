"""Visible defect checks. These experimental CLIP margins are not probabilities."""

EVIDENCE_PROMPTS = {
    'whole': ['a photo of a whole uncut onion bulb', 'a photo of a whole red onion with papery skin',
              'a photo of a whole yellow onion with papery skin', 'a photo of a whole white onion'],
    'dry': ['a photo of an onion with a dry brown papery neck',
            'a photo of an onion with dry roots and flaky skin',
            'a photo of a red onion with loose peeling outer skin'],
    'cut': ['a photo of an onion cut in half with a knife showing white concentric rings',
            'a photo of a sliced onion with an exposed flat cut surface',
            'a photo of a halved onion with fresh white flesh'],
    'injury': ['a photo of an onion bulb with deep open splits and cracks in its flesh',
               'a photo of a physically damaged onion with a deep wound',
               'a photo of a bruised onion with crushed tissue'],
    'rot': ['a photo of a rotten onion with brown decomposing flesh',
            'a photo of an onion covered in black and white mold',
            'a photo of an onion with wet slimy decaying tissue'],
    'shoot': ['a photo of an onion bulb with long green shoots growing out of its neck',
              'a photo of a sprouting onion with thick white and green shoots emerging from the bulb',
              'a photo of an onion growing fresh green leaves'],
    'background': ['a photo of a kitchen knife on a table', 'a photo of an empty cloth surface',
                   'a photo of loose dry onion peel without an onion bulb'],
}


def detail_views(image):
    w, h = image.size
    return [image, image.crop((w*.2, h*.2, w*.8, h*.8)),
            image.crop((0, 0, w, h*.65)), image.crop((0, h*.35, w, h)),
            image.crop((0, 0, w*.65, h)), image.crop((w*.35, 0, w, h))]


def decide(prediction, views, config):
    """Require repeated localized evidence; retain raw CLIP scores for audit."""
    votes = {key: sum(s[key] >= config.EVIDENCE_MIN_SIMILARITY and
                     s[key] - max(v for k, v in s.items() if k != key) >= config.EVIDENCE_MARGIN
                     for s in views) for key in ('cut', 'shoot', 'injury', 'rot')}
    whole = views[0]
    background_votes = sum(s['background'] > max(v for k,v in s.items() if k != 'background')
                           + config.BACKGROUND_MARGIN for s in views)
    reject = (whole['background'] > max(v for k,v in whole.items() if k != 'background')
              + config.BACKGROUND_MARGIN and background_votes >= 3)
    original = prediction['predicted_class']
    # Visible decay has priority when an onion is both cut and spoiled. A fresh
    # cut surface is physical damage even when the exposed flesh looks healthy.
    if votes['rot'] >= 2:
        condition, reason = 'rotten', 'Repeated visual evidence of mold or decomposing tissue.'
    elif votes['cut'] >= 2:
        condition, reason = 'damaged', 'Cut-face evidence: sliced or halved flesh is physical damage, even when fresh.'
    elif votes['shoot'] >= 2:
        condition, reason = 'sprouted', 'Growing-shoot evidence exceeds dry-neck and dry-root descriptions in multiple views.'
    elif votes['injury'] >= 2:
        condition, reason = 'damaged', 'Repeated evidence of physical injury; no repeated decay evidence.'
    elif original == 'rotten':
        condition, reason = original, 'Overall appearance suggests decay; close-up evidence is weak and needs review.'
    else:
        condition, reason = 'grade_a', 'Whole-bulb appearance; no defect confirmed by the close-up checks.'
    conflict = condition != original
    weak = max(votes.values()) < 2
    prediction.update(condition=condition, confidence=prediction['scores'][condition],
                      needs_review=prediction['scores'][condition] < config.CLIP_CONFIDENCE_THRESHOLD or conflict or weak,
                      decision_reason=reason, visible_evidence={'votes': votes, 'views': len(views),
                      'whole_crop_similarities': whole}, exclude_from_count=reject)
    return prediction
