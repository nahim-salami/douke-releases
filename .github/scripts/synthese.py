"""Fait lire à Kodo tous les textes de textes.json et écrit un MP3 par texte (nommé par sa clé).

Usage : python synthese.py textes.json voix.onnx dossier-sortie
Les fichiers déjà présents ne sont pas regénérés : seuls les textes nouveaux ou modifiés coûtent du temps.
"""

import json
import sys
from pathlib import Path

import lameenc
from piper import PiperVoice, SynthesisConfig

textes, modele, sortie = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sortie.mkdir(parents=True, exist_ok=True)
voix = PiperVoice.load(str(modele))
# Débit un peu posé pour des apprenants, voix légèrement plus vivante que par défaut.
reglages = SynthesisConfig(length_scale=1.05, noise_scale=0.6, noise_w_scale=0.8, normalize_audio=True)

liste = json.loads(textes.read_text(encoding="utf-8"))
nouveaux = 0
for element in liste:
    fichier = sortie / f"{element['cle']}.mp3"
    if fichier.exists():
        continue
    morceaux = list(voix.synthesize(element["texte"], syn_config=reglages))
    if not morceaux:
        continue
    taux = morceaux[0].sample_rate
    silence = b"\x00\x00" * int(taux * 0.12)
    pcm = silence + b"".join(m.audio_int16_bytes for m in morceaux) + silence
    encodeur = lameenc.Encoder()
    encodeur.set_bit_rate(56)
    encodeur.set_in_sample_rate(taux)
    encodeur.set_channels(1)
    encodeur.set_quality(2)
    fichier.write_bytes(encodeur.encode(pcm) + encodeur.flush())
    nouveaux += 1

print(f"{len(liste)} textes, {nouveaux} fichiers générés")
