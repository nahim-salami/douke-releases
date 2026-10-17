"""Essai d'écoute : Kodo lu par Chatterbox avec la voix de personnes du corpus African Accented French.

Deux étapes, lancées par le workflow « Essai de voix (Chatterbox) » :

  python essai_chatterbox.py references corpus/ sortie/ 8
      Range les enregistrements du corpus par personne, garde celles dont le son est le plus propre
      et écrit pour chacune un extrait de référence (sortie/<id>/reference.wav et .mp3), plus
      sortie/locuteurs.json.

  python essai_chatterbox.py voix sortie/<id>/reference.wav phrases.json sortie/<id>/
      Fait lire les phrases par Chatterbox Multilingual V3 avec cette voix : sortie/<id>/<n>.mp3.
"""

import collections
import json
import re
import sys
from pathlib import Path

import lameenc
import numpy as np


def mp3(audio: np.ndarray, taux: int, fichier: Path) -> None:
    pic = float(np.max(np.abs(audio))) or 1.0
    pcm = (audio / pic * 0.9 * 32767).astype(np.int16)
    silence = np.zeros(int(taux * 0.12), dtype=np.int16)
    encodeur = lameenc.Encoder()
    encodeur.set_bit_rate(64)
    encodeur.set_in_sample_rate(taux)
    encodeur.set_channels(1)
    encodeur.set_quality(2)
    donnees = np.concatenate([silence, pcm, silence]).tobytes()
    fichier.write_bytes(encodeur.encode(donnees) + encodeur.flush())


# --- Étape 1 : choisir les voix de référence ---------------------------------------------------


def personne(chemin: Path, corpus: Path) -> str:
    """Identifiant de la personne qui parle : son dossier, ou le préfixe du nom de fichier
    quand plusieurs personnes partagent un dossier (« dossier/F12_003.wav » → « dossier/F12 »)."""
    dossier = chemin.parent.relative_to(corpus).as_posix()
    prefixe = re.sub(r"[_-]?\d+$", "", chemin.stem)
    return f"{dossier}/{prefixe}" if prefixe and prefixe != chemin.stem else dossier


def proprete(audio: np.ndarray, taux: int) -> float:
    """Écart en dB entre la parole (trames fortes) et le bruit de fond (trames faibles)."""
    trame = int(taux * 0.025)
    n = len(audio) // trame
    if n < 20:
        return 0.0
    energie = (audio[: n * trame].reshape(n, trame) ** 2).mean(axis=1) + 1e-10
    sature = float(np.mean(np.abs(audio) > 0.99))
    return 10 * np.log10(np.percentile(energie, 90) / np.percentile(energie, 10)) - 200 * sature


def references(corpus: Path, sortie: Path, nombre: int) -> None:
    import librosa
    import soundfile as sf

    fichiers = sorted(corpus.rglob("*.wav"))
    groupes = collections.defaultdict(list)
    for f in fichiers:
        groupes[personne(f, corpus)].append(f)
    # Un « groupe » de centaines de fichiers est un dossier commun à plusieurs personnes : on l'écarte.
    groupes = {k: v for k, v in groupes.items() if 4 <= len(v) <= 400}
    print(f"{len(fichiers)} fichiers audio, {len(groupes)} personnes")

    notes = []
    for cle, liste in groupes.items():
        mesures = []
        for f in liste[:: max(1, len(liste) // 12)][:12]:
            try:
                audio, taux = sf.read(f, dtype="float32", always_2d=True)
            except Exception:
                continue
            audio = audio.mean(axis=1)
            mesures.append((proprete(audio, taux), f, len(audio) / taux))
        if not mesures:
            continue
        duree = sum(d for _, _, d in mesures) * len(liste) / len(mesures)
        if duree < 20:
            continue
        notes.append((float(np.median([m for m, _, _ in mesures])), cle, duree, liste))
    notes.sort(reverse=True)

    # Les plus propres, sans prendre plus de trois personnes dans la même partie du corpus.
    choisis, par_partie = [], collections.Counter()
    for note, cle, duree, liste in notes:
        partie = cle.split("/")[0]
        if par_partie[partie] >= 3:
            continue
        par_partie[partie] += 1
        choisis.append((note, cle, duree, liste))
        if len(choisis) == nombre:
            break

    locuteurs = []
    for i, (note, cle, duree, liste) in enumerate(choisis, 1):
        ident = f"voix{i}"
        dossier = sortie / ident
        dossier.mkdir(parents=True, exist_ok=True)
        # Extrait de référence : ses enregistrements les plus propres, sans les silences, mis bout à bout
        # jusqu'à environ 12 secondes.
        classes = sorted(liste, key=lambda f: -proprete(librosa.load(f, sr=16000)[0], 16000))[:15]
        morceaux, total = [], 0.0
        for f in classes:
            audio, _ = librosa.load(f, sr=24000, mono=True)
            audio, _ = librosa.effects.trim(audio, top_db=30)
            if len(audio) < 24000:
                continue
            morceaux += [audio, np.zeros(int(24000 * 0.25), dtype=np.float32)]
            total += len(audio) / 24000
            if total >= 12:
                break
        if not morceaux:
            continue
        extrait = np.concatenate(morceaux)
        extrait = extrait / (np.max(np.abs(extrait)) or 1.0) * 0.9
        sf.write(dossier / "reference.wav", extrait, 24000, subtype="PCM_16")
        mp3(extrait, 24000, dossier / "reference.mp3")
        locuteurs.append({"id": ident, "partie": cle.split("/")[0], "duree": round(duree), "proprete": round(note, 1)})
        print(f"{ident} : {cle} ({duree / 60:.1f} min, {note:.1f} dB)")

    (sortie / "locuteurs.json").write_text(json.dumps(locuteurs, ensure_ascii=False, indent=1), encoding="utf-8")


# --- Étape 2 : faire lire les phrases --------------------------------------------------------


def voix(reference: Path, phrases: Path, sortie: Path) -> None:
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    torch.set_num_threads(max(1, torch.get_num_threads()))
    modele = ChatterboxMultilingualTTS.from_pretrained(device="cpu", t3_model="v3")
    sortie.mkdir(parents=True, exist_ok=True)
    for i, texte in enumerate(json.loads(phrases.read_text(encoding="utf-8")), 1):
        with torch.inference_mode():
            wav = modele.generate(texte, language_id="fr", audio_prompt_path=str(reference))
        mp3(wav.squeeze(0).cpu().numpy(), modele.sr, sortie / f"{i}.mp3")
        print(f"phrase {i} lue")


if __name__ == "__main__":
    if sys.argv[1] == "references":
        references(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]))
    else:
        voix(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
