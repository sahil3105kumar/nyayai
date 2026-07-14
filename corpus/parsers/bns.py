from corpus.parsers.base import ChapterSectionParser


class BNSParser(ChapterSectionParser):
    act = "BNS"
    default_status = "active"
    effective_date = "2024-07-01"