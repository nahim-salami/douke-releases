"""Fait lire à Douke une part des textes de textes.json avec Chatterbox Multilingual V3, dans la voix
d'un extrait de référence, et écrit un MP3 par texte (nommé par sa clé).

Usage : python synthese_chatterbox.py textes.json reference.wav sortie/ part nombre-de-parts existants.txt minutes
  part, nombre-de-parts : le texte n° i est lu par la part i % nombre-de-parts (les premiers textes,
                          les plus entendus, sont ainsi lus en premier par toutes les parts) ;
  existants.txt         : clés déjà publiées, à ne pas relire ;
  minutes               : temps de calcul alloué ; au-delà, le script s'arrête proprement et une
                          prochaine exécution reprendra les textes manquants.
"""

import json
import re
import sys
import time
import zlib
from pathlib import Path

import lameenc
import librosa
import numpy as np
import torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

textes, reference, sortie = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
part, parts = int(sys.argv[4]), int(sys.argv[5])
existants = set(Path(sys.argv[6]).read_text(encoding="utf-8").split())
fin = time.monotonic() + float(sys.argv[7]) * 60
sortie.mkdir(parents=True, exist_ok=True)

modele = ChatterboxMultilingualTTS.from_pretrained(device="cpu", t3_model="v3")
modele.prepare_conditionals(str(reference))
taux = modele.sr


def morceaux(texte: str) -> list[str]:
    """Les textes longs sont lus phrase par phrase : la voix reste stable et rien n'est coupé."""
    if len(texte) <= 220:
        return [texte]
    groupes, courant = [], ""
    for phrase in re.split(r"(?<=[.!?…])\s+", texte):
        if courant and len(courant) + len(phrase) > 220:
            groupes.append(courant)
            courant = phrase
        else:
            courant = f"{courant} {phrase}".strip()
    return groupes + [courant] if courant else groupes


def mp3(audio: np.ndarray, fichier: Path) -> None:
    audio, _ = librosa.effects.trim(audio, top_db=45)
    pic = float(np.max(np.abs(audio))) or 1.0
    silence = np.zeros(int(taux * 0.12), dtype=np.int16)
    pcm = np.concatenate([silence, (audio / pic * 0.9 * 32767).astype(np.int16), silence])
    encodeur = lameenc.Encoder()
    encodeur.set_bit_rate(48)
    encodeur.set_in_sample_rate(taux)
    encodeur.set_channels(1)
    encodeur.set_quality(2)
    fichier.write_bytes(encodeur.encode(pcm.tobytes()) + encodeur.flush())


liste = json.loads(textes.read_text(encoding="utf-8"))
a_lire = [e for i, e in enumerate(liste) if i % parts == part and e["cle"] not in existants]
lus = 0
for element in a_lire:
    if time.monotonic() > fin:
        break
    # Même texte, même lecture : la graine dépend du texte.
    torch.manual_seed(zlib.crc32(element["cle"].encode()))
    pause = np.zeros(int(taux * 0.25), dtype=np.float32)
    audio = []
    try:
        for bout in morceaux(element["texte"]):
            with torch.inference_mode():
                wav = modele.generate(bout, language_id="fr")
            audio += [wav.squeeze(0).cpu().numpy().astype(np.float32), pause]
    except Exception as erreur:  # un texte raté ne doit pas arrêter les autres
        print(f"texte ignoré : {type(erreur).__name__}")
        continue
    mp3(np.concatenate(audio[:-1]), sortie / f"{element['cle']}.mp3")
    lus += 1

print(f"part {part + 1}/{parts} : {lus} lus sur {len(a_lire)} à lire")
