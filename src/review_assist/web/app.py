"""Flask app entrypoint for the local Review Assist web UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask, abort, flash, redirect, render_template, request, send_file, session, url_for

from review_assist.web import adapter


def create_app(*, project_root: str | Path | None = None, testing: bool = False) -> Flask:
    """Create the local web UI application."""

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("REVIEW_ASSIST_WEB_SECRET", "review-assist-local-dev"),
        PROJECT_ROOT=str(adapter.project_root_path(project_root)),
        TESTING=testing,
    )

    @app.context_processor
    def inject_layout_context() -> dict[str, Any]:
        selected_key = session.get("project_key", "")
        selected_project = _selected_project_ref(app, selected_key) if selected_key else None
        return {
            "selected_project_key": selected_key,
            "selected_project": selected_project,
        }

    @app.get("/")
    def index() -> Any:
        return redirect(url_for("projects"))

    @app.get("/projects")
    def projects() -> str:
        return render_template(
            "projects.html",
            active_page="projects",
            projects=adapter.list_projects(app.config["PROJECT_ROOT"]),
        )

    @app.post("/projects/select")
    def select_project() -> Any:
        project_key = request.form.get("project_key", "")
        try:
            adapter.resolve_project_dir(app.config["PROJECT_ROOT"], project_key)
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
            return redirect(url_for("projects"))
        session["project_key"] = project_key
        flash("Project selected.", "success")
        return redirect(url_for("overview"))

    @app.post("/projects/create")
    def create_project() -> Any:
        try:
            result = adapter.create_draft_project(
                app.config["PROJECT_ROOT"],
                project_id=request.form.get("project_id", ""),
                name=request.form.get("name", ""),
                description=request.form.get("description", ""),
            )
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
            return redirect(url_for("projects"))
        session["project_key"] = result["project_key"]
        flash("Draft project workspace created. Upload and commit at least one input to create config/project.json.", "success")
        return redirect(url_for("setup"))

    @app.get("/setup")
    def setup() -> str:
        project_dir = _selected_project_dir_or_none(app)
        if project_dir is None:
            return render_template("empty_project.html", active_page="setup", title="Project Setup")
        return render_template("setup.html", active_page="setup", setup=adapter.setup_status(project_dir))

    @app.post("/setup/upload")
    def upload_inputs() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        uploads = request.files.getlist("files")
        if not uploads or all(not upload.filename for upload in uploads):
            flash("Choose at least one file to upload.", "error")
            return redirect(url_for("setup"))
        saved_count = 0
        for upload in uploads:
            if not upload.filename:
                continue
            try:
                adapter.stage_upload(project_dir, upload)
                saved_count += 1
            except adapter.WebAdapterError as exc:
                flash(str(exc), "error")
        if saved_count:
            flash(f"Staged {saved_count} uploaded file(s).", "success")
        return redirect(url_for("setup"))

    @app.post("/setup/commit")
    def commit_inputs() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            result = adapter.commit_staged_inputs(project_dir)
            flash(f"Committed {result.get('committed_count', 0)} input file(s) and classified project inputs.", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("setup"))

    @app.post("/setup/classify")
    def classify_inputs() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            result = adapter.classify_project_inputs(project_dir)
            flash(f"Input classification completed with {result.get('input_count', 0)} configured input(s).", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("setup"))

    @app.get("/overview")
    def overview() -> str:
        project_dir = _selected_project_dir_or_none(app)
        if project_dir is None:
            return render_template("empty_project.html", active_page="overview", title="Overview")
        summary = adapter.project_summary(project_dir)
        summary["gpt_interpretive_assist"]["ui_enabled"] = bool(session.get("gpt_interpretive_assist_enabled", False))
        return render_template("overview.html", active_page="overview", summary=summary)

    @app.post("/overview/populate")
    def populate() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            result = adapter.run_populate(project_dir)
            flash(f"Create Review Queue completed with {result.get('review_queue_item_count', 0)} review items.", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("overview"))

    @app.post("/overview/gpt-interpretive-assist/toggle")
    def toggle_gpt_interpretive_assist() -> Any:
        _selected_project_dir_or_abort(app)
        enabled = request.form.get("gpt_interpretive_assist_enabled") == "yes"
        session["gpt_interpretive_assist_enabled"] = enabled
        flash("GPT Interpretive Assist controls enabled." if enabled else "GPT Interpretive Assist controls disabled.", "success")
        return redirect(url_for("overview"))

    @app.post("/overview/gpt-interpretive-assist/generate")
    def generate_gpt_interpretive_assist() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        if not session.get("gpt_interpretive_assist_enabled", False):
            flash("Turn on GPT Interpretive Assist before generating GPT drafts.", "error")
            return redirect(url_for("overview"))
        dry_run = "dry_run" in request.form
        if not dry_run:
            status = adapter.project_summary(project_dir).get("gpt_interpretive_assist", {})
            if isinstance(status, dict) and status.get("status") != "ready":
                flash("GPT Interpretive Assist is not ready. Check GPT_DRAFTING and OPENAI_API_KEY before generating drafts.", "error")
                return redirect(url_for("overview"))
        try:
            result = adapter.run_gpt_interpretive_assist(
                project_dir,
                sections=request.form.getlist("sections") or None,
                max_calls=_form_int(request.form.get("max_calls"), default=5),
                dry_run=dry_run,
                skip_existing="skip_existing" in request.form,
                source_backed_only="source_backed_only" in request.form,
                force_refresh="force_refresh" in request.form,
            )
            if result.get("dry_run"):
                flash(f"GPT dry run planned {result.get('planned_call_count', 0)} section draft call(s).", "success")
            else:
                flash(
                    f"GPT Interpretive Assist generated/reused {result.get('accepted_gpt_draft_count', 0)} draft candidate(s); "
                    f"{result.get('rejected_gpt_draft_count', 0)} output(s) were rejected.",
                    "success",
                )
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("overview"))

    @app.post("/overview/reset-review-queue")
    def reset_review_queue() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        if request.form.get("confirm_reset") != "yes":
            flash("Confirm the developer reset before clearing and rebuilding generated review candidates.", "error")
            return redirect(url_for("overview"))
        try:
            result = adapter.reset_generated_review_queue(
                project_dir,
                include_exports="include_exports" in request.form,
            )
            after = result.get("after", {}) if isinstance(result.get("after"), dict) else {}
            flash(f"Review artifacts refreshed and queue rebuilt with {after.get('review_queue_item_count', 0)} review items.", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("overview"))

    @app.get("/review")
    def review_queue() -> str:
        project_dir = _selected_project_dir_or_none(app)
        if project_dir is None:
            return render_template("empty_project.html", active_page="review", title="Review Queue")
        try:
            queue = adapter.review_queue_summary(project_dir)
        except adapter.WebAdapterError as exc:
            return render_template("review.html", active_page="review", queue=None, error=str(exc))
        status_filter = request.args.get("status", "")
        if status_filter:
            queue = {**queue, "items": [item for item in queue["items"] if item["status"] == status_filter]}
        return render_template("review.html", active_page="review", queue=queue, error="")

    @app.get("/review/<item_id>")
    def review_detail(item_id: str) -> str:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            item = adapter.review_item_detail(project_dir, item_id)
        except adapter.WebAdapterError as exc:
            abort(404, str(exc))
        return render_template("review_detail.html", active_page="review", item=item)

    @app.get("/review/<item_id>/figure-style")
    def figure_style_editor(item_id: str) -> str:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            editor = adapter.figure_style_editor_context(project_dir, item_id)
        except adapter.WebAdapterError as exc:
            abort(404, str(exc))
        return render_template("figure_style_editor.html", active_page="review", editor=editor)

    @app.post("/review/<item_id>/figure-style")
    def figure_style_update(item_id: str) -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            result = adapter.save_figure_style_form(project_dir, item_id, request.form)
            if str(request.form.get("style_action") or "") == "reset_default":
                flash(f"Figure style reset to default. {result.get('reset_count', 0)} active draft override(s) reset.", "success")
            elif result.get("override_saved"):
                flash("Draft figure style saved.", "success")
            else:
                flash("No draft style changes were saved; submitted values match defaults.", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("figure_style_editor", item_id=item_id))

    @app.post("/review/<item_id>")
    def review_update(item_id: str) -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        form_kind = str(request.form.get("form_kind") or "")
        try:
            if form_kind == "figure_review":
                adapter.save_figure_review_action(
                    project_dir,
                    item_id,
                    caption=request.form.get("caption"),
                    replacement_file=request.files.get("replacement_figure"),
                    note=request.form.get("note") or None,
                )
            else:
                status = str(request.form.get("status") or "")
                adapter.save_review_action(
                    project_dir,
                    item_id,
                    status=status,
                    note=request.form.get("note") or None,
                    edited_content=request.form.get("edited_content") if status == "edited" else None,
                    replacement_content=request.form.get("replacement_content") if status == "replaced" else None,
                    export_eligible=("export_eligible" in request.form) if status == "unable_to_verify" else None,
                )
            flash("Review item updated.", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("review_detail", item_id=item_id))

    @app.get("/export")
    def export_status() -> str:
        project_dir = _selected_project_dir_or_none(app)
        if project_dir is None:
            return render_template("empty_project.html", active_page="export", title="Export Readiness")
        readiness = adapter.export_readiness(project_dir)
        return render_template("export.html", active_page="export", readiness=readiness)

    @app.post("/export/preview")
    def preview_export() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            result = adapter.run_export(project_dir, preview=True)
            flash(f"Internal preview export created: {result.get('review_gate_status', 'preview_bypassed')}.", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("export_status"))

    @app.post("/export/reviewed")
    def reviewed_export() -> Any:
        project_dir = _selected_project_dir_or_abort(app)
        try:
            result = adapter.run_export(project_dir, preview=False)
            flash(f"Reviewed export created: {result.get('review_gate_status', 'passed')}.", "success")
        except adapter.WebAdapterError as exc:
            flash(str(exc), "error")
        return redirect(url_for("export_status"))

    @app.get("/outputs")
    def outputs() -> str:
        project_dir = _selected_project_dir_or_none(app)
        if project_dir is None:
            return render_template("empty_project.html", active_page="outputs", title="Package Outputs")
        return render_template("outputs.html", active_page="outputs", outputs=adapter.package_outputs(project_dir))

    @app.get("/artifact")
    def artifact() -> Any:
        project_key = request.args.get("project", session.get("project_key", ""))
        relative_path = request.args.get("path", "")
        try:
            project_dir = adapter.resolve_project_dir(app.config["PROJECT_ROOT"], project_key)
            path = adapter.resolve_artifact_path(project_dir, relative_path)
        except adapter.WebAdapterError:
            abort(404)
        return send_file(path, as_attachment=False)

    return app


def _selected_project_ref(app: Flask, project_key: str) -> adapter.ProjectRef | None:
    for project in adapter.list_projects(app.config["PROJECT_ROOT"]):
        if project.project_key == project_key:
            return project
    return None


def _selected_project_dir_or_none(app: Flask) -> Path | None:
    project_key = session.get("project_key")
    if not project_key:
        return None
    try:
        return adapter.resolve_project_dir(app.config["PROJECT_ROOT"], str(project_key))
    except adapter.WebAdapterError:
        session.pop("project_key", None)
        return None


def _selected_project_dir_or_abort(app: Flask) -> Path:
    project_dir = _selected_project_dir_or_none(app)
    if project_dir is None:
        abort(400, "No project selected.")
    return project_dir


def _form_int(value: str | None, *, default: int) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def main() -> None:
    """Run the local development server."""

    app = create_app(project_root=os.environ.get("REVIEW_ASSIST_PROJECT_ROOT"))
    host = os.environ.get("REVIEW_ASSIST_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("REVIEW_ASSIST_WEB_PORT", "8766"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":  # pragma: no cover
    main()
