from cineforge.export_report import build_report, report_markdown

def test_report_status_and_fields():
    report=build_report({"valid":True,"width":1280,"height":720,"fps":30,"duration_seconds":5,"video_frames_decoded":150,"audio_frames_decoded":160,"audio_present":True,"file_size_bytes":12345})
    assert report["status"]=="PASS"
    md=report_markdown(report)
    assert "1280 × 720" in md
    assert "Audio present: True" in md

def test_report_includes_warnings():
    report=build_report({"valid":False},warnings=["Optional soundtrack missing"])
    assert report["status"]=="FAIL"
    assert "Optional soundtrack missing" in report_markdown(report)
