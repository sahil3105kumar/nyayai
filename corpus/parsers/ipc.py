from corpus.parsers.base import ChapterSectionParser
from corpus.data.ipc_bns_mapping import IPC_TO_BNS


class IPCParser(ChapterSectionParser):
    act = "IPC"
    default_status = "repealed"  # BNS replaced the IPC in full, effective 2024-07-01
    effective_date = "1860-01-01"

    def extra_metadata(self, number: str) -> dict:
        if number in IPC_TO_BNS:
            return {"replaced_by": IPC_TO_BNS[number]}
        return {}