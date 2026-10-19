from transcriber.formats import to_srt, to_txt

SEGS = [{"start": 0, "end": 1.5, "text": "a"}, {"start": 3661.25, "end": 3662, "text": "b"}]


def test_srt():
    assert to_srt(SEGS) == "1\n00:00:00,000 --> 00:00:01,500\na\n\n2\n01:01:01,250 --> 01:01:02,000\nb\n"


def test_txt():
    assert to_txt(SEGS) == "[00:00:00] a\n[01:01:01] b\n"
    assert to_txt(SEGS, timestamps=False) == "a\nb\n"
