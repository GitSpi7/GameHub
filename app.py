from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import subprocess
import uuid
import re

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

# Создаем папку для загрузок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Разрешенные расширения
ALLOWED_EXTENSIONS = {'py'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_code(code):
    # Базовая проверка: запрещаем опасные импорты и встроенные функции
    dangerous = [
        'import os', 'import sys', 'import subprocess', 'import shutil',
        'import socket', 'import pickle', 'import ctypes',
        '__import__', 'eval(', 'exec(', 'open(',
        'file(', 'input(', 'raw_input('
    ]
    code_lower = code.lower()
    for danger in dangerous:
        if danger in code_lower:
            return False
    return True

@app.route('/')
def index():
    games = []
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        if file.endswith('.py'):
            games.append(file)
    return render_template('index.html', games=games)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('Файл не выбран')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        content = file.read().decode('utf-8', errors='ignore')
        if not sanitize_code(content):
            flash('Код содержит запрещенные конструкции')
            return redirect(request.url)
        ext = file.filename.rsplit('.', 1)[1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.seek(0)
        file.save(filepath)
        flash('Игра успешно загружена!')
    else:
        flash('Разрешены только .py файлы')
    return redirect(url_for('index'))

@app.route('/game/<filename>')
def play_game(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        flash('Игра не найдена')
        return redirect(url_for('index'))
    return render_template('game.html', filename=filename)

@app.route('/run/<filename>')
def run_game(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "Игра не найдена", 404
    try:
        result = subprocess.run(
            ['python', filepath],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout + "\n" + result.stderr
        output = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', output)
        return f"<pre>{output}</pre>"
    except subprocess.TimeoutExpired:
        return "<pre>Игра выполнялась слишком долго и была остановлена.</pre>"
    except Exception as e:
        return f"<pre>Ошибка запуска: {str(e)}</pre>"

@app.route('/download/<filename>')
def download_game(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)

