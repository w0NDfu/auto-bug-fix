from backend.core.vector_store import CodeRetriever

def retrieve(state, context):
    retriever = CodeRetriever()
    docs = [code for _, code in context.get("suspects", [])]
    retriever.index(docs)
    hits = retriever.search(state.log, topk=2)
    state.context["retrieved"] = hits
    return {"docs": hits}