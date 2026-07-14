"""
corpus-specific dataclasses.

Section is the canonical legal unit - one section of IPC/BNS/BNSS/CPC, or
one article of the Constitution. Passage is the retrieval unit - one chunk
of a Section's text, fully self-contained (it repeats the section's
metadata) so a search hit never needs a join back to the original Section.

deliberately no Embedding dataclass - a vector is just a list[float], no
need to wrap it in anything.
"""

from dataclasses import dataclass, field


@dataclass
class Section:
    act: str            # "IPC", "BNS", "BNSS", "CPC", "Constitution"
    unit_type: str       # "section" or "article"
    number: str          # "302", "304A", "21" - string to handle alphanumeric
    title: str
    body: str            # full section/article text
    status: str          # "active" or "repealed"
    metadata: dict = field(default_factory=dict)
    # act/parser-specific extras live here: chapter, part, effective_date,
    # replaced_by, etc. - a dict rather than named fields so each parser can
    # attach what's relevant to its act without changing this schema


@dataclass
class Passage:
    act: str
    unit_type: str
    number: str
    title: str
    status: str
    text: str            # this passage's chunk of text (subset of Section.body)
    metadata: dict = field(default_factory=dict)
    # copy of the parent Section's metadata, plus a "part" key describing
    # which structural piece this passage is: "body", "explanation_1",
    # "illustration_2", "exception", etc.