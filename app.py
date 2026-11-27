import json
from pathlib import Path
import streamlit as st

from cineforge.comfy import ComfyUI
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
from cineforge.project_store import save_project, load_project, list_projects
from cineforge.preview import preview_rows, to_csv
from cineforge.studio import scene_cards
from cineforge.render_status import read_registry, set_scene_status
from cineforge.replacements import record_replacement, apply_replacements
from cineforge.assembly_checks import validate_clips, assembly_summary, validate_final_video
from cineforge.export_report import build_report, save_report, report_markdown
from cineforge.voice_studio import VOICE_PROFILES, narration_text
from cineforge.sound_studio import validate_audio_tracks, mix_settings
from cineforge.export_presets import PRESETS, get_preset
from cineforge.release_audit import audit_repo, save_audit


st.set_page_config(page_title="CineForge AI Studio", page_icon="🎬", layout="wide")
st.title("🎬 CineForge AI — Production Studio")
st.caption("Storyboard, scene review, rendering, narration, soundtrack and final MP4. No FFmpeg executable is called.")

with st.expander("Release readiness audit"):
    audit = audit_repo(".")
    st.json(audit)
    audit_path = save_audit(audit, Path("outputs/cineforge_release_audit.json"))
    st.download_button("Download release audit JSON", audit_path.read_bytes(),
                      file_name="cineforge_release_audit.json", mime="application/json")

from cineforge.startup_check import run_checks
with st.expander("Startup diagnostics"):
    st.json(run_checks())

with st.sidebar:
    server = st.text_input("ComfyUI server URL", "http://127.0.0.1:8188")
    if st.button("Check ComfyUI connection"):
        diagnostic = check_server(server)
        (st.success if diagnostic["reachable"] else st.error)(format_queue(diagnostic))
    prompt = st.text_area("Movie idea", st.session_state.get("prompt", "A traveler discovers a glowing hidden city deep in the mountains"), height=140)
    character = st.text_area("Character continuity", st.session_state.get("character", "A traveler in a weathered dark-green cloak, leather backpack and boots; same appearance throughout"), height=90)
    negative = st.text_area("Negative prompt", "blurry, flicker, distorted anatomy, text, watermark")
    duration_choice = st.selectbox("Movie length", list(DURATIONS))
    scene_count = st.slider("Number of scenes", 2, 6, 4)
    style = st.selectbox("Visual style", ["cinematic photorealism", "stylized fantasy film", "science fiction cinema", "documentary cinematic", "animated feature-film look"])
    profile_name = st.selectbox("Output format", list(PRESETS))
    profile = get_preset(profile_name)
    st.caption(f"Target: {profile['width']} × {profile['height']} · {profile['fps']} FPS")
    workflow_file = st.file_uploader("ComfyUI API workflow JSON", type=["json"])
    music_file = st.file_uploader("Optional soundtrack WAV", type=["wav"])
    music_volume = st.slider("Music volume", 0.0, 1.0, 0.18)
    voice_volume = st.slider("Narration volume", 0.0, 1.0, 1.0)
    look = st.selectbox("Color look preset", list(LOOK_PRESETS))
    fade_seconds = st.slider("Fade duration (seconds)", 0.0, 2.0, 0.5, step=0.1)\n    transition_seconds = st.slider("Scene crossfade (seconds)", 0.0, 1.5, 0.5, step=0.1)
    fps = st.slider("Final FPS", 12, 60, int(profile["fps"]))

if st.button("Expand prompt into cinematic story"):
    st.session_state["expanded_prompt"] = expand_story(prompt, scene_count, style, character)
story_prompt = st.session_state.get("expanded_prompt", prompt)
scenes = plan(story_prompt, scene_count, style, character)
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
        output_dir = Path("outputs/bilingual_preview")
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
project_files = list_projects(project_dir)
if project_files:
    selected_project = st.selectbox("Saved project", project_files, format_func=lambda p: p.stem)
    if st.button("Load from library"):
        try:
            loaded = load_project(selected_project)
            st.session_state["restored_project"] = loaded
            st.session_state["prompt"] = loaded.get("original_prompt", loaded.get("story_prompt", ""))
            st.session_state["character"] = loaded.get("character_continuity", "")
            st.success("Project loaded into session. Refresh the page to rebuild the storyboard.")
        except Exception as library_error:
            st.error(f"Library load failed: {library_error}")
else:
    st.caption("No saved projects yet. Use Save to library below.")

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
                st.session_state["prompt"] = restored.get("original_prompt", restored.get("story_prompt", ""))
                st.session_state["character"] = restored.get("character_continuity", "")
                st.session_state["restored_project"] = restored
                st.success("Imported project data saved in session. Reloading the storyboard from restored scenes is not yet fully implemented.")
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
            st.info("Imported storyboard scenes restored for this session.")
    except (ValueError, TypeError, KeyError) as import_apply_error:
        st.warning(f"Could not restore scenes: {import_apply_error}")

st.header("Render status dashboard")
status_registry = read_registry(Path("outputs/render_status.json"))
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
for i, scene in enumerate(scenes, 1):
    with st.expander(f"Scene {i} · {scene.title}", expanded=i == 1):
        scene.title = st.text_input("Scene title", scene.title, key=f"title{i}")
        scene.seconds = st.slider("Duration (seconds)", 2, 20, min(20, max(2, scene.seconds)), key=f"duration{i}")
        scene.camera = st.selectbox("Camera direction", list(CAMERA_PRESETS), index=list(CAMERA_PRESETS).index(scene.camera), key=f"camera{i}")
        scene.prompt = st.text_area("Video prompt", scene.prompt, key=f"prompt{i}", height=120)
        scene.narration = st.text_area("Narration", scene.narration, key=f"narr{i}")


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

st.header("Scene Gallery — saved renders")
gallery_dir = Path("outputs")
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

total = sum(scene.seconds for scene in scenes) - transition_seconds * max(0, len(scenes) - 1)
st.subheader("Timeline")
preview_data = preview_rows(scenes)
st.download_button("Download timeline CSV", to_csv(preview_data), file_name="cineforge_timeline.csv", mime="text/csv")
with st.expander("Scene preview details"):
    for row in preview_data:
        st.markdown(f"**{row[\"number\"]}. {row[\"title\"]}** · {row[\"start\"]}–{row[\"end\"]} seconds")
        st.caption(f"Camera: {row[\"camera\"]}")
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
st.download_button("Download subtitles (SRT)", create_srt(scenes, transition_seconds), file_name="cineforge_subtitles.srt", mime="text/plain")
st.download_button("Save project JSON", json.dumps(script, indent=2), file_name="cineforge_project.json", mime="application/json")
if st.button("Save to project library"):
    try:
        save_project(script, project_dir / (prompt[:40].strip().replace(" ", "_") or "project") .replace("/", "_") + ".json")
        st.success("Project saved to library.")
    except Exception as save_error:
        st.error(f"Library save failed: {save_error}")


st.header("Export Presets")
export_preset_name = st.selectbox("Export format", list(PRESETS.keys()), key="export_preset")
export_config = get_preset(export_preset_name)
color_grade = st.selectbox("Final cinematic color grade", ["none", "cinematic", "warm", "cool"], index=1, key="final_color_grade")
st.caption(f"Resolution: {export_config[\"width\"]} × {export_config[\"height\"]} · {export_config[\"fps\"]} FPS · {export_config[\"format\"].upper()}")
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
            preview_ordered = apply_replacements(preview_candidates, Path("outputs/replacements.json"))
            preview_file = assemble(preview_ordered, Path("outputs/cineforge_preview.mp4"), fps, fade_seconds=fade_seconds)
            st.success("Preview assembled.")
            st.video(str(preview_file))
            st.download_button("Download cinematic preview", preview_file.read_bytes(), file_name="cineforge_preview.mp4", mime="video/mp4")
        except Exception as preview_error:
            st.error(f"Preview assembly failed: {preview_error}")
else:
    st.caption("Render scenes first to enable preview assembly.")

st.header("Regenerate a single scene")
st.caption("Render a revised scene independently for preview. This does not automatically replace the clip in the final movie checkpoint.")
if workflow_file:
    try:
        regen_workflow = json.loads(workflow_file.getvalue())
        scene_choice = st.selectbox("Scene to regenerate", list(range(1, len(scenes) + 1)), format_func=lambda n: f"Scene {n}: {scenes[n-1].title}")
        regen_prompt = st.text_area("Regeneration prompt", scenes[scene_choice-1].prompt, key="regen_prompt")
        if st.button("Render replacement preview"):
            with st.spinner(f"Rendering replacement for scene {scene_choice}..."):
                regen_engine = ComfyUI(server)
                chosen = scenes[scene_choice-1]
                final_prompt = regen_prompt + " Camera direction: " + CAMERA_PRESETS[chosen.camera] + f". Color look: {LOOK_PRESETS[look]}. Target format: {profile_name}, {profile['width']}x{profile['height']}."
                regen_wf = ComfyUI.replace_placeholders(regen_workflow, {"__PROMPT__": final_prompt, "__NEGATIVE__": negative})
                regen_pid = regen_engine.submit(regen_wf)
                regen_outputs = regen_engine.wait_for_outputs(regen_pid, st)
                regen_clips = regen_engine.download_videos(regen_outputs, Path("outputs") / f"scene_{scene_choice}_replacement_preview")
                if regen_clips:
                    st.success("Replacement preview rendered.")
                    st.info("Replacement previews are saved separately; you can mark a preview for use in the final timeline.")
                    for replacement in regen_clips:
                        st.video(str(replacement))
                        st.download_button("Download replacement clip", replacement.read_bytes(), file_name=replacement.name, key=f"regen_download_{replacement.name}")
                else:
                    st.error("No video output was found for the replacement preview.")
    except Exception as regen_exc:
        st.error(f"Scene regeneration setup failed: {regen_exc}")
else:
    st.info("Upload your ComfyUI workflow JSON in the sidebar to enable individual scene regeneration.")

st.header("Generate final movie")
st.caption(f"Final MP4 will be resized to {export_config['width']} × {export_config['height']} at {fps} FPS during assembly.")
if workflow_file:
    try:
        workflow = json.loads(workflow_file.getvalue())
    except Exception as exc:
        workflow = None
        st.error(f"Invalid workflow JSON: {exc}")
    if workflow is not None and st.button("🎬 Generate / Resume movie", type="primary"):
        try:
            engine = ComfyUI(server)
            clips = []
            status = st.empty()
            progress = st.progress(0)
            checkpoint_path = Path("outputs/cineforge_checkpoint.json")
            completed = []
            if checkpoint_path.exists():
                try:
                    previous = load_checkpoint(checkpoint_path)
                    if previous.get("project_prompt") == story_prompt:
                        completed = previous.get("completed_scene_indices", [])
                        clips = [Path(p) for p in previous.get("clip_paths", []) if Path(p).exists()]
                        status.info(f"Resuming checkpoint: {len(completed)} scene(s) already saved.")
                except Exception:
                    completed, clips = [], []
            for i, scene in enumerate(scenes, 1):
                if i in completed:
                    progress.progress(min(1.0, len(completed) / len(scenes)))
                    continue
                set_scene_status(Path("outputs/render_status.json"), i, "rendering", scene.title)
                status.info(f"Rendering scene {i}/{len(scenes)}: {scene.title}")
                scene_prompt = scene.prompt + " Camera direction: " + CAMERA_PRESETS[scene.camera] + f". Color look: {LOOK_PRESETS[look]}. Target format: {profile_name}, {profile['width']}x{profile['height']}."
                wf = ComfyUI.replace_placeholders(workflow, {"__PROMPT__": scene_prompt, "__NEGATIVE__": negative})
                pid = engine.submit(wf)
                outputs = engine.wait_for_outputs(pid, status)
                videos = engine.download_videos(outputs, Path("outputs") / f"final_scene_{i}")
                if not videos:
                    raise RuntimeError(f"No video output detected for scene {i}.")
                clips.extend(videos)
                set_scene_status(Path("outputs/render_status.json"), i, "complete", scene.title)
                completed.append(i)
                progress.progress(i / len(scenes))
                save_checkpoint(checkpoint_path, story_prompt, scenes, completed, clips)
            status.info("Generating narration...")
            audio_dir = Path("outputs/audio")
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
            mixed = mix_timeline(voices, [scene.seconds for scene in scenes], audio_dir / "movie_mix.wav", music_path, music_volume, voice_volume, fade_seconds=sound_fade, transition_seconds=transition_seconds)
            status.info("Assembling and muxing...")
            clips = apply_replacements(clips, Path("outputs/replacements.json"))
            valid_clips, clip_issues = validate_clips(clips)
            for issue in clip_issues:
                st.warning(issue)
            if not valid_clips:
                raise RuntimeError("No valid video clips available for final assembly.")
            st.json(assembly_summary(valid_clips, fps, fade_seconds, mixed))
            final = assemble(valid_clips, Path("outputs/cineforge_movie_with_sound.mp4"), fps, audio_path=mixed, fade_seconds=fade_seconds, target_width=export_config["width"], target_height=export_config["height"], color_grade=color_grade, transition_seconds=transition_seconds)
            validation = validate_final_video(
                final,
                expected_width=export_config["width"],
                expected_height=export_config["height"],
                expected_fps=fps,
                expected_duration=total,
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
            export_report = build_report(
                validation,
                expected={
                    "width": export_config["width"],
                    "height": export_config["height"],
                    "fps": fps,
                    "duration_seconds": total,
                },
                warnings=report_warnings,
            )
            report_path = save_report(export_report, Path("outputs/cineforge_export_report.json"))
            st.markdown(report_markdown(export_report))
            from cineforge.quality_gate import quality_gate
            gate_result = quality_gate(
                validation, audio_quality if "audio_quality" in locals() else None,
                scene_count=len(valid_clips), expected_scene_count=len(scenes),
                clip_issues=clip_issues,
            )
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
            status.success("Movie export finished.")
            st.video(str(final))
            st.download_button("Download final MP4", final.read_bytes(), file_name="cineforge_movie.mp4", mime="video/mp4")
            st.audio(mixed.read_bytes(), format="audio/wav")
        except Exception as exc:
            st.error(f"Movie pipeline failed: {exc}")
else:
    st.info("Upload a compatible ComfyUI API workflow JSON to enable generation.")

st.caption("PyAV may use FFmpeg libraries internally, but CineForge does not invoke the FFmpeg executable. Full pipeline still needs testing against a configured ComfyUI instance.")
