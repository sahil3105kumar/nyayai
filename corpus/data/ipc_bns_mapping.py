"""
verified IPC -> BNS section mappings.

ONLY add entries here that are confirmed against the official BNS text
(indiacode.nic.in) or the MHA comparative statement between IPC and BNS.
do NOT guess, interpolate, or assume a pattern - a wrong mapping here makes
citation_checker suggest an incorrect section, which is worse than
suggesting nothing at all.

entries below are the ones already verified in docs/corpus.md. add more
as you verify them - each addition should be checkable against a real
source, not inferred from these.
"""

IPC_TO_BNS = {
    "302": "Section 103 BNS",
    "304A": "Section 106 BNS",
    "307": "Section 109 BNS",
    "376": "Section 64 BNS",
    "420": "Section 318 BNS",
    "498A": "Section 85 BNS",
}