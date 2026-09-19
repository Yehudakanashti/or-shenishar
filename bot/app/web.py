"""הדשבורד המקומי. רץ על המחשב שלכם, ללא שום דבר בענן."""
import json
import uuid
from pathlib import Path

from flask import (
    Flask, abort, flash, redirect, render_template, request, send_from_directory, url_for,
)

from . import ai, db, engine
from .config import (
    ALLOWED_IMAGE_EXT, CLAUDE_MODEL, DEFAULT_SETTINGS, MAX_IMAGE_BYTES,
    UPLOAD_DIR, ai_enabled, facebook_enabled,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "local-dashboard"  # שרת מקומי בלבד; אין כאן סודות
    app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES

    @app.context_processor
    def globals_for_templates() -> dict:
        return {
            "business": db.business(),
            "ai_on": ai_enabled(),
            "fb_on": facebook_enabled(),
            "model": CLAUDE_MODEL,
            "auto_mode": db.get_setting("auto_mode", "off") == "on",
            "kill_switch": db.setting_bool("kill_switch"),
            "pending_count": db.stats()["pending"],
            "intent_labels": ai.INTENT_LABELS,
            "sensitivity_labels": ai.SENSITIVITY_LABELS,
        }

    # ---------- תור האישורים ----------

    @app.get("/")
    def queue():
        pending = db.list_suggestions("pending", limit=60)
        pending.sort(key=lambda s: (not s["relevant"], -s["confidence"]))
        return render_template("queue.html", suggestions=pending, stats=db.stats(),
                               used_today=db.suggestions_today(), cap=db.setting_int("daily_cap", 12))

    @app.post("/ingest")
    def ingest():
        result = engine.ingest(
            text=request.form.get("text", ""),
            group_name=request.form.get("group_name", ""),
            author_name=request.form.get("author_name", ""),
            url=request.form.get("url", ""),
        )
        if not result["ok"]:
            flash(f"{result['reason']} — {result['detail']}", "warn")
            return redirect(url_for("queue"))
        if not result.get("relevant", True):
            flash("הבוט סבור שהפוסט לא רלוונטי. ההצעה בתור, ואפשר לאשר בכל זאת.", "warn")
        return redirect(url_for("suggestion", suggestion_id=result["suggestion_id"]))

    @app.get("/s/<int:suggestion_id>")
    def suggestion(suggestion_id: int):
        item = db.get_suggestion(suggestion_id)
        if not item:
            abort(404)
        return render_template("suggestion.html", s=item, products=db.list_products(active_only=True))

    @app.post("/s/<int:suggestion_id>/approve")
    def approve(suggestion_id: int):
        engine.approve(suggestion_id, request.form.get("comment", ""), request.form.get("dm", ""))
        flash("אושר. הטקסט מוכן להעתקה למטה.", "ok")
        return redirect(url_for("suggestion", suggestion_id=suggestion_id))

    @app.post("/s/<int:suggestion_id>/reject")
    def reject(suggestion_id: int):
        engine.reject(suggestion_id, request.form.get("reason", ""))
        flash("ההצעה נדחתה ולא תוצע שוב לאותו פוסט.", "ok")
        return redirect(url_for("queue"))

    @app.post("/s/<int:suggestion_id>/media")
    def change_media(suggestion_id: int):
        product_id = request.form.get("product_id", type=int)
        image_id = request.form.get("image_id", type=int)
        db.update_suggestion_media(suggestion_id, product_id or None, image_id or None)
        flash("המוצר והתמונה עודכנו.", "ok")
        return redirect(url_for("suggestion", suggestion_id=suggestion_id))

    # ---------- מוצרים ----------

    @app.get("/products")
    def products():
        return render_template("products.html", products=db.list_products())

    @app.get("/products/new")
    def product_new():
        return render_template("product_form.html", product=None)

    @app.get("/products/<int:product_id>")
    def product_edit(product_id: int):
        product = db.get_product(product_id)
        if not product:
            abort(404)
        return render_template("product_form.html", product=product)

    @app.post("/products/save")
    def product_save():
        product_id = request.form.get("id", type=int)
        keywords = [k.strip() for k in request.form.get("keywords", "").replace("\n", ",").split(",") if k.strip()]
        data = {
            "slug": request.form.get("slug", "").strip() or f"product-{uuid.uuid4().hex[:6]}",
            "name": request.form.get("name", "").strip(),
            "line": request.form.get("line", "memorial"),
            "tagline": request.form.get("tagline", "").strip(),
            "description": request.form.get("description", "").strip(),
            "audience": request.form.get("audience", "").strip(),
            "price_from": request.form.get("price_from", type=int),
            "price_to": request.form.get("price_to", type=int),
            "lead_time": request.form.get("lead_time", "").strip(),
            "shipping": request.form.get("shipping", "").strip(),
            "customization": request.form.get("customization", "").strip(),
            "order_url": request.form.get("order_url", "").strip(),
            "keywords": keywords,
            "occasion": request.form.get("occasion", "").strip(),
            "season_start": request.form.get("season_start", "").strip(),
            "season_end": request.form.get("season_end", "").strip(),
            "notes": request.form.get("notes", "").strip(),
            "active": 1 if request.form.get("active") else 0,
        }
        if not data["name"]:
            flash("חובה למלא שם מוצר.", "warn")
            return redirect(url_for("product_new"))
        new_id = db.upsert_product(data, product_id)
        db.log_event("product_saved", f"נשמר מוצר: {data['name']}")
        flash("המוצר נשמר.", "ok")
        return redirect(url_for("product_edit", product_id=new_id))

    @app.post("/products/<int:product_id>/delete")
    def product_delete(product_id: int):
        db.delete_product(product_id)
        flash("המוצר נמחק.", "ok")
        return redirect(url_for("products"))

    @app.post("/products/<int:product_id>/images")
    def product_images(product_id: int):
        files = request.files.getlist("images")
        added = 0
        for file in files:
            if not file or not file.filename:
                continue
            ext = Path(file.filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXT:
                flash(f"קובץ לא נתמך: {file.filename}", "warn")
                continue
            filename = f"{uuid.uuid4().hex}{ext}"
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            file.save(UPLOAD_DIR / filename)
            db.add_image(product_id, filename, request.form.get("caption", "").strip())
            added += 1
        flash(f"נוספו {added} תמונות." if added else "לא נוספו תמונות.", "ok" if added else "warn")
        return redirect(url_for("product_edit", product_id=product_id))

    @app.post("/images/<int:image_id>/primary")
    def image_primary(image_id: int):
        image = db.get_image(image_id)
        db.set_primary_image(image_id)
        flash("נקבעה תמונה ראשית.", "ok")
        return redirect(url_for("product_edit", product_id=image["product_id"]) if image else url_for("products"))

    @app.post("/images/<int:image_id>/delete")
    def image_delete(image_id: int):
        image = db.get_image(image_id)
        filename = db.delete_image(image_id)
        if filename:
            (UPLOAD_DIR / filename).unlink(missing_ok=True)
        flash("התמונה נמחקה.", "ok")
        return redirect(url_for("product_edit", product_id=image["product_id"]) if image else url_for("products"))

    @app.get("/uploads/<path:filename>")
    def uploads(filename: str):
        return send_from_directory(UPLOAD_DIR, filename)

    # ---------- הגדרות ----------

    @app.get("/settings")
    def settings():
        return render_template(
            "settings.html",
            settings=db.get_settings(),
            defaults=DEFAULT_SETTINGS,
            blocklist=db.list_blocklist(),
            examples=db.list_examples(),
        )

    @app.post("/settings")
    def settings_save():
        for key in DEFAULT_SETTINGS:
            if key in ("auto_mode", "kill_switch", "allow_links_in_comment"):
                db.set_setting(key, "on" if request.form.get(key) else "off")
            elif key in request.form:
                db.set_setting(key, request.form.get(key, "").strip())
        db.log_event("settings_saved", "עודכנו הגדרות")
        flash("ההגדרות נשמרו.", "ok")
        return redirect(url_for("settings"))

    @app.post("/blocklist/add")
    def blocklist_add():
        db.add_block(request.form.get("kind", "keyword"), request.form.get("value", ""), request.form.get("note", ""))
        flash("נוספה החרגה.", "ok")
        return redirect(url_for("settings"))

    @app.post("/blocklist/<int:block_id>/delete")
    def blocklist_delete(block_id: int):
        db.delete_block(block_id)
        return redirect(url_for("settings"))

    @app.post("/examples/add")
    def example_add():
        db.add_example(request.form.get("kind", "comment"), request.form.get("text", ""), origin="manual")
        flash("הדוגמה נוספה. הבוט ילמד ממנה בניסוחים הבאים.", "ok")
        return redirect(url_for("settings"))

    @app.post("/examples/<int:example_id>/delete")
    def example_delete(example_id: int):
        db.delete_example(example_id)
        return redirect(url_for("settings"))

    # ---------- היסטוריה ----------

    @app.get("/history")
    def history():
        events = [dict(e) for e in db.recent_events(200)]
        for event in events:
            try:
                event["payload"] = json.loads(event["payload"])
            except json.JSONDecodeError:
                event["payload"] = {}
        return render_template(
            "history.html",
            events=events,
            decided=db.list_suggestions("approved", 40) + db.list_suggestions("rejected", 40),
        )

    return app
