"""Values derived from a document's own structure, computed once per document object.

Kept outside the document so that nothing is added to what it serializes. A
document whose segments or sections change length is computed afresh.
"""

_MEMO = {}


def document_memo(document, name, compute):
    key = (id(document), name)
    shape = (len(document.get("segments", [])), len(document.get("sections", [])))
    cached = _MEMO.get(key)
    if cached and cached[0] is document and cached[1] == shape:
        return cached[2]
    value = compute()
    if len(_MEMO) > 512:
        _MEMO.clear()
    _MEMO[key] = (document, shape, value)
    return value
