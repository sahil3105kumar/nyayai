from corpus.parsers.base import ChapterSectionParser


class CPCParser(ChapterSectionParser):
    act = "CPC"
    default_status = "active"
    effective_date = "1908-01-01"