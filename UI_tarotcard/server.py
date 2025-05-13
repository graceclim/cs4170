from flask import Flask, render_template, request, redirect, url_for, session
import json, random

app = Flask(__name__)
app.secret_key = 'tarotsecret'

with open('data/quiz.json', 'r') as f:
    quiz_data = json.load(f)

with open('data/cards.json', 'r') as f:
    card_data = json.load(f)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/learn/<int:lesson_id>')
def learn(lesson_id):
    if lesson_id > len(card_data):
        return redirect(url_for('ready'))  
    
    viewed = set(session.get('viewed_lessons', []))
    viewed.add(lesson_id)
    session['viewed_lessons'] = list(viewed)

    # Optional: if all 10 lessons viewed, mark as complete
    if len(viewed) == 10:
        session['learn_complete'] = True

    return render_template('learn.html', card=card_data[lesson_id - 1], lesson_id=lesson_id)

@app.route('/ready')
def ready():
    return render_template('ready.html')

@app.route('/quiz/start')
def start_quiz():
    all_indices = list(range(len(quiz_data)))
    random.shuffle(all_indices)
    session['text_order'] = all_indices[:5]  # Pick any 5 random questions (text or mc)

    drag_order = list(range(len(card_data)))
    random.shuffle(drag_order)
    session['drag_order'] = drag_order[:5]

    session['answers'] = {}
    session['drag_score'] = 0
    session['drag_total'] = 0

    return redirect(url_for('quiz', question_num=1))



@app.route('/quiz/<int:question_num>')
def quiz(question_num):
    text_order = session.get('text_order', [])
    
    # ✅ Defensive check: avoid accessing beyond available questions
    if not text_order or question_num > len(text_order):
        return redirect(url_for('drag_quiz'))

    idx = text_order[question_num - 1]
    question = quiz_data[idx]

    return render_template('quiz.html', question=question, question_num=question_num)


@app.route('/submit', methods=['POST'])
def submit():
    answer = request.form.get('answer', '').strip().lower()
    q_num = int(request.form.get('question_num'))
    print(f"[DEBUG] Submitted Q{q_num}: {answer}")

    answers = session.get('answers', {})
    answers[str(q_num)] = answer
    session['answers'] = answers

    if q_num >= len(session.get('text_order', [])):
        return redirect(url_for('drag_quiz'))

    return redirect(url_for('quiz', question_num=q_num + 1))

@app.route('/quiz/drag')
def drag_quiz():
    drag_ids = session.get('drag_order', [])
    cards = [card_data[i] for i in drag_ids]

    # Extract all keywords and shuffle them
    keywords = []
    for card in cards:
        for kw in card['keywords']:
            keywords.append({'text': kw['text'], 'card_name': card['name']})
    random.shuffle(keywords)

    return render_template('drag_quiz.html', cards=cards, shuffled_keywords=keywords)


@app.route('/submit_drag', methods=['POST'])
def submit_drag():
    drag_ids = session.get('drag_order', [])
    cards = [card_data[i] for i in drag_ids]

    raw_answers = request.form.to_dict()
    cleaned_answers = {}

    # Normalize keys and values
    for key, value in raw_answers.items():
        cleaned_key = key.strip()
        cleaned_value = value.strip().lower()
        cleaned_answers[cleaned_key] = cleaned_value

    session['drag_submitted'] = cleaned_answers  # Save for result analysis

    correct = 0
    total = 0
    per_card_feedback = []

    for card in cards:
        expected_keywords = set(kw['text'].strip().lower() for kw in card['keywords'])
        
        # Match all user-submitted answers that belong to this card
        submitted_keywords = {
            val for key, val in cleaned_answers.items()
            if key.startswith(f"{card['name']}_")
        }

        correct_matches = expected_keywords & submitted_keywords
        correct += len(correct_matches)
        total += len(expected_keywords)

        per_card_feedback.append({
            'card': card['name'],
            'correct': len(correct_matches),
            'total': len(expected_keywords)
        })

    session['drag_score'] = correct
    session['drag_total'] = total
    session['drag_feedback'] = per_card_feedback
    session['quiz_complete'] = True 

    return redirect(url_for('result'))

@app.route('/result')
def result():
    answers = session.get('answers', {})
    text_order = session.get('text_order', [])
    score = 0

    # Evaluate only the used questions in text_order
    for i, idx in enumerate(text_order):
        q = quiz_data[idx]
        user_input = answers.get(str(i + 1), '').strip().lower()
        correct_answer = q['correct'].strip().lower()
        if user_input == correct_answer:
            score += 1

    # Drag and drop result
    drag_score = session.get('drag_score', 0)
    drag_total = session.get('drag_total', 0)

    total_score = score + drag_score
    total_possible = len(text_order) + drag_total

    # Prepare drag_feedback
    drag_ids = session.get('drag_order', [])
    cards = [card_data[i] for i in drag_ids]
    drag_feedback = session.get('drag_feedback', [])

    return render_template('result.html',
                           score=total_score,
                           total=total_possible,
                           answers=answers,
                           quiz_data=quiz_data,
                           text_order=text_order,
                           drag_score=drag_score,
                           drag_total=drag_total,
                           drag_feedback=drag_feedback)

@app.route('/fortune/loading')
def fortune_loading():
    return render_template('fortune_loading.html')

@app.route('/fortune')
def fortune():
    import random
    card = random.choice(card_data)
    return render_template('fortune.html', card=card)

if __name__ == '__main__':
    app.run(debug=True)
