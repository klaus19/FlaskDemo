from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookmarks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Needed for flash messages

db = SQLAlchemy(app)


# Database Model
class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    tags = db.Column(db.String(200), default='')

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "tags": self.tags.split(',') if self.tags else []
        }


# Create tables
with app.app_context():
    db.create_all()


# Helper function to get tags with counts
def get_tags_with_counts():
    bookmarks = Bookmark.query.all()
    tag_count = {}
    for bookmark in bookmarks:
        if bookmark.tags:
            for tag in bookmark.tags.split(','):
                tag = tag.strip()
                if tag:
                    tag_count[tag] = tag_count.get(tag, 0) + 1
    sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
    return [{"name": tag, "count": count} for tag, count in sorted_tags]


# ============ HTML PAGES ============

@app.route('/')
def home_page():
    bookmarks = Bookmark.query.all()
    tags = get_tags_with_counts()
    return render_template('index.html', bookmarks=[b.to_dict() for b in bookmarks], tags=tags)


@app.route('/add', methods=['GET', 'POST'])
def add_page():
    if request.method == 'POST':
        url = request.form.get('url')
        title = request.form.get('title')
        tags = request.form.get('tags', '')

        if not url or not title:
            flash('URL and Title are required!', 'error')
            return redirect(url_for('add_page'))

        # Clean up tags
        tags_clean = ','.join([t.strip() for t in tags.split(',') if t.strip()])

        bookmark = Bookmark(url=url, title=title, tags=tags_clean)
        db.session.add(bookmark)
        db.session.commit()

        flash('Bookmark added successfully!', 'success')
        return redirect(url_for('home_page'))

    return render_template('add.html')


@app.route('/edit/<int:bookmark_id>', methods=['GET', 'POST'])
def edit_page(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)

    if request.method == 'POST':
        bookmark.url = request.form.get('url')
        bookmark.title = request.form.get('title')
        tags = request.form.get('tags', '')
        bookmark.tags = ','.join([t.strip() for t in tags.split(',') if t.strip()])

        db.session.commit()
        flash('Bookmark updated successfully!', 'success')
        return redirect(url_for('home_page'))

    return render_template('add.html', bookmark=bookmark.to_dict())


@app.route('/delete/<int:bookmark_id>', methods=['POST'])
def delete_bookmark_form(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)
    db.session.delete(bookmark)
    db.session.commit()
    flash('Bookmark deleted!', 'success')
    return redirect(url_for('home_page'))


@app.route('/search')
def search_page():
    tag = request.args.get('tag')
    title = request.args.get('title')
    q = request.args.get('q')

    results = None

    # Only search if at least one parameter is provided
    if tag or title or q:
        query = Bookmark.query

        if tag:
            query = query.filter(Bookmark.tags.contains(tag))
        if title:
            query = query.filter(Bookmark.title.ilike(f'%{title}%'))
        if q:
            query = query.filter(
                db.or_(
                    Bookmark.tags.ilike(f'%{q}%'),
                    Bookmark.title.ilike(f'%{q}%'),
                    Bookmark.url.ilike(f'%{q}%')
                )
            )

        results = [b.to_dict() for b in query.all()]

    return render_template('search.html', results=results)


# ============ JSON API (still works!) ============

@app.route('/api/bookmarks', methods=['GET'])
def api_get_bookmarks():
    bookmarks = Bookmark.query.all()
    return jsonify([b.to_dict() for b in bookmarks])


@app.route('/api/bookmarks', methods=['POST'])
def api_add_bookmark():
    data = request.get_json()
    if not data.get('url') or not data.get('title'):
        return jsonify({"error": "url and title are required"}), 400

    bookmark = Bookmark(
        url=data.get('url'),
        title=data.get('title'),
        tags=','.join(data.get('tags', []))
    )
    db.session.add(bookmark)
    db.session.commit()
    return jsonify(bookmark.to_dict()), 201


@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def api_delete_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    if not bookmark:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(bookmark)
    db.session.commit()
    return jsonify({"message": "Deleted"})


if __name__ == '__main__':
    app.run(debug=True)