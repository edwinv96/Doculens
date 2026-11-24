# RAG and Agentic AI: a practical primer

This original demonstration note explains a small document-grounded assistant.
It is written for this project and is intended for local testing and reuse.

## Retrieval-Augmented Generation

Retrieval-Augmented Generation (RAG) combines a search step with language
generation. Instead of asking a language model to answer from its training
alone, an application first finds passages in a selected knowledge collection.
It then gives those passages to the model as evidence for the current answer.
The retrieved passages can be shown beside the response so a reader can check
where claims came from.

RAG is useful when answers should reflect a changing or private document set.
It does not guarantee correctness: retrieval can miss useful material, a model
can misread a passage, and a source can itself be incomplete. A grounded
assistant should say when its indexed evidence does not answer a question.

## Ingestion, chunks, and embeddings

Document ingestion extracts text and useful metadata from a source. A PDF
loader can keep page numbers with the extracted text. A text splitter then
divides long pages into smaller chunks. Chunks should be large enough to keep a
complete idea together and small enough to find precise evidence. Overlap
between neighboring chunks can retain context near a split boundary.

An embedding model maps each chunk to a vector: a list of numbers representing
some of its semantic meaning. The application stores the vector with the
original text and metadata. A query is embedded with the same model. Vector
similarity can then retrieve passages whose meaning is related even when they
do not repeat the query's exact words.

## Vector search and reranking

A vector database stores embeddings and supports nearest-neighbor search. In
this project, Chroma stores chunk vectors and metadata. A query retrieves a
bounded set of candidate passages from the collection. Metadata such as source
filename and PDF page travels with each passage so citations can point back to
the indexed material.

Retrieval is a ranking problem. The first vector-search results are candidates,
not proof that the answer is present. A reranker can compare the query against
each candidate more directly and reorder the shortlist. Reranking may improve
precision, but it adds model work and cannot recover evidence that was never
retrieved.

## Grounded answer generation

The answer step receives the question and a bounded set of retrieved passages.
Its instruction should treat passage text as untrusted data, answer from that
evidence, and avoid inventing details. The application should preserve the
actual source filename, page number, and excerpt from each retrieved chunk.
Those citations are evidence links, not a numeric confidence score.

When retrieval returns no useful evidence, the application should give a clear
insufficient-evidence response rather than asking the language model to guess.

## Agent workflow and LangGraph

An agent workflow can choose and call tools based on a request. For document
questions, a small flow is enough: receive the question, call the knowledge-base
retrieval tool, inspect its result, and produce a cited response. LangGraph
orchestrates those steps and can persist conversation state through a
checkpointer. A conversation identifier keeps turns in one session associated
with one state record.

Tool events such as “retrieval started”, “documents returned”, and “response
completed” help a user understand observable application activity. They should
report tool execution and status only. Hidden model reasoning, credentials, and
private prompts are not useful execution details and should not be displayed.

## Security and limitations

Uploaded documents and retrieved passages are untrusted input. Instructions
inside a document must not become privileged system instructions. File uploads
need type, name, and size validation. A web-ingestion feature must restrict
requests to public HTTP or HTTPS destinations, handle redirects safely, and
bound its time and response size. API credentials belong in backend
configuration and should never be placed in browser state, chat payloads, or
logs.

RAG quality depends on extraction, chunking, embedding, retrieval, reranking,
and model behavior. A citation shows which passage was retrieved; it does not
prove that every generated sentence follows from it. Evaluation with questions
and expected source names can measure retrieval behavior, but a small demo
dataset is not a broad quality benchmark.
