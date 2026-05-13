from auditmate.utils.debug import DebugRecorder


def test_debug_recorder_writes_artifacts(tmp_path):
    recorder = DebugRecorder(enabled=True, output_dir=tmp_path)

    recorder.save_prompt("agent one", "system", "user")
    recorder.save_response("agent one", "raw")
    recorder.save_json("context.json", {"value": 1})
    recorder.save_repaired_json("agent one", '{"value": 1}')

    run_dirs = list(tmp_path.iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    assert (run_dir / "prompts" / "agent_one.system.txt").read_text(encoding="utf-8") == "system"
    assert (run_dir / "responses" / "agent_one.txt").read_text(encoding="utf-8") == "raw"
    assert (run_dir / "context.json").exists()
    assert (run_dir / "repaired_json" / "agent_one.json").exists()

