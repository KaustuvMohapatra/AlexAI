from textblob import TextBlob
def analyze_sentiment(text: str) -> dict:
    blob = TextBlob(text)
    sentiment = {
        "polarity": round(blob.sentiment.polarity, 2),
        "subjectivity": round(blob.sentiment.subjectivity, 2)
    }
    return sentiment