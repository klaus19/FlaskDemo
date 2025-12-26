from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookmarks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model (like a table schema)
class Bookmark(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    tags = db.Column(db.String(200), default='')  # Store as comma-separated string

    def to_dict(self):
        return {
            "id":self.id,
            "url":self.url,
            "title":self.title,
            "tags":self.tags.split(',') if self.tags else []
        }

# Create tables when app starts
with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return jsonify({"message": "Bookmark API v2 is running!"})


@app.route('/bookmarks', methods=['GET'])
def get_bookmarks():
    bookmarks = Bookmark.query.all()
    return jsonify([b.to_dict() for b in bookmarks])

@app.route('/bookmarks/<int:bookmark_id>', methods=['GET'])
def get_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    if not bookmark:
        return jsonify({"error": "Bookmark not found"}), 404
    return jsonify(bookmark.to_dict())

@app.route('/bookmarks', methods=['POST'])
def add_bookmark():
    data = request.get_json()

    # Validation
    if not data.get('url') or not data.get('title'):
        return jsonify({"error": "url and title are required"}), 400

    bookmark = Bookmark(
        url=data.get('url'),
        title=data.get('title'),
        tags=','.join(data.get('tags', []))  # Convert list to comma-separated string
    )

    db.session.add(bookmark)
    db.session.commit()

    return jsonify(bookmark.to_dict()), 201

@app.route('/bookmarks/<int:bookmark_id>', methods=['PUT'])
def update_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    if not bookmark:
        return jsonify({"error": "Bookmark not found"}), 404

    data = request.get_json()
    bookmark.url = data.get('url', bookmark.url)
    bookmark.title = data.get('title', bookmark.title)
    if 'tags' in data:
        bookmark.tags = ','.join(data.get('tags', []))

    db.session.commit()

    return jsonify(bookmark.to_dict())

@app.route('/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def delete_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    if not bookmark:
        return jsonify({"error": "Bookmark not found"}), 404

    db.session.delete(bookmark)
    db.session.commit()

    return jsonify({"message": "Bookmark deleted successfully"})

# ============ NEW SEARCH ENDPOINTS ============

@app.route('/bookmarks/search', methods=['GET'])
def search_bookmarks():
    """
    Search bookmarks by tag, title, or URL
    Usage:
      /bookmarks/search?tag=python
      /bookmarks/search?title=react
      /bookmarks/search?url=github
      /bookmarks/search?q=python  (searches all fields)
    """
    tag = request.args.get('tag')
    title = request.args.get('title')
    url = request.args.get('url')
    q = request.args.get('q')  # General search

    query = Bookmark.query

    # Search by tag
    if tag:
        query = query.filter(Bookmark.tags.contains(tag))

    # Search by title (case-insensitive)
    if title:
        query = query.filter(Bookmark.title.ilike(f'%{title}%'))

    # Search by URL
    if url:
        query = query.filter(Bookmark.url.ilike(f'%{url}%'))

    # General search (searches all fields)
    if q:
        query = query.filter(
            db.or_(
                Bookmark.tags.ilike(f'%{q}%'),
                Bookmark.title.ilike(f'%{q}%'),
                Bookmark.url.ilike(f'%{q}%')
            )
        )

    bookmarks = query.all()
    return jsonify({
        "count": len(bookmarks),
        "results": [b.to_dict() for b in bookmarks]
    })


@app.route('/tags', methods=['GET'])
def get_all_tags():
    """
    Get all unique tags with their count
    """
    bookmarks = Bookmark.query.all()
    tag_count = {}

    for bookmark in bookmarks:
        if bookmark.tags:
            for tag in bookmark.tags.split(','):
                tag = tag.strip()
                if tag:
                    tag_count[tag] = tag_count.get(tag, 0) + 1

    # Sort by count (most used first)
    sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)

    return jsonify({
        "total_tags": len(sorted_tags),
        "tags": [{"name": tag, "count": count} for tag, count in sorted_tags]
    })


@app.route('/bookmarks/tag/<string:tag_name>', methods=['GET'])
def get_bookmarks_by_tag(tag_name):
    """
    Get all bookmarks with a specific tag
    Usage: /bookmarks/tag/python
    """
    bookmarks = Bookmark.query.filter(Bookmark.tags.contains(tag_name)).all()

    return jsonify({
        "tag": tag_name,
        "count": len(bookmarks),
        "bookmarks": [b.to_dict() for b in bookmarks]
    })




if __name__ == '__main__':
    app.run(debug=True)