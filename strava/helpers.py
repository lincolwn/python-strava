class BatchIterator:
    default_per_page = 100

    def __init__(self, fetcher, limit=None):
        self.fetcher = fetcher
        self.page = 1
        self.limit = limit
        self.fetched_count = 0

        if self.limit and self.limit < self.default_per_page:
            self.per_page = self.limit
        else:
            self.per_page = self.default_per_page

        self._finished = False
        self._fetch_page()

    def _fetch_page(self):
        page_size = None

        if self.limit:
            missing = self.limit - self.fetched_count
            if missing < self.per_page:
                page_size = missing

        page_size = page_size or self.per_page

        result = self.fetcher(page=self.page, per_page=page_size)
        self.page += 1
        self.fetched_count += len(result)

        if len(result) < self.per_page or self.fetched_count == self.limit:
            self._finished = True

        return result

    def __iter__(self):
        while not self._finished:
            yield from self._fetch_page()
