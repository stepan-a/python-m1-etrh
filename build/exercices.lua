-- Filtre pandoc : traitement des blocs de code du cours.
--
-- Deux en-têtes Org sont reconnus.
--
-- 1. « :corrige t » — bascule énoncé / corrigé.
--
--    Dans la source, la solution d'un exercice est écrite juste sous
--    l'énoncé, dans un bloc marqué :
--
--      *Exercice 4.2* — Salaire moyen par diplôme.
--
--      #+BEGIN_SRC python :corrige t
--      df.groupby("diplome")["salaire"].mean()
--      #+END_SRC
--
--    pandoc conserve cet en-tête comme attribut du CodeBlock, ce qui permet
--    de produire deux notebooks depuis une source unique :
--
--      make            -> cellule d'amorce vide   (notebook de l'étudiant)
--      CORRIGE=1 make  -> cellule remplie         (notebook du corrigé)
--
-- 2. « :skip t » — cellule à ne pas exécuter automatiquement.
--
--    Les cellules qui appellent input() bloquent indéfiniment sous
--    « jupyter nbconvert --execute », donc sous « make check ». On leur
--    attache le tag jupyter « skip-execution », que nbclient respecte :
--    l'étudiant peut les exécuter dans son navigateur, la CI les saute.
--
--    Le writer GFM de pandoc ne sait pas rendre les attributs d'un bloc de
--    code — il émet « ```python » et rien d'autre. On écrit donc la clôture
--    à la main dans un RawBlock markdown, forme que jupytext relit et
--    convertit en métadonnées de cellule.
--
-- Les blocs d'exemple ordinaires (#+BEGIN_SRC python sans en-tête) ne
-- portent aucun de ces attributs : le filtre les laisse passer intacts.

local corrige = (os.getenv("CORRIGE") or "") ~= ""

-- Amorce déposée dans la cellule laissée à l'étudiant. Une cellule vraiment
-- vide serait indistinguable d'une cellule d'exemple non exécutée.
local AMORCE = "# À toi de jouer — écris ta réponse ici, puis exécute la cellule."

--- Émet une cellule de code portant le tag « skip-execution ».
local function bloc_non_execute(texte)
  return pandoc.RawBlock(
    "markdown",
    '```python tags=["skip-execution"]\n' .. texte:gsub("\n+$", "") .. "\n```")
end

function CodeBlock(cb)
  local skip = cb.attributes["skip"] ~= nil
  local exercice = cb.attributes["corrige"] ~= nil

  if not skip and not exercice then
    return nil
  end

  local texte = cb.text
  if exercice and not corrige then
    texte = AMORCE
  end

  if skip then
    return bloc_non_execute(texte)
  end

  -- Les attributs reconnus sont retirés : sans cela pandoc les émettrait
  -- dans le Markdown et jupytext les recopierait dans le notebook.
  local attrs = cb.attributes
  attrs["corrige"] = nil
  attrs["skip"] = nil
  return pandoc.CodeBlock(texte, pandoc.Attr(cb.identifier, cb.classes, attrs))
end
