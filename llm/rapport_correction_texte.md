# Rapport — Module de correction orthographique (corriger_texte.py)

## Objectif

Corriger automatiquement les fautes d'OCR dans un texte arabe complet
(documents judiciaires), en complément de l'extraction ciblée des 4 champs
principaux du projet.

## Problème rencontré

Testé sur un document réel fortement bruité, le module initial corrigeait
bien les fautes simples (mots coupés, lettres mal reconnues), mais avait
tendance à **halluciner** sur les passages très abîmés :

| Type d'erreur | Exemple observé |
|---|---|
| Date inventée | Une référence vague ("à la date mentionnée ci-dessus") remplacée par une fausse date recopiée d'un autre contexte |
| Mot inventé | Un artefact de tampon transformé en un mot arabe qui n'existe pas, pour "réparer" la grammaire |
| Institutions fusionnées | Deux noms d'institutions réelles et distinctes combinées en une entité fictive |

## Solution mise en place

1. Prompt renforcé avec des règles strictes accompagnées de contre-exemples
   réels (tirés des échecs observés).
2. Garde-fou automatique : toute donnée numérique (date, numéro) absente de
   l'ensemble du document original est détectée dans le texte corrigé, et le
   morceau concerné est alors rejeté au profit de sa version d'origine.

## Résultat

Sur le nouveau test, le garde-fou a intercepté et neutralisé le cas de la
date inventée (et, par la même occasion, la fusion d'institutions présente
dans le même passage). Le cas du mot inventé isolé n'a pas été intercepté :
aucun mécanisme de vérification simple n'existe pour détecter un mot
fabriqué qui n'est pas un nombre.

## Conclusion

Le module est fiable pour une correction légère à modérée et une relecture
rapide, mais ne doit pas remplacer une vérification humaine sur les passages
très abîmés par l'OCR, en particulier pour les noms propres, institutions et
données chiffrées. Cette limite est documentée et assumée : elle illustre la
difficulté générale, déjà rencontrée ailleurs dans le projet, de garantir
qu'un modèle de langage ne « comble » pas silencieusement les trous d'un
texte bruité par du contenu plausible mais inventé.
