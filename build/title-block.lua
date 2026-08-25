-- Filtre pandoc : réinjecte le titre / sous-titre / auteur / date du fichier
-- Org (#+TITLE, #+SUBTITLE, #+AUTHOR, #+DATE) en tête du corps du document,
-- afin qu'ils apparaissent dans le notebook (sinon ils restent dans les
-- métadonnées et disparaissent à l'export GFM).

local stringify = pandoc.utils.stringify

function Pandoc(doc)
  local m = doc.meta
  local head = {}

  if m.title then
    table.insert(head, pandoc.Header(1, pandoc.Str(stringify(m.title))))
  end
  if m.subtitle then
    table.insert(head, pandoc.Para({ pandoc.Emph(pandoc.Str(stringify(m.subtitle))) }))
  end

  local credits = {}
  if m.author then table.insert(credits, stringify(m.author)) end
  if m.date   then table.insert(credits, stringify(m.date))   end
  if #credits > 0 then
    table.insert(head, pandoc.Para(pandoc.Str(table.concat(credits, " — "))))
  end

  for _, b in ipairs(doc.blocks) do
    table.insert(head, b)
  end

  return pandoc.Pandoc(head, m)
end
