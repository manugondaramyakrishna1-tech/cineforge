import json
import os
from pathlib import Path
import streamlit as st

from cineforge.comfy import ComfyUI
from cineforge.hosted_video import ReplicateVideo, validate_workflow as validate_hosted_workflow
from cineforge.director import plan, export_script, CAMERA_PRESETS, LOOK_PRESETS
from cineforge.voice import synthesize
from cineforge.assembly import assemble
from cineforge.audio_mix import mix_timeline
from cineforge.subtitles import create_srt
from cineforge.story import expand_story
from cineforge.profiles import PRESETS, get_preset
from cineforge.creator import DURATIONS
from cineforge.health import check_server, format_queue
from cineforge.checkpoint import save_checkpoint, load_checkpoint
from cineforge.scene_review import review_scenes
from cineforge.timeline import move_item, validate_timeline
from cineforge.visual_timeline import build_visual_timeline
from cineforge.project_store import save_project, load_project, list_projects
from cineforge.project_database import save_project_record, load_project_record, list_project_records
from cineforge.project_state import apply_project_settings, project_settings_payload, reorder_scenes_by_titles
from cineforge.preview import preview_rows, to_csv
from cineforge.studio import scene_cards
from cineforge.render_status import read_registry, set_scene_status
from cineforge.replacements import record_replacement, apply_replacements
from cineforge.scene_assets import register_scene_asset, set_active_scene_video, resolve_scene_videos, scene_asset_inventory
from cineforge.scene_recovery import SceneRecoveryStore
from cineforge.assembly_checks import validate_clips, assembly_summary, validate_final_video
from cineforge.export_report import build_report, save_report, report_markdown
from cineforge.voice_studio import VOICE_PROFILES, narration_text
from cineforge.sound_studio import validate_audio_tracks, mix_settings
from cineforge.export_presets import PRESETS, get_preset
from cineforge.release_audit import audit_repo, save_audit


st.set_page_config(page_title="CineForge AI Studio", page_icon="🎬", layout="centered")
st.title("🎬 CineForge AI — Production Studio")
st.caption("Storyboard, scene review, rendering, narration, soundtrack and final MP4. No FFmpeg executable is called.")

st.header("🎬 Create a Movie")
prompt = st.text_area(
    "Describe your movie idea",
    st.session_state.get("prompt", "A traveler discovers a glowing hidden city deep in the mountains"),
    height=160,
    key="prompt",
    help="Write the story or scene idea you want CineForge to turn into a cinematic storyboard."
)
st.caption("Step 1: create and review your storyboard. Step 2: generate actual scene footage using hosted AI video generation or your own ComfyUI server.")
st.markdown("**Ready to render actual video?** Choose Hosted (Replicate) or ComfyUI in the sidebar, then jump to [Generate final movie ↓](#generate-final-movie).")

# Early defaults prevent engine-status UI from referencing sidebar inputs before they exist.
server = ""
workflow_file = None

st.markdown("### Quick video settings")
quick_cols = st.columns(2)
with quick_cols[0]:
    st.selectbox("Format", ["Vertical 9:16", "Landscape 16:9", "Square 1:1"], key="quick_format")
with quick_cols[1]:
    st.selectbox("Length", ["15 seconds", "30 seconds", "60 seconds"], key="quick_length")
st.caption("Storyboard creation does not render footage. Actual AI video generation is a separate step after scene review.")

with st.expander("Release readiness audit"):
    audit = audit_repo(".")
    st.json(audit)
    audit_path = save_audit(audit, Path("outputs/cineforge_release_audit.json"))
    st.download_button("Download release audit JSON", audit_path.read_bytes(),
                      file_name="cineforge_release_audit.json", mime="application/json")

from cineforge.startup_check import run_checks
with st.expander("Startup diagnostics"):
    st.json(run_checks())

with st.expander("Self-hosted video model diagnostics", expanded=True):
    from cineforge.local_video import runtime_status
    local_state = runtime_status()
    st.json(local_state)
    try:
        from cineforge.local_video import gpu_memory_status, cleanup_gpu_memory
        memory_status = gpu_memory_status()
        if memory_status.get("available"):
            st.metric("GPU", memory_status.get("device", "CUDA"))
            m1, m2, m3 = st.columns(3)
            m1.metric("Free VRAM", f'{memory_status.get("free_bytes", 0) / 1024**3:.2f} GiB')
            m2.metric("Allocated", f'{memory_status.get("allocated_bytes", 0) / 1024**3:.2f} GiB')
            m3.metric("Reserved", f'{memory_status.get("reserved_bytes", 0) / 1024**3:.2f} GiB')
        else:
            st.caption("GPU memory telemetry unavailable: " + str(memory_status.get("error", memory_status.get("device", "no CUDA device"))))
        if st.button("Release unused GPU memory", key="cleanup_gpu_memory"):
            st.json(cleanup_gpu_memory())
    except Exception as memory_ui_error:
        st.caption(f"GPU telemetry could not be loaded: {memory_ui_error}")
    if local_state.get("ready"):
        st.success("GPU/accelerator detected. Local model inference can be configured on this machine.")
    else:
        st.warning("Local video generation is unavailable in this environment. CineForge can still build storyboards and manage project assets; actual local model rendering requires supported GPU hardware.")
    st.caption("This diagnostic does not download model weights or call an external video-generation service.")
    if st.button("Run detailed GPU diagnostics", key="detailed_gpu_check"):
        try:
            from cineforge.gpu_setup import check
            diagnostic_report = check()
            st.json(diagnostic_report)
            st.subheader("nvidia-smi output")
            smi_output = diagnostic_report.get("nvidia_smi", "No output")
            st.code(smi_output, language="text")
            st.subheader("Detected device")
            st.write(diagnostic_report.get("device", diagnostic_report.get("gpu_details", "Device information unavailable")))
            st.caption("If nvidia-smi reports that it cannot communicate with the NVIDIA driver or is not found, this runtime may not expose NVIDIA GPU hardware.")
            if diagnostic_report.get("nvidia_smi_status") or "not installed" in str(smi_output).lower() or "not available on path" in str(smi_output).lower():
                st.error("NVIDIA GPU tools are not detected in this runtime.")
                st.markdown("**Platform-specific GPU setup**")
                detected_platform = str(diagnostic_report.get("platform", "")).lower()
                if "windows" in detected_platform:
                    st.markdown("**Windows:** install the NVIDIA driver, restart, then open a fresh terminal and rerun this check.")
                    st.markdown("[Official NVIDIA driver downloads](https://www.nvidia.com/en-us/drivers/)
                elif "linux" in detected_platform:
                    st.markdown("**Linux:** use the distribution-recommended driver installer and restart. Ubuntu documents the Additional Drivers app and `ubuntu-drivers` method.")
                    st.markdown("[Ubuntu driver guidance](https://ubuntu.com/desktop/docs/en/latest/how-to/graphics/install-nvidia-drivers/)")
                elif "darwin" in detected_platform or "mac" in detected_platform:
                    st.markdown("**macOS:** CUDA-based NVIDIA inference is generally not supported on modern macOS systems.")
                else:
                    st.markdown("**Other or container runtime:** verify GPU hardware and driver availability on the host and ensure the runtime exposes the GPU.")
                st.markdown("**Verification commands**")
                st.code('nvidia-smi\\npython -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.device_count())"', language="bash")
                st.info("CineForge cannot install system-level GPU drivers or grant GPU access from inside the app. This panel reports and guides setup; it does not fake GPU availability.")
        except Exception as diagnostic_error:
            st.error(f"GPU diagnostic failed: {diagnostic_error}")

    with st.expander("GPU / CUDA troubleshooting", expanded=not local_state.get("ready", False)):
        st.markdown("**If PyTorch says no CUDA device detected:**")
        st.markdown("1. Run \`python -m cineforge.gpu_setup\` in the project terminal.\n2. Run \`nvidia-smi\` to verify the NVIDIA driver and GPU are visible.\n3. Run the PyTorch check below.\n4. If a GPU is visible to the driver but CUDA is false, install a matching CUDA-enabled PyTorch build from [the official selector](https://pytorch.org/get-started/locally/).\n5. Restart the Python environment and rerun the diagnostic.")
        st.code("python -c \\\"import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.device_count())\\\"")
        st.warning("A CUDA package cannot attach a GPU to a CPU-only host. GitHub Codespaces or another hosted runtime may not expose an NVIDIA GPU. Use a GPU-enabled machine/runtime; installing drivers may require system administrator access.")
        st.markdown("**Local inference dependencies:** \`pip install -r requirements-local-video.txt\` (only after GPU access and compatible CUDA PyTorch are confirmed).")

    st.markdown("#### Local model clip test")
    local_test_prompt = st.text_area("Test prompt", "A cinematic aerial view of a misty mountain valley at sunrise", key="local_test_prompt")
    local_test_frames = st.slider("Test clip frames", 9, 49, 17, step=4, key="local_test_frames")
    local_test_steps = st.slider("Inference steps", 1, 30, 10, key="local_test_steps")
    if st.button("Generate local test clip", disabled=not local_state.get("ready", False)):
        try:
            from cineforge.local_video import LocalCogVideoX
            local_engine = LocalCogVideoX()
            local_request = {"prompt": local_test_prompt, "num_frames": local_test_frames, "steps": local_test_steps}
            local_job = local_engine.submit(local_request)
            local_status = st.empty()
            local_engine.wait_for_outputs(local_job, local_status)
            local_test_folder = Path("outputs/local_model_test")
            local_test_folder.mkdir(parents=True, exist_ok=True)
            local_videos = local_engine.download_videos({"frames": local_test_frames}, local_test_folder)
            if local_videos:
                st.video(str(local_videos[0]))
                st.download_button("Download local test clip", local_videos[0].read_bytes(), file_name="local_model_test.mp4", mime="video/mp4")
        except Exception as local_test_error:
            st.error(f"Local test render failed: {local_test_error}")
    if not local_state.get("ready", False):
        st.caption("Test button is disabled until a supported GPU/accelerator is detected.")

with st.sidebar:
    st.subheader("Local AI video generation")
    from cineforge.local_video import runtime_status
    local_state = runtime_status()
    st.json(local_state)
    if not local_state.get("ready"):
        st.warning("Local generation requires a supported GPU. This environment is not ready.")
    else:
        st.success("Local model rendering is available on this machine.")
    server = ""
    provider_mode = "Local (CogVideoX)"
    workflow_file = None
    character = st.text_area("Character continuity", st.session_state.get("character", "A traveler in a weathered dark-green cloak, leather backpack and boots; same appearance throughout"), height=90, key="character")
    negative = st.text_area("Negative prompt", "blurry, flicker, distorted anatomy, text, watermark")
    duration_choice = st.selectbox("Movie length", list(DURATIONS), key="duration_choice")
    scene_count = st.slider("Number of scenes", 2, 6, 4, key="scene_count")
    style = st.selectbox("Visual style", ["cinematic photorealism", "stylized fantasy film", "science fiction cinema", "documentary cinematic", "animated feature-film look"], key="visual_style")
    profile_name = st.selectbox("Output format", list(PRESETS), key="output_profile")
    profile = get_preset(profile_name)
    music_file = st.file_uploader("Optional soundtrack WAV", type=["wav"])
    music_volume = st.slider("Music volume", 0.0, 1.0, 0.18, key="music_volume")
    voice_volume = st.slider("Narration volume", 0.0, 1.0, 1.0, key="voice_volume")
    look = st.selectbox("Color look preset", list(LOOK_PRESETS), key="look")
    fade_seconds = st.slider("Fade duration (seconds)", 0.0, 2.0, 0.5, step=0.1, key="fade_seconds")
    transition_seconds = st.slider("Scene crossfade (seconds)", 0.0, 1.5, 0.5, step=0.1, key="transition_seconds")
    fps = st.slider("Final FPS", 12, 60, int(profile["fps"]), key="fps")

from cineforge.local_video import runtime_status
local_state = runtime_status()
with st.expander("Local model status", expanded=True):
    st.json(local_state)
    st.caption("CineForge local rendering uses in-process model inference. No hosted video-generation API or ComfyUI.")


st.header("Project Workspace Isolation")
from cineforge.project_workspace import initialize_workspace, read_manifest
workspace_root = Path("projects/workspaces")
workspace_root.mkdir(parents=True, exist_ok=True)
workspace_label = st.text_input("Workspace name", prompt[:40] or "project", key="workspace_label")
active_workspace = initialize_workspace(workspace_root, workspace_label)
workspace_manifest = read_manifest(active_workspace)
workspace_renders = active_workspace / "renders"
workspace_audio = active_workspace / "audio"
workspace_exports = active_workspace / "exports"
workspace_checkpoints = active_workspace / "checkpoints"
workspace_reports = active_workspace / "reports"
for folder in (workspace_renders, workspace_audio, workspace_exports, workspace_checkpoints, workspace_reports):
    folder.mkdir(parents=True, exist_ok=True)
gallery_dir = workspace_renders
st.caption(f"Active workspace: {active_workspace}")
st.json(workspace_manifest)

if st.button("📝 Create storyboard", type="primary"):
    st.session_state["expanded_prompt"] = expand_story(prompt, scene_count, style, character)
    st.session_state["prompt_storyboard_ready"] = True

if st.session_state.get("prompt_storyboard_ready"):
    st.success("Storyboard created. Review and edit scenes below. To render actual footage, configure a compatible generation provider and workflow in the sidebar.")

if st.button("Expand prompt into cinematic story"):
    st.session_state["expanded_prompt"] = expand_story(prompt, scene_count, style, character)
story_prompt = st.session_state.get("expanded_prompt", prompt)
scene_signature = (story_prompt, scene_count, style, character)
if st.session_state.get("scene_cache_signature") != scene_signature:
    st.session_state["editable_scenes"] = plan(story_prompt, scene_count, style, character)
    st.session_state["scene_cache_signature"] = scene_signature
scenes = st.session_state["editable_scenes"]
from cineforge.director import analyze_scene_plan
scene_plan_report = analyze_scene_plan(scenes)
from cineforge.continuity import analyze_continuity
continuity_report = analyze_continuity(scenes, character, style)
with st.expander("Story Continuity Check", expanded=False):
    if continuity_report["issues"]:
        st.warning("Continuity prompt checks found items to review.")
    else:
        st.success("Continuity prompt checks passed.")
    st.json(continuity_report)
with st.expander("Intelligent Scene Director", expanded=False):
    st.metric("Shot diversity", f'{scene_plan_report["distinct_camera_count"]}/{scene_plan_report["scene_count"]}')
    st.json(scene_plan_report)
    for scene_index, directed_scene in enumerate(scenes, 1):
        st.caption(f"Scene {scene_index}: {directed_scene.camera} — {directed_scene.title}")
if DURATIONS.get(duration_choice):
    per_scene = max(2, int(DURATIONS[duration_choice] / len(scenes)))
    for scene in scenes:
        scene.seconds = min(20, per_scene)

if "scene_order" not in st.session_state or len(st.session_state.scene_order) != len(scenes):
    st.session_state.scene_order = list(range(len(scenes)))
order = st.session_state.scene_order
order_cols = st.columns([3,1,1])
for position, scene_index in enumerate(order):
    scene = scenes[scene_index]
    cols = st.columns([3,1,1])
    cols[0].write(f"{position+1}. {scene.title} · {scene.seconds}s")
    if cols[1].button("↑", key=f"up_{position}", disabled=position==0):
        st.session_state.scene_order = move_item(order, position, -1); st.rerun()
    if cols[2].button("↓", key=f"down_{position}", disabled=position==len(order)-1):
        st.session_state.scene_order = move_item(order, position, 1); st.rerun()
scenes = [scenes[index] for index in st.session_state.scene_order]
st.session_state["editable_scenes"] = scenes
try:
    st.metric("Ordered timeline duration", f"{validate_timeline([{'seconds': scene.seconds} for scene in scenes])} seconds")
except Exception as timeline_error:
    st.warning(str(timeline_error))

st.header("Visual Storyboard Preview")
storyboard_rows = preview_rows(scenes)
storyboard_columns = st.columns(2)
for storyboard_index, storyboard_scene in enumerate(scenes):
    with storyboard_columns[storyboard_index % 2]:
        with st.container(border=True):
            st.markdown(f"### Scene {storyboard_index + 1}: {storyboard_scene.title}")
            st.caption(f"🎥 {storyboard_scene.camera} · ⏱ {storyboard_scene.seconds}s")
            st.text_area("Scene prompt", storyboard_scene.prompt, key=f"storyboard_prompt_{storyboard_index}")
            st.text_area("Narration", storyboard_scene.narration, key=f"storyboard_narration_{storyboard_index}")
            st.caption(f"Timeline: {storyboard_rows[storyboard_index]['start']}s – {storyboard_rows[storyboard_index]['end']}s")
st.download_button("Download storyboard CSV", to_csv(storyboard_rows), file_name="cineforge_storyboard.csv", mime="text/csv")
for storyboard_index, storyboard_scene in enumerate(scenes):
    storyboard_scene.prompt = st.session_state.get(f"storyboard_prompt_{storyboard_index}", storyboard_scene.prompt)
    storyboard_scene.narration = st.session_state.get(f"storyboard_narration_{storyboard_index}", storyboard_scene.narration)

# Scene validation from the reusable scene-editing utility.
from cineforge.scene_editor_utils import validate_scenes
with st.expander("Scene edit validation", expanded=False):
    scene_errors = validate_scenes(scenes)
    if scene_errors:
        for scene_error in scene_errors:
            st.error(scene_error)
    else:
        st.success("All scenes have titles, prompts and valid durations.")

st.header("Bilingual Voiceover Studio")
from cineforge.voice import list_voices
voice_mode = st.selectbox("Narration languages", ["English + Telugu (both)", "English only", "Telugu only"], key="voice_mode")
voice_profile = st.selectbox("Narration voice style", list(VOICE_PROFILES), key="voice_profile")
all_voices = list_voices()

def choose_voice(lang, key):
    filtered = [v for v in all_voices if lang in v["languages"] or lang in v["name"].lower()]
    options = filtered or all_voices
    return st.selectbox(f"{lang.upper()} voice", options, format_func=lambda v: v["name"], key=key) if options else None

english_voice = choose_voice("en", "english_voice") if voice_mode != "Telugu only" else None
telugu_voices = [v for v in all_voices if "te" in v["languages"] or "telugu" in v["name"].lower()]
telugu_voice = st.selectbox("Telugu voice", telugu_voices or all_voices, format_func=lambda v: v["name"], key="telugu_voice") if voice_mode != "English only" and (telugu_voices or all_voices) else None
if voice_mode != "English only" and not telugu_voices:
    st.warning("No Telugu system voice detected. Install one on the machine running CineForge.")

telugu_scripts = st.session_state.setdefault("telugu_scene_scripts", {})
for idx, scene in enumerate(scenes, 1):
    with st.expander(f"Scene {idx} bilingual narration", expanded=False):
        st.text_area("English narration", scene.narration, key=f"bilingual_en_{idx}")
        telugu_scripts[idx] = st.text_area("Telugu narration", telugu_scripts.get(idx, ""), key=f"bilingual_te_{idx}")

combined_en = "\n\n".join(st.session_state.get(f"bilingual_en_{idx}", scene.narration) for idx, scene in enumerate(scenes, 1))
combined_te = "\n\n".join(telugu_scripts.get(idx, "") for idx in range(1, len(scenes) + 1))
if st.button("Generate bilingual voice previews"):
    try:
        settings = VOICE_PROFILES[voice_profile]
        output_dir = workspace_audio / "bilingual_preview"
        output_dir.mkdir(parents=True, exist_ok=True)
        if voice_mode != "Telugu only" and english_voice:
            en_file = synthesize(combined_en, output_dir / "preview_english.wav", rate=settings["rate"], volume=settings["volume"], voice_id=english_voice["id"])
            st.audio(str(en_file))
        if voice_mode != "English only" and telugu_voice and combined_te.strip():
            te_file = synthesize(combined_te, output_dir / "preview_telugu.wav", rate=settings["rate"], volume=settings["volume"], voice_id=telugu_voice["id"])
            st.audio(str(te_file))
        elif voice_mode != "English only":
            st.warning("Add Telugu narration to scene fields before generating Telugu audio.")
    except Exception as e:
        st.error(f"Preview generation failed: {e}")
st.header("Timeline ordering")



st.header("Project Library")
project_dir = Path("projects")
project_dir.mkdir(parents=True, exist_ok=True)
project_database_path = project_dir / "cineforge.sqlite3"
project_records = list_project_records(project_database_path)
if project_records:
    selected_slug = st.selectbox("Saved project", [item["slug"] for item in project_records],
                                 format_func=lambda slug: next(item["name"] for item in project_records if item["slug"] == slug))
    if st.button("Load from project database"):
        try:
            loaded = load_project_record(project_database_path, selected_slug)
            apply_project_settings(st.session_state, loaded)
            st.rerun()
        except Exception as library_error:
            st.error(f"Project database load failed: {library_error}")
else:
    st.caption("No database projects yet. Save the current storyboard to create one.")

st.header("Restore a saved project")
project_upload = st.file_uploader("Import CineForge project JSON", type=["json"], key="project_restore_upload")
if project_upload is not None:
    try:
        restored = json.loads(project_upload.getvalue())
        restored_scenes = restored.get("scenes", [])
        if not isinstance(restored_scenes, list) or not restored_scenes:
            st.error("Project file has no scenes.")
        else:
            st.write(f"Project contains {len(restored_scenes)} scene(s).")
            if st.button("Apply imported project settings"):
                apply_project_settings(st.session_state, restored)
                st.rerun()
    except Exception as restore_error:
        st.error(f"Project import failed: {restore_error}")


# Reconstruct imported projects into editable Scene objects (validated and bounded).
if st.session_state.get("restored_project"):
    restored_project = st.session_state["restored_project"]
    try:
        imported_items = restored_project.get("scenes", [])
        if imported_items and all(isinstance(item, dict) for item in imported_items):
            restored_scene_objects = []
            for item in imported_items[:6]:
                restored_scene_objects.append(type(scenes[0])(
                    title=str(item.get("title", "Imported scene"))[:160],
                    prompt=str(item.get("prompt", ""))[:12000],
                    seconds=max(2, min(20, int(item.get("seconds", 5)))),
                    narration=str(item.get("narration", ""))[:5000],
                    camera=item.get("camera", "Tracking shot") if item.get("camera") in CAMERA_PRESETS else "Tracking shot"))
            scenes = restored_scene_objects
            scenes = reorder_scenes_by_titles(scenes, restored_project.get("scene_order", []))
            st.session_state["scene_order"] = list(range(len(scenes)))
            st.info("Imported storyboard scenes restored for this session.")
    except (ValueError, TypeError, KeyError) as import_apply_error:
        st.warning(f"Could not restore scenes: {import_apply_error}")

st.header("Render status dashboard")
status_registry = read_registry(workspace_reports / "render_status.json")
recovery_dashboard = SceneRecoveryStore(workspace_reports / "scene_recovery.json")
recovery_summary = recovery_dashboard.summary()
recovery_cols = st.columns(5)
recovery_cols[0].metric("Tracked scenes", recovery_summary["scene_count"])
recovery_cols[1].metric("Complete", recovery_summary["complete"])
recovery_cols[2].metric("Retrying", recovery_summary["retrying"])
recovery_cols[3].metric("Failed", recovery_summary["failed"])
recovery_cols[4].metric("Render attempts", recovery_summary["total_attempts"])
with st.expander("Scene-by-scene render details", expanded=False):
    for scene_number, scene in enumerate(scenes, 1):
        render_entry = status_registry.get(str(scene_number), {})
        scene_history = recovery_dashboard.get_scene(scene_number)
        render_state = render_entry.get("status", scene_history.get("status", "not started"))
        detail = render_entry.get("detail", "")
        attempts = scene_history.get("attempts", 0)
        st.markdown(f"**Scene {scene_number}: {scene.title}**")
        detail_cols = st.columns(3)
        detail_cols[0].write(f"Status: {render_state.title()}")
        detail_cols[1].write(f"Attempts: {attempts}")
        detail_cols[2].write(f"Updated: {scene_history.get('updated_at', '—')}")
        if detail and render_state != "failed":
            st.caption(detail)
        last_error = scene_history.get("last_error") or (detail if render_state == "failed" else "")
        if last_error:
            st.error(f"Latest error: {last_error}")
if status_registry:
    status_cols = st.columns(4)
    counts = {state: sum(1 for entry in status_registry.values() if entry.get("status") == state) for state in ["complete", "rendering", "queued", "failed"]}
    for col, state in zip(status_cols, ["complete", "rendering", "queued", "failed"]):
        col.metric(state.title(), counts[state])
else:
    st.caption("Render status is populated as renders progress.")

st.header("CineForge Scene Studio")
for card in scene_cards(scenes):
    with st.container(border=True):
        st.subheader(f"Scene {card['number']} · {card['title']}")
        st.caption(f"{card['duration']} seconds · {card['camera']} · Status: {card['status']}")
        if card["clips"]:
            for clip in card["clips"]:
                st.video(str(clip))
        st.write(card["prompt"])
        if card["narration"]:
            st.caption("Narration: " + card["narration"])

st.header("Storyboard editor")
with st.expander("Timeline ordering — move scenes", expanded=True):
    for order_index, order_scene in enumerate(scenes):
        order_cols = st.columns([4, 1, 1])
        order_cols[0].write(f"{order_index + 1}. {order_scene.title}")
        if order_cols[1].button("↑", key=f"timeline_up_{order_index}", disabled=order_index == 0):
            scenes = move_item(scenes, order_index, -1)
            st.session_state["editable_scenes"] = scenes
            st.session_state["scene_cache_signature"] = scene_signature
            st.rerun()
        if order_cols[2].button("↓", key=f"timeline_down_{order_index}", disabled=order_index >= len(scenes) - 1):
            scenes = move_item(scenes, order_index, 1)
            st.session_state["editable_scenes"] = scenes
            st.session_state["scene_cache_signature"] = scene_signature
            st.rerun()
from cineforge.scene_editor_utils import add_scene, duplicate_scene, remove_scene
scene_action_cols = st.columns(3)
if scene_action_cols[0].button("➕ Add scene", key="editor_add_scene"):
    scenes = add_scene(scenes, lambda: type(scenes[0])(title="New scene", prompt="Describe the visuals for this scene.", seconds=5, narration="", camera="Tracking shot"))
    st.session_state["editable_scenes"] = scenes
    st.session_state.scene_order = list(range(len(scenes)))
    st.rerun()
for i, scene in enumerate(scenes, 1):
    with st.expander(f"Scene {i} · {scene.title}", expanded=i == 1):
        scene.title = st.text_input("Scene title", scene.title, key=f"title{i}")
        scene.seconds = st.slider("Duration (seconds)", 2, 20, min(20, max(2, scene.seconds)), key=f"duration{i}")
        scene.camera = st.selectbox("Camera direction", list(CAMERA_PRESETS), index=list(CAMERA_PRESETS).index(scene.camera), key=f"camera{i}")
        scene.prompt = st.text_area("Video prompt", scene.prompt, key=f"prompt{i}", height=120)
        scene.narration = st.text_area("Narration", scene.narration, key=f"narr{i}")
        action_cols = st.columns(2)
        if action_cols[0].button("Duplicate scene", key=f"duplicate_scene_{i}"):
            scenes = duplicate_scene(scenes, i-1)
            st.session_state["editable_scenes"] = scenes
            st.session_state.scene_order = list(range(len(scenes)))
            st.rerun()
        if action_cols[1].button("Delete scene", key=f"delete_scene_{i}", disabled=len(scenes) <= 1):
            scenes = remove_scene(scenes, i-1)
            st.session_state["editable_scenes"] = scenes
            st.session_state.scene_order = list(range(len(scenes)))
            st.rerun()


st.header("AI Scene Image Review — technical checks")
from cineforge.image_review import review_image_folder
image_review_report = review_image_folder(gallery_dir)
with st.expander("Scene image review report", expanded=False):
    st.metric("Images found", image_review_report["image_count"])
    st.metric("Review flags", image_review_report["issue_count"])
    for image_result in image_review_report["results"]:
        st.caption(image_result["path"])
        if image_result["valid"]:
            st.write(f'{image_result["width"]} × {image_result["height"]} · brightness {image_result["brightness"]} · contrast {image_result["contrast"]}')
        for image_issue in image_result["issues"]:
            st.warning(image_issue)
        if image_result["valid"] and not image_result["issues"]:
            st.success("No technical image flags.")
    if not image_review_report["image_count"]:
        st.info("No saved scene images found. This checks image files, not video frames or semantic continuity.")

st.header("Smart Scene Asset Manager")
from cineforge.asset_manager import scan_assets, summarize_assets
asset_root = active_workspace
asset_inventory = scan_assets(asset_root)
asset_summary = summarize_assets(asset_inventory)
asset_cols = st.columns(5)
asset_cols[0].metric("Total assets", asset_summary["total"])
for col, asset_kind in zip(asset_cols[1:], ["image", "video", "audio", "project"]):
    col.metric(asset_kind.title(), asset_summary["by_type"].get(asset_kind, 0))
with st.expander("Asset inventory", expanded=False):
    if asset_inventory:
        st.dataframe(asset_inventory, use_container_width=True)
        inventory_json = json.dumps(asset_inventory, indent=2)
        st.download_button("Download asset inventory JSON", inventory_json, file_name="cineforge_asset_inventory.json", mime="application/json")
    else:
        st.info("No recognized assets found under outputs yet.")
st.header("Scene Asset Links & Replacement History")
scene_asset_manifest = workspace_reports / "scene_assets.json"

st.header("Visual Preview Timeline")
# Per-scene trim controls use source clip duration and store bounded start/end values.
trim_ranges = []
for trim_scene_index, trim_scene in enumerate(scenes, 1):
    trim_candidates = sorted((workspace_renders / f"final_scene_{trim_scene_index}").glob("*"))
    trim_candidates = [p for p in trim_candidates if p.is_file() and p.suffix.lower() in {".mp4", ".webm", ".mov"}]
    if trim_candidates:
        try:
            import av
            with av.open(str(trim_candidates[0])) as trim_container:
                trim_stream = next((s for s in trim_container.streams if s.type == "video"), None)
                trim_duration = float(trim_stream.duration * trim_stream.time_base) if trim_stream and trim_stream.duration and trim_stream.time_base else float(trim_container.duration / av.time_base) if trim_container.duration else float(trim_scene.seconds)
            trim_duration = max(0.1, trim_duration)
            trim_key = f"trim_{trim_scene_index}"
            saved_trim = st.session_state.get(trim_key, (0.0, trim_duration))
            saved_start = min(max(0.0, float(saved_trim[0])), trim_duration)
            saved_end = min(max(saved_start + 0.1, float(saved_trim[1])), trim_duration)
            with st.expander(f"Trim Scene {trim_scene_index} · {trim_scene.title}"):
                trim_start = st.slider("Start offset (seconds)", 0.0, max(0.0, trim_duration-0.1), min(saved_start, trim_duration-0.1), 0.1, key=f"trim_start_{trim_scene_index}")
                trim_end = st.slider("End offset (seconds)", min(0.1, trim_duration), trim_duration, saved_end, 0.1, key=f"trim_end_{trim_scene_index}")
                st.session_state[trim_key] = (trim_start, max(trim_start+0.1, trim_end))
            trim_ranges.append(st.session_state[trim_key])
        except Exception as trim_error:
            st.caption(f"Trim controls unavailable for scene {trim_scene_index}: {trim_error}")
            trim_ranges.append((0.0, None))
    else:
        trim_ranges.append((0.0, None))
from cineforge.trim_timeline import calculate_trimmed_duration, trim_summary
trimmed_duration = calculate_trimmed_duration([scene.seconds for scene in scenes], trim_ranges, transition_seconds)
st.info(f"Trim-adjusted movie duration estimate: {trimmed_duration:.1f} seconds")
with st.expander("Trim-adjusted timeline summary"):
    st.json(trim_summary([scene.title for scene in scenes], [scene.seconds for scene in scenes], trim_ranges, transition_seconds))
timeline_clip_paths = []
for timeline_index in range(1, len(scenes) + 1):
    candidates = sorted((workspace_renders / f"final_scene_{timeline_index}").glob("*"))
    candidates = [path for path in candidates if path.is_file() and path.suffix.lower() in {".mp4", ".webm", ".mov"}]
    timeline_clip_paths.append(candidates[0] if candidates else None)
registered_timeline_clips = [
    path if path is not None else workspace_renders / f"__missing_scene_{index}.mp4"
    for index, path in enumerate(timeline_clip_paths, 1)
]
resolved_timeline_clips = resolve_scene_videos(scene_asset_manifest, registered_timeline_clips)
timeline_report = build_visual_timeline(scenes, resolved_timeline_clips, transition_seconds)
timeline_metrics = st.columns(4)
timeline_metrics[0].metric("Scenes", timeline_report["scene_count"])
timeline_metrics[1].metric("Ready clips", timeline_report["ready_count"])
timeline_metrics[2].metric("Missing clips", timeline_report["missing_count"])
timeline_metrics[3].metric("Timeline duration", f'{timeline_report["total_seconds"]:.1f}s')
if timeline_report["missing_count"]:
    st.warning("Some scenes do not have a usable video clip yet. Render or register a replacement before preview assembly.")
for timeline_row in timeline_report["scenes"]:
    with st.container(border=True):
        timeline_cols = st.columns([3, 1, 1])
        timeline_cols[0].markdown(f"**Scene {timeline_row['scene']}: {timeline_row['title']}**")
        timeline_cols[1].write(f"{timeline_row['start']:.1f}s – {timeline_row['end']:.1f}s")
        timeline_cols[2].write(f"{timeline_row['duration']:.1f}s")
        st.progress(min(1.0, timeline_row["duration"] / max(timeline_report["total_seconds"], 1.0)))
        if timeline_row["clip_ready"]:
            st.video(timeline_row["clip_path"])
            if timeline_row["transition_after"]:
                st.caption(f"Crossfade after this scene: {timeline_row['transition_after']:.1f}s")
        else:
            st.info("Video clip missing — render this scene or activate a registered replacement.")
with st.expander("Timeline data"):
    st.json(timeline_report)
scene_asset_rows = scene_asset_inventory(scene_asset_manifest)
if scene_asset_rows:
    st.dataframe(scene_asset_rows, use_container_width=True)
else:
    st.caption("No scene-specific assets registered yet.")
with st.expander("Link an existing workspace asset to a scene"):
    link_scene_number = st.number_input("Scene number", min_value=1, max_value=max(1, len(scenes)), value=1, step=1, key="link_scene_number")
    linkable_assets = [item for item in asset_inventory if item["type"] in {"image", "video", "audio"}]
    if linkable_assets:
        linkable_paths = [item["path"] for item in linkable_assets]
        selected_link_path = st.selectbox("Asset file", linkable_paths, key="selected_scene_asset")
        selected_link_type = next(item["type"] for item in linkable_assets if item["path"] == selected_link_path)
        activate_linked_video = st.checkbox("Set as active scene video", value=selected_link_type == "video", key="activate_linked_scene_video")
        if st.button("Register scene asset", key="register_scene_asset_button"):
            try:
                register_scene_asset(scene_asset_manifest, int(link_scene_number), selected_link_path, selected_link_type, activate=activate_linked_video)
                st.success("Scene asset registered.")
                st.rerun()
            except Exception as link_error:
                st.error(f"Asset registration failed: {link_error}")
    else:
        st.info("Place an image, video or audio file in this project's workspace first.")

st.header("Scene Gallery — saved renders")
gallery_dir = workspace_renders
saved_scene_files = sorted(gallery_dir.glob("final_scene_*/*")) if gallery_dir.exists() else []
saved_scene_files = [p for p in saved_scene_files if p.is_file() and p.suffix.lower() in {".mp4", ".webm", ".mov"}]
if saved_scene_files:
    gallery_cols = st.columns(2)
    for gallery_index, clip_file in enumerate(saved_scene_files):
        with gallery_cols[gallery_index % 2]:
            st.caption(clip_file.name)
            st.video(str(clip_file))
else:
    st.info("Rendered clips will appear here after a successful scene render.")

st.header("Pre-render storyboard review")
findings = review_scenes(scenes)
for item in findings:
    if item.severity == "error":
        st.error(f"{item.message}")
    elif item.severity == "warning":
        st.warning(f"{('Scene '+str(item.scene_index)+': ') if item.scene_index else ''}{item.message}")
    else:
        st.success(item.message)
if st.button("Refresh scene review"):
    st.rerun()

total = trimmed_duration
st.subheader("Timeline")
preview_data = preview_rows(scenes)
st.download_button("Download timeline CSV", to_csv(preview_data), file_name="cineforge_timeline.csv", mime="text/csv")
with st.expander("Scene preview details"):
    for row in preview_data:
        st.markdown(f"**{row['number']}. {row['title']}** · {row['start']}–{row['end']} seconds")
        st.caption(f"Camera: {row['camera']}")
        st.write(row["prompt"])
        if row["narration"]:
            st.caption("Narration: " + row["narration"])
st.metric("Movie duration", f"{total} seconds")
offset = 0
for i, scene in enumerate(scenes, 1):
    st.write(f"{i}. {scene.title} · {offset}s–{offset+scene.seconds}s")
    st.progress(scene.seconds / max(total, 1))
    offset += scene.seconds - transition_seconds

script = export_script(story_prompt, style, character, scenes)
script.update({"original_prompt": prompt, "scene_order": [scene.title for scene in scenes], "timeline": {"total_seconds": total, "fps": fps}, "cinematic_look": look, "output_profile": profile_name, "duration_preset": duration_choice, "target_dimensions": [profile["width"], profile["height"]]})
script["cineforge_settings"] = project_settings_payload({"negative_prompt": negative, "duration_choice": duration_choice, "scene_count": scene_count, "visual_style": style, "output_profile": profile_name, "music_volume": music_volume, "voice_volume": voice_volume, "look": look, "fade_seconds": fade_seconds, "transition_seconds": transition_seconds, "fps": fps, "voice_mode": voice_mode, "voice_profile": voice_profile, "workspace_label": workspace_label})
st.download_button("Download subtitles (SRT)", create_srt(scenes, transition_seconds, trim_ranges), file_name="cineforge_subtitles.srt", mime="text/plain")
st.download_button("Save project JSON", json.dumps(script, indent=2), file_name="cineforge_project.json", mime="application/json")
if st.button("Save to project database"):
    try:
        from cineforge.workspace import workspace_name
        project_slug = workspace_name(workspace_label)
        save_project_record(project_database_path, project_slug, workspace_label, script)
        save_project(script, active_workspace / "cineforge_project.json")
        st.success(f"Project saved to SQLite and workspace: {workspace_label}")
    except Exception as save_error:
        st.error(f"Project save failed: {save_error}")


st.header("Export Presets")
export_preset_name = st.selectbox("Export format", list(PRESETS.keys()), key="export_preset")
export_config = get_preset(export_preset_name)
color_grade = st.selectbox("Final cinematic color grade", ["none", "cinematic", "warm", "cool"], index=1, key="final_color_grade")
st.caption(f"Resolution: {export_config['width']} × {export_config['height']} · {export_config['fps']} FPS · {export_config['format'].upper()}")
st.success("The selected export dimensions are applied during final MP4 assembly.")

st.header("Sound Studio")
with st.expander("Mixing settings", expanded=True):
    narration_level = st.slider("Narration volume", 0.0, 1.0, 1.0, 0.05, key="mix_narration_level")
    music_level = st.slider("Music volume", 0.0, 1.0, 0.25, 0.05, key="mix_music_level")
    sound_fade = st.slider("Sound fade duration", 0.0, 10.0, 1.5, 0.5, key="sound_fade")
    mix_config = mix_settings(narration_level, music_level, sound_fade)
    st.json(mix_config)

st.header("Cinematic Preview Player")
preview_candidates = sorted(gallery_dir.glob("final_scene_*/*")) if gallery_dir.exists() else []
preview_candidates = [p for p in preview_candidates if p.is_file() and p.suffix.lower() in {".mp4", ".webm", ".mov"}]
if preview_candidates:
    if st.button("Assemble visual preview from available scenes"):
        try:
            preview_ordered = resolve_scene_videos(scene_asset_manifest, apply_replacements(preview_candidates, workspace_reports / "replacements.json"))
            preview_file = assemble(preview_ordered, workspace_exports / "cineforge_preview.mp4", fps, fade_seconds=fade_seconds)
            st.success("Preview assembled.")
            st.video(str(preview_file))
            st.download_button("Download cinematic preview", preview_file.read_bytes(), file_name="cineforge_preview.mp4", mime="video/mp4")
        except Exception as preview_error:
            st.error(f"Preview assembly failed: {preview_error}")
else:
    st.caption("Render scenes first to enable preview assembly.")

st.header("Regenerate a single scene")
st.caption("Generate a revised scene locally for preview, without a hosted generation service.")
if local_state.get("ready", False):
    scene_choice = st.selectbox("Scene to regenerate", list(range(1, len(scenes) + 1)), format_func=lambda n: f"Scene {n}: {scenes[n-1].title}")
    regen_prompt = st.text_area("Regeneration prompt", scenes[scene_choice-1].prompt, key="regen_prompt")
    if st.button("Render replacement preview"):
        try:
            from cineforge.local_scene_renderer import render_local_scene
            chosen = scenes[scene_choice-1]
            final_prompt = regen_prompt + " Camera direction: " + CAMERA_PRESETS[chosen.camera] + f". Color look: {LOOK_PRESETS[look]}. Target format: {profile_name}, {profile['width']}x{profile['height']}."
            with st.spinner("Rendering locally..."):
                regen_clips = render_local_scene(final_prompt, workspace_renders / f"scene_{scene_choice}_replacement_preview", negative_prompt=negative, frames=49, steps=20, fps=fps, status_box=st)
            st.success("Replacement preview rendered.")
            for replacement in regen_clips:
                st.video(str(replacement))
                st.download_button("Download replacement clip", replacement.read_bytes(), file_name=replacement.name, key=f"regen_download_{replacement.name}")
                if st.button(f"Use this clip for Scene {scene_choice}", key=f"activate_scene_{scene_choice}_{replacement.name}"):
                    register_scene_asset(scene_asset_manifest, scene_choice, replacement, "video", activate=True)
                    st.success("Replacement registered and selected as active.")
                    st.rerun()
        except Exception as regen_exc:
            st.error(f"Local scene render failed: {regen_exc}")
else:
    st.info("Single-scene local rendering requires a supported GPU/accelerator.")

st.markdown('<div id="generate-final-movie"></div>', unsafe_allow_html=True)
st.header("🎥 Generate final movie — AI video rendering")
st.caption(f"Final MP4 will be resized to {export_config['width']} × {export_config['height']} at {fps} FPS during assembly.")
if not local_state.get("ready", False):
    st.warning("Local movie rendering is unavailable until a supported GPU/accelerator and dependencies are configured.")
if local_state.get("ready", False):
    if st.button("🎬 Generate / Resume movie", type="primary"):
        try:
            from cineforge.local_video_provider import LocalVideoProvider
            engine = LocalVideoProvider(fps=8)
            clips = []
            status = st.empty()
            progress = st.progress(0)
            checkpoint_path = workspace_checkpoints / "cineforge_checkpoint.json"
            completed = []
            scene_clip_paths = {}
            if checkpoint_path.exists():
                try:
                    previous = load_checkpoint(checkpoint_path)
                    if previous.get("project_prompt") == story_prompt:
                        saved_scene_clips = previous.get("scene_clip_paths")
                        if isinstance(saved_scene_clips, dict):
                            for scene_key, paths in saved_scene_clips.items():
                                scene_number = int(scene_key)
                                valid_paths = [Path(p) for p in paths if Path(p).is_file() and Path(p).stat().st_size > 0]
                                if 1 <= scene_number <= len(scenes) and valid_paths and len(valid_paths) == len(paths):
                                    scene_clip_paths[scene_number] = valid_paths
                            completed = sorted(scene_clip_paths)
                            clips = [path for scene_number in completed for path in scene_clip_paths[scene_number]]
                            status.info(f"Resuming checkpoint: {len(completed)} scene(s) have verified saved clips.")
                        else:
                            status.warning("Older checkpoint has no per-scene clip map; starting a safe render rather than skipping scenes with missing footage.")
                except (OSError, TypeError, ValueError, KeyError):
                    completed, clips, scene_clip_paths = [], [], {}
            recovery_store = SceneRecoveryStore(workspace_reports / "scene_recovery.json")
            for queue_index, queue_scene in enumerate(scenes, 1):
                if queue_index not in completed:
                    set_scene_status(workspace_reports / "render_status.json", queue_index, "queued", queue_scene.title)
                    recovery_store.record(queue_index, "queued")
            for i, scene in enumerate(scenes, 1):
                if i in completed:
                    if recovery_store.get_scene(i).get("status") != "complete":
                        recovery_store.record(i, "complete")
                    progress.progress(min(1.0, len(completed) / len(scenes)))
                    continue
                scene_prompt = scene.prompt + " Camera direction: " + CAMERA_PRESETS[scene.camera] + f". Color look: {LOOK_PRESETS[look]}. Target format: {profile_name}, {profile['width']}x{profile['height']}."
                wf = {"prompt": scene_prompt, "negative_prompt": negative, "num_frames": 49, "steps": 20, "guidance_scale": 6.0, "width": profile["width"], "height": profile["height"]}

                def render_scene():
                    set_scene_status(workspace_reports / "render_status.json", i, "rendering", scene.title)
                    status.info(f"Rendering scene {i}/{len(scenes)}: {scene.title}")
                    pid = engine.submit(wf)
                    outputs = engine.wait_for_outputs(pid, status)
                    videos = engine.download_videos(outputs, workspace_renders / f"final_scene_{i}")
                    if not videos:
                        raise RuntimeError(f"No video output detected for scene {i}.")
                    return videos

                def show_retry_attempt(attempt, maximum):
                    status.info(f"Rendering scene {i}/{len(scenes)} — attempt {attempt}/{maximum}")

                try:
                    videos = recovery_store.run_with_retry(i, render_scene, max_attempts=3, delay_seconds=2, on_attempt=show_retry_attempt)
                except Exception as scene_error:
                    set_scene_status(workspace_reports / "render_status.json", i, "failed", str(scene_error))
                    status.error(f"Scene {i} failed after retries. Check the recovery report and retry this scene.")
                    raise
                scene_clip_paths[i] = [Path(video) for video in videos]
                clips = [path for scene_number in sorted(scene_clip_paths) for path in scene_clip_paths[scene_number]]
                set_scene_status(workspace_reports / "render_status.json", i, "complete", scene.title)
                completed.append(i)
                progress.progress(i / len(scenes))
                save_checkpoint(checkpoint_path, story_prompt, scenes, completed, clips, scene_clip_paths=scene_clip_paths)
            status.info("Generating narration...")
            audio_dir = workspace_audio
            audio_dir.mkdir(parents=True, exist_ok=True)
            voice_settings = VOICE_PROFILES[voice_profile]
            voices = []
            for i, scene in enumerate(scenes, 1):
                scene_tracks = []
                if voice_mode != "Telugu only" and english_voice and scene.narration.strip():
                    scene_tracks.append(synthesize(
                        str(st.session_state.get(f"bilingual_en_{i}", scene.narration)).strip(),
                        audio_dir / f"final_scene_{i}_english.wav",
                        rate=voice_settings["rate"],
                        volume=voice_settings["volume"],
                        voice_id=english_voice["id"]))
                telugu_text = str(telugu_scripts.get(i, "")).strip()
                if voice_mode != "English only" and telugu_voice and telugu_text:
                    scene_tracks.append(synthesize(
                        telugu_text,
                        audio_dir / f"final_scene_{i}_telugu.wav",
                        rate=voice_settings["rate"],
                        volume=voice_settings["volume"],
                        voice_id=telugu_voice["id"]))
                voices.append(scene_tracks)
            music_path = None
            if music_file:
                music_path = audio_dir / "uploaded_soundtrack.wav"
                music_path.write_bytes(music_file.getvalue())
            mixed = mix_timeline(voices, [scene.seconds for scene in scenes], audio_dir / "movie_mix.wav", music_path, music_volume, voice_volume, fade_seconds=sound_fade, transition_seconds=transition_seconds, trim_ranges=trim_ranges)
            status.info("Assembling and muxing...")
            clips = resolve_scene_videos(scene_asset_manifest, apply_replacements(clips, workspace_reports / "replacements.json"))
            valid_clips, clip_issues = validate_clips(clips)
            for issue in clip_issues:
                st.warning(issue)
            if not valid_clips:
                raise RuntimeError("No valid video clips available for final assembly.")
            st.json(assembly_summary(valid_clips, fps, fade_seconds, mixed))
            final = assemble(valid_clips, workspace_exports / "cineforge_movie_with_sound.mp4", fps, audio_path=mixed, fade_seconds=fade_seconds, target_width=export_config["width"], target_height=export_config["height"], color_grade=color_grade, transition_seconds=transition_seconds, trim_ranges=trim_ranges)
            validation = validate_final_video(
                final,
                expected_width=export_config["width"],
                expected_height=export_config["height"],
                expected_fps=fps,
                expected_duration=trimmed_duration,
                require_audio=True,
            )
            if validation.get("audio_silent"):
                st.warning("Video export passed structural validation, but the decoded audio is nearly silent. Review the soundtrack before publishing.")
            else:
                st.success("Final MP4 passed structural validation with a non-silent audio signal.")
            st.json(validation)
            try:
                from cineforge.audio_quality import analyze_audio
                audio_quality = analyze_audio(mixed)
                st.subheader("Audio Quality Report")
                q1, q2, q3, q4 = st.columns(4)
                q1.metric("Peak", audio_quality["peak"])
                q2.metric("RMS", audio_quality["rms"])
                q3.metric("Clipped samples", audio_quality["clipped_sample_count"])
                q4.metric("Quiet samples", f'{audio_quality["quiet_sample_ratio"]:.1%}')
                if audio_quality["clipping_detected"]:
                    st.warning("Clipping detected in the mixed audio.")
                if audio_quality["mostly_silent"]:
                    st.warning("Audio is mostly silent or very quiet.")
                if not audio_quality["clipping_detected"] and not audio_quality["mostly_silent"]:
                    st.success("Signal-level check passed: no clipping detected and audio is not mostly silent.")
                st.json(audio_quality)
            except Exception as audio_exc:
                st.warning(f"Audio quality analysis could not be completed: {audio_exc}")
            report_warnings = list(clip_issues)
            if validation.get("audio_silent"):
                report_warnings.append("Decoded audio signal is nearly silent; review audio before publishing.")
            from cineforge.quality_gate import quality_gate
            gate_result = quality_gate(
                validation, audio_quality if "audio_quality" in locals() else None,
                scene_count=len(valid_clips), expected_scene_count=len(scenes),
                clip_issues=clip_issues,
            )
            export_report = build_report(
                validation,
                expected={
                    "width": export_config["width"],
                    "height": export_config["height"],
                    "fps": fps,
                    "duration_seconds": total,
                },
                warnings=report_warnings,
                quality_gate=gate_result,
            )
            report_path = save_report(export_report, workspace_reports / "cineforge_export_report.json")
            st.markdown(report_markdown(export_report))
            st.subheader("Cinematic Quality Gate")
            st.progress(gate_result["score"] / 100)
            st.metric("Readiness score", f'{gate_result["score"]}/100')
            if gate_result["ready_to_publish"]:
                st.success("READY — quality checks passed.")
            else:
                st.warning("REVIEW REQUIRED — review the issues before publishing.")
            st.json(gate_result)
            st.download_button(
                "Download export validation report",
                report_path.read_bytes(),
                file_name="cineforge_export_report.json",
                mime="application/json",
            )
            if gate_result["ready_to_publish"]:
                status.success("Movie export finished and passed the publishing quality gate.")
            else:
                status.warning("Movie export completed, but publishing checks require review. See the quality gate report before publishing.")
            st.video(str(final))
            st.download_button("Download final MP4", final.read_bytes(), file_name="cineforge_movie.mp4", mime="video/mp4")
            st.audio(mixed.read_bytes(), format="audio/wav")
        except Exception as exc:
            st.error(f"Movie pipeline failed: {exc}")
else:
    st.info("Local full-movie rendering requires a supported GPU/accelerator. Storyboard, project library, timeline, scene review, narration tools and asset management remain available.")

st.caption("Hosted mode uses a third-party video model API and may incur usage charges. Store credentials only in server environment variables or Streamlit secrets. PyAV may use FFmpeg libraries internally, but CineForge does not invoke the FFmpeg executable.")
