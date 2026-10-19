from transcriber.benchmark import wer


def test_wer():
    assert wer("the cat sat", "the cat sat") == 0
    assert wer("the cat sat", "the cat") == 1 / 3
    assert wer("Hello, world!", "hello world") == 0
    assert wer("שלום עולם", "שלום עולם יפה") == 0.5
