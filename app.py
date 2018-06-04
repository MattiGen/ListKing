from flask import Flask, request, jsonify, abort, Response, render_template
from flask_cors import CORS # Inter-OS communication
from flask_sse import sse # Server-sent events
from flask_sqlalchemy import SQLAlchemy # Easy flask -> python -> sqlite interfacing
import json

app = Flask(__name__) # Initialize app
CORS(app) # Initialize CORS
app.config['REDIS_URL'] = 'redis://localhost' # Redis server allows SSE to work (somehow?)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app) # Initialize database
app.register_blueprint(sse, url_prefix='/stream') # Sets URL for server-sent events

# --- Database definitions
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

# --- HTML routes

@app.route('/SSETest/')
def sseTest():
    return render_template('SSETest.html')

@app.route('/pinEnter/')
def pinEnter():
    return render_template('PinEnter.html')

@app.route('/index/')
def index():
    return render_template('index.html')

@app.route('/categoryPick/')
def categoryPick():
    return render_template('CategoryPick.html')

@app.route('/createCat/')
def createCat():
    return render_template('CreateCat.html')

@app.route('/gameEnd/')
def gameEnd():
    return render_template('GameEnd.html')

@app.route('/play/')
def play():
    return render_template('Play.html')

@app.route('/showPin/')
def showPin():
    return render_template('ShowPin.html')

@app.route('/showQuest/')
def showQuest():
    return render_template('ShowQuest.html')

@app.route('/userCat/')
def userCat():
    return render_template('UserCat.html')

@app.route('/waitBefore/')
def waitBefore():
    return render_template('WaitBefore.html')

@app.route('/waitDuring/')
def waitDuring():
    return render_template('WaitDuring.html')

@app.route('/defaultCat/')
def defaultCat():
    return render_template('DefaultCat.html')

# --- HTTP endpoint routes
@app.route('/join/<int:gameID>/', methods=['POST'])
def joinGame(gameID):
    username = request.get_json(force=True)
    player = Player(username=username, score=0, isFacilitator=False, gameID=gameID)
    db.session.add(player)
    db.session.commit()
    sse.publish(json.dumps(username), type='newPlayer')
    game = [i for i in Game.query.all() if i.id == gameID][0]
    return game.category

@app.route('/<int:gameID>/scores', methods=['GET', 'POST'])
def scores(gameID):
    '''
    This endpoint allows us to 1) add updated scores after each question and 2) send the ranked leader board
    '''
    game = [i for i in Game.query.all() if i.id == gameID][0]
    if request.method == 'POST': # Updating score after each question
        jsonRequest = request.get_json(force=True)
        username, score = jsonRequest[0], jsonRequest[1]
        player = [i for i in Player.query.all() if i.username == username][0]
        player.score = score
        db.session.commit()
        place = Player.query.order_by(Player.score).all().index(player) + 1
        return jsonify(place)

    elif request.method == 'GET': # For showing leaderboard on facilitator screen
        return jsonify([{'username': i.username, 'score': i.score} for i in Player.query.order_by(Player.score).all()])



@app.route('/<string:category>/questions', methods=['GET', 'POST'])
def questions(category):
    if request.method == 'GET':
        category = [i for i in Category.query.all() if i.name == category][0]
        return jsonify([i.name for i in category.questions])
    if request.method == 'POST':
        question = Question(name=request.get_json(force=True), category=category)
        db.session.add(question)
        db.session.commit()


@app.route('/<string:category>/<string:question>/answers', methods=['GET', 'POST'])
def answers(category, question):
    """
    API Endpoint: Gets or puts answers
    """
    if request.method == 'GET':
        answers = [i for i in Answer.query.all() if i.question == question] # Gets all answers to question
        return jsonify([i.name for i in answers])

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
        return jsonify([i.name for i in Category.query.all()])

    else: # method == 'POST'
        category = Category(request.get_json(force=True))
        db.session.add(category)
        db.session.commit()


@app.route('/games/', methods=['GET','POST'])
def games():
    if request.method == 'POST':
        category = request.get_json(force=True)

        game = Game(category=category)
        db.session.add(game)
        db.session.commit()
        return jsonify(game.id)

    elif request.method == 'GET':
        games = Game.query.all()
        return jsonify({i.id: i.category for i in games})

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0') # This host represents external ips