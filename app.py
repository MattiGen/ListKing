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
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    question = db.relationship('Question', backref=db.backref('answers', lazy=True))


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    categoryID = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('questions', lazy=True))


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    gameID = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=True)
    game = db.relationship('Game', backref=db.backref('category', uselist=False))


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    score = db.Column(db.Integer)
    isFacilitator = db.Column(db.Integer) # Boolean integer
    gameID = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    game = db.relationship('Game', backref=db.backref('players', lazy=True))


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)


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

@app.route('/finalScores/')
def finalScores():
    return render_template('FinalScores.html')

@app.route('/scoreBoard/')
def scoreBoard():
    return render_template('ScoreBoard.html')

@app.route('/createQuest/')
def createQuest():
    return render_template('CreateQuest.html')

# --- HTTP endpoint routes
@app.route('/nextQuestion/', methods=['GET'])
def nextQuestion():
    sse.publish(1, type='nextQuestion')
    return Response(200)

@app.route('/join/<int:gameID>/', methods=['POST'])
def joinGame(gameID):
    username = request.get_json(force=True)
    print(username)
    game = [i for i in Game.query.all() if i.id == int(gameID)][0]
    player = Player(username=username, score=0, isFacilitator=False, game=game)
    db.session.add(player)
    db.session.commit()
    sse.publish(json.dumps(username), type='newPlayer')
    return jsonify(game.category.name)

@app.route('/<int:gameID>/scores/', methods=['GET', 'POST'])
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
        place = [i for i in Player.query.order_by(Player.score).all() if i.game == game].index(player) + 1
        return jsonify(place)

    elif request.method == 'GET': # For showing leaderboard on facilitator screen
        return jsonify([[i.username, i.score] for i in Player.query.order_by(Player.score).all() if i.game==game])



@app.route('/<string:category>/questions/', methods=['GET', 'POST'])
def questions(category):
    try:
        category = [i for i in Category.query.all() if i.name == category][0]
    except IndexError:
        abort(404)

    if request.method == 'GET':

        return jsonify([i.name for i in category.questions])

    if request.method == 'POST':
        name = request.get_json(force=True)
        question = Question(name=name, category=category)
        db.session.add(question)
        db.session.commit()
        return question.name


@app.route('/<string:category>/<string:question>/answers/', methods=['GET', 'POST'])
def answers(category, question):
    """
    API Endpoint: Gets or puts answers
    """
    if request.method == 'GET':
        answers = [i for i in Answer.query.all() if i.question.name == question] # Gets all answers to question
        return jsonify([i.name for i in answers])

    elif request.method == 'POST':
        questions = Question.query.all()
        for i in questions:
            if i.name == question and i.category.name == category:
                names = [i for i in request.get_json(force=True)]
                for i in names:
                    answer = Answer(name=i, question=[j for j in questions if j.name == question][0])
                    db.session.add(answer)
                db.session.commit()
                return jsonify(question)


@app.route('/categories/', methods=['GET', 'POST'])
def categories():
    if request.method == 'GET':
        return jsonify([i.name for i in Category.query.all()])

    else: # method == 'POST'
        category = Category(name=request.get_json(force=True))
        db.session.add(category)
        db.session.commit()
        return category.name


@app.route('/games/', methods=['GET', 'POST'])
def games():
    if request.method == 'POST':
        category = request.get_json(force=True)

        game = Game(category=[i for i in Category.query.all() if i.name == category][0])
        db.session.add(game)
        db.session.commit()
        return jsonify(game.id)

    elif request.method == 'GET':
        games = Game.query.all()
        return jsonify({i.id: i.category for i in games})

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0') # This host represents external ips