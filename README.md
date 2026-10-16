# Douke — versions publiées

Douke est une application d’apprentissage du numérique en leçons de 5 minutes, pensée pour l’Afrique de l’Ouest.

Ce dépôt sert uniquement à **publier les versions** de l’application. Le code source est privé.

## Télécharger

Les versions sont dans l’onglet [Releases](https://github.com/nahim-salami/douke-releases/releases). Chaque release indique sa date, ses nouveautés et les fichiers à télécharger (APK Android, version web).

## Signaler un problème

Ouvre une [issue](https://github.com/nahim-salami/douke-releases/issues) en indiquant la version, ton téléphone et ce qui s’est passé.

## Intégration continue

Les workflows de ce dépôt vérifient, compilent et publient Douke à partir de sa source privée, récupérée en lecture seule.

| Workflow | Rôle |
|---|---|
| `Vérifier` | Contenu pédagogique, lint, types et tests, à chaque modification de la source |
| `Compiler` | Compilation Android et web, sans rien publier |
| `Publier une version` | Vérification, compilation, puis release (brouillon, pré-version ou version) |

Ces journaux sont publics, alors la sortie des commandes n’y apparaît pas : seuls le nom de chaque étape, sa durée et son résultat sont affichés. Le détail est chiffré et lisible uniquement par l’équipe. Les contributions externes ne déclenchent aucun workflow.
