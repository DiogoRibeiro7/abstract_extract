from abstract_extract.models import Article


def test_article_is_immutable_and_typed_container() -> None:
    article = Article(
        title="A title",
        abstract="An abstract",
        publication_date="2026-01-01",
        authors=("Alice", "Bob"),
        doi="10.1000/example",
    )

    assert article.title == "A title"
    assert article.authors == ("Alice", "Bob")
