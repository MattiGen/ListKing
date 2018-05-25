from flask import Flask, request, jsonify, abort, Response, render_template
from models import *
from flask_cors import CORS # Inter-OS communication
from flask_sse import sse # Server-sent events
from flask_sqlalchemy import SQLAlchemy # Easy flask -> python -> sqlite interfacing

app = Flask(__name__) # Initialize app
CORS(app) # Initialize CORS
app.config['REDIS_URL'] = 'redis://localhost' # Redis server allows SSE to work (somehow?)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.register_blueprint(sse, url_prefix='/stream')

# --- Database
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    score = db.Column(db.Integer)
    isFacilitator = db.Column(db.Integer) # Boolean integer
    gameID = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    game = db.relationship('Game', backref=db.backref('players', lazy=True))

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.Text, nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    categoryID = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('questions', lazy=True))

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    question = db.relationship('Question', backref=db.backref('answers', lazy=True))


db.create_all()

# ---
Quiz = QuizData()

@app.route('join/<int:gameID>', methods=['POST'])
def joinGame(gameID):
    username = request.get_json(force=True)
    player = Player(username=username, score=0, isFacilitator=False, gameID=gameID)
    db.session.add(player)
    db.session.commit()
    sse.publish(username, type='newPlayer')

@app.route('/<string:category>/<string:question>/', methods=['GET', 'PUT'])
def answers(category, question):
    """
    API Endpoint: Gets or puts answers
    """
    if request.method == 'GET':
        answers = [i for i in Answer.query.all() if i.question == question] # Gets all answers to question
        return jsonify(answers)

    elif request.method == 'POST':
        questions = Question.query.all()
        for i in questions:
            if i.question == question and i.category == category:
                answer = Answer(request.get_json(force=True), question)
                db.session.add(answer)
                db.session.commit()


@app.route('/categories/', methods=['GET', 'POST'])
def categories():
    if request.method == 'GET':
        return Category.query.all()

    else: # method == 'POST'
        category = Category(request.get_json(force=True))
        db.session.add(category)
        db.session.commit()

@app.route('/addQuestion/', methods=['POST'])
def addToQuestions():
    json_request = request.get_json()
    if not json_request:
        abort(400)# Bad request

    return jsonify(), 201 # Created


@app.route('/games/', methods=['GET','POST'])
def games():
    if request.method == 'POST':
        category = request.get_json(force=True)
        if not category: # TODO: Check that category has questions.
            abort(400)
        else:
            game = Game(category=category)
            db.session.add(game)
            db.session.commit()
            return game.id

    elif request.method == 'GET':
        games = Game.query.all()
        return jsonify({i.id: i.category for i in games})

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0') # This host represents external ips