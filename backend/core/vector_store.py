from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class CodeRetriever:
    def __init__(self):
        self.docs = []
        self.vectorizer = TfidfVectorizer()
        self.matrix = None

    def index(self, files):
        self.docs = files
        self.matrix = self.vectorizer.fit_transform(files)

    def search(self, query, topk=2):
        if not self.docs:
            return []
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix)[0]
        idx = scores.argsort()[-topk:][::-1]
        return [self.docs[i] for i in idx]