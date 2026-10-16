#!/usr/bin/env bash
# Lance une commande sans afficher sa sortie dans le journal public.
#
# Les journaux de ce dépôt sont publics : la sortie d'un test ou d'une compilation
# peut contenir du code source. Elle est donc écrite dans $RUNNER_TEMP/journaux/,
# chiffrée en fin de job (action « journaux ») et lisible seulement avec la clé privée.
# Le journal public ne montre que le libellé, la durée et le résultat.
#
# Usage : discret.sh "Libellé" commande [arguments…]
# La commande elle-même n'est jamais écrite, ni en clair ni dans le journal chiffré,
# pour ne pas y laisser de mot de passe passé en argument.

set -uo pipefail

libelle="$1"
shift

dossier="${RUNNER_TEMP:-/tmp}/journaux"
mkdir -p "$dossier"
numero=$(( $(find "$dossier" -maxdepth 1 -name '*.log' | wc -l) + 1 ))
nom=$(printf '%s' "$libelle" | tr -c 'A-Za-z0-9' '-' | tr -s '-' | sed 's/^-//; s/-$//')
fichier="$dossier/$(printf '%02d' "$numero")-${nom}.log"

resume="${GITHUB_STEP_SUMMARY:-/dev/null}"
if [ ! -f "$dossier/.entete" ]; then
  {
    echo "| Étape | Résultat | Durée |"
    echo "|---|---|---|"
  } >> "$resume"
  touch "$dossier/.entete"
fi

debut=$(date +%s)
echo "# $libelle — $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$fichier"
"$@" >> "$fichier" 2>&1
code=$?
duree=$(( $(date +%s) - debut ))

if [ "$code" -eq 0 ]; then
  echo "✓ $libelle (${duree} s)"
  echo "| $libelle | ✓ | ${duree} s |" >> "$resume"
else
  echo "::error title=${libelle}::Échec (code ${code}). Le journal complet est dans l'artefact chiffré « journaux-chiffres-… »."
  echo "| $libelle | ✗ code ${code} | ${duree} s |" >> "$resume"
fi
exit "$code"
