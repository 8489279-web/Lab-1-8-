from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from findex.index import Index


@dataclass
class NumpyPosting:
    doc_ids: NDArray[np.int32]
    tfs: NDArray[np.int32]


@dataclass
class NumpyIndex:
    postings: dict[str, NumpyPosting]
    doc_lengths: NDArray[np.int32]
    num_docs: int
    avg_doc_length: float

    @classmethod
    def from_index(cls, index: Index) -> "NumpyIndex":
        size = max(index.doc_lengths, default=0) + 1
        lengths = np.zeros(size, dtype=np.int32)

        for doc_id, length in index.doc_lengths.items():
            lengths[doc_id] = length

        postings = {
            term: NumpyPosting(
                doc_ids=np.array(
                    [p.doc_id for p in items],
                    dtype=np.int32,
                ),
                tfs=np.array(
                    [p.tf for p in items],
                    dtype=np.int32,
                ),
            )
            for term, items in index.postings.items()
        }

        return cls(
            postings=postings,
            doc_lengths=lengths,
            num_docs=index.num_docs,
            avg_doc_length=index.avg_doc_length,
        )
