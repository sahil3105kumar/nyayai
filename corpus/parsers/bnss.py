from corpus.parsers.base import ChapterSectionParser


class BNSSParser(ChapterSectionParser):
    act = "BNSS"
    default_status = "active"
    effective_date = "2024-07-01"