import os
from flask import Flask, session, redirect, url_for, flash, request, render_template, send_file, jsonify
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import mysql.connector
from mysql.connector import Error

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("CLIENT_SECRET")

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Produto(db.Model):
    __tablename__ = 'PRODUTO'
    
    ID_PRODUTO = db.Column(db.Integer, primary_key=True)
    VALOR_PROD = db.Column(db.Float, nullable=False)
    QTD_ESTOQUE = db.Column(db.Integer, nullable=False)
    COR = db.Column(db.String(50))
    TAMANHO = db.Column(db.String(50))
    MARCA = db.Column(db.String(100))
    TIPO_TECIDO = db.Column(db.String(100))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

def get_database_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=os.getenv("DB_PORT"),
            unix_socket=None
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


@app.route('/')
def index():
    connection = get_database_connection()
    if connection is None:
        return "Error connecting to database", 500

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM PRODUTO")
    produtos = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('index.html', produtos=produtos)

@app.route('/api/produtos', methods=['GET'])
def filtrar_produtos():
    cor = request.args.get('cor')
    tamanho = request.args.get('tamanho')
    marca = request.args.get('marca')
    valor_min = request.args.get('valor_min', type=float)
    valor_max = request.args.get('valor_max', type=float)
    
    query = Produto.query
    
    if cor:
        query = query.filter(Produto.COR.ilike(f'%{cor}%'))
    if tamanho:
        query = query.filter(Produto.TAMANHO.ilike(f'%{tamanho}%'))
    if marca:
        query = query.filter(Produto.MARCA.ilike(f'%{marca}%'))
    if valor_min is not None:
        query = query.filter(Produto.VALOR_PROD >= valor_min)
    if valor_max is not None:
        query = query.filter(Produto.VALOR_PROD <= valor_max)
    
    produtos = query.all()
    
    resultado = [
        {
            'id_produto': produto.ID_PRODUTO,
            'valor': produto.VALOR_PROD,
            'qtd_estoque': produto.QTD_ESTOQUE,
            'cor': produto.COR,
            'tamanho': produto.TAMANHO,
            'marca': produto.MARCA,
            'tipo_tecido': produto.TIPO_TECIDO
        }
        for produto in produtos
    ]
    
    return jsonify(resultado), 200

@app.route('/pagamento_pix', methods=['GET'])
def pagamento_pix():
    return render_template('pagamento_pix.html')

@app.route('/pagamento_cartao', methods=['GET'])
def pagamento_cartao():
    return render_template('pagamento_cartao.html')

@app.route('/carrinho')
def ver_carrinho():
    carrinho = session.get('carrinho', [])
    total = sum(item['preco'] * item['quantidade'] for item in carrinho)
    return render_template('carrinho.html', carrinho=carrinho, total=total)

@app.route('/comprar/<int:produto_id>', methods=['POST'])
def adicionar_ao_carrinho(produto_id):
    if 'user_id' not in session:
        flash("Você precisa estar logado para adicionar ao carrinho.", "warning")
        return redirect(url_for('login'))
    
    connection = get_database_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM PRODUTO WHERE ID_PRODUTO = %s", (produto_id,))
    produto = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if not produto:
        flash("Produto não encontrado.", "error")
        return redirect(url_for('index'))
    
    if 'carrinho' not in session:
        session['carrinho'] = []

    carrinho = session['carrinho']
    
    for item in carrinho:
        if item['produto_id'] == produto_id:
            item['quantidade'] += 1
            break
    else:
        carrinho.append({
            'produto_id': produto['ID_PRODUTO'],
            'nome': produto['MARCA'],
            'preco': produto['VALOR_PROD'],
            'quantidade': 1
        })
    
    session['carrinho'] = carrinho
    flash(f"{produto['MARCA']} foi adicionado ao carrinho.", "success")
    
    return redirect(url_for('ver_carrinho'))

@app.route('/finalizar', methods=['POST', 'GET'])
def finalizar_compra():
    if 'user_id' not in session:
        flash("Você precisa estar logado para finalizar a compra.", "warning")
        return redirect(url_for('login'))

    cliente_id = session['user_id']
    carrinho = session.get('carrinho', [])
    
    if not carrinho:
        flash("Seu carrinho está vazio.", "warning")
        return redirect(url_for('ver_carrinho'))

    connection = get_database_connection()
    cursor = connection.cursor()

    for item in carrinho:
        query = """
        INSERT INTO PEDIDO (PRODUTO_ID, CLIENTE_ID, QTD_PEDIDO, FORMA_PAGAMENTO, STATUS_PAGAMENTO)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (item['produto_id'], cliente_id, item['quantidade'], 'Não especificado', 'Pendente'))
    
    connection.commit()
    cursor.close()
    connection.close()
    
    session.pop('carrinho', None)
    flash("Compra finalizada com sucesso!", "success")
    session['carrinho'] = []
    return redirect(url_for('index'))

@app.route('/remover_do_carrinho/<int:produto_id>', methods=['POST'])
def remover_do_carrinho(produto_id):
    if 'carrinho' in session:
        carrinho = session['carrinho']
        session['carrinho'] = [item for item in carrinho if item['produto_id'] != produto_id]
        flash("Produto removido do carrinho.", "success")
    else:
        flash("Carrinho está vazio.", "warning")
    
    return redirect(url_for('ver_carrinho'))


@app.route('/atualizar_quantidade/<int:produto_id>', methods=['POST'])
def atualizar_quantidade(produto_id):
    nova_quantidade = int(request.form['quantidade'])
    carrinho = session.get('carrinho', [])
    
    for item in carrinho:
        if item['produto_id'] == produto_id:
            item['quantidade'] = nova_quantidade
            break
    
    session['carrinho'] = carrinho
    flash("Quantidade atualizada.", "success")
    return redirect(url_for('ver_carrinho'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['password']

        conn = get_database_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM CLIENTE WHERE EMAIL = %s', (email,))
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()

        if cliente and check_password_hash(cliente['SENHA'], senha):
            session['user_id'] = cliente['ID_CLIENTE']
            session['perfil'] = cliente['PERFIL']
            flash('Login bem-sucedido!', 'success')
            if cliente['PERFIL'] == 1:
                return redirect(url_for('adicionar_produto'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Email ou senha inválidos!', 'error')

    return render_template('login.html')


@app.route('/adicionar_produto', methods=['GET', 'POST'])
def adicionar_produto():
    if request.method == 'POST':
        if 'adicionar' in request.form:
            marca = request.form['marca']
            valor = float(request.form['valor'])
            imagem = request.files['imagem'].read()
            qtd_estoque = int(request.form.get('qtd_estoque', 0))
            

            try:
                connection = get_database_connection()
                cursor = connection.cursor()
                query = "INSERT INTO PRODUTO (MARCA, VALOR_PROD, IMAGEM, QTD_ESTOQUE) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (marca, valor, imagem, qtd_estoque))
                connection.commit()
                cursor.close()
                connection.close()

                flash('Produto adicionado com sucesso!', 'success')
                return redirect(url_for('adicionar_produto'))
            except Error as e:
                print(f"Erro ao adicionar produto: {e}")
                flash(f"Erro ao adicionar produto: {e}", 'error')

        elif 'remover' in request.form:
            id_produto = int(request.form['id_produto'])

            try:
                connection = get_database_connection()
                cursor = connection.cursor()
                query = "DELETE FROM PRODUTO WHERE ID_PRODUTO = %s"
                cursor.execute(query, (id_produto,))
                connection.commit()
                cursor.close()
                connection.close()

                flash('Produto removido com sucesso!', 'success')
                return redirect(url_for('adicionar_produto'))
            except Error as e:
                print(f"Erro ao remover produto: {e}")
                flash(f"Erro ao remover produto: {e}", 'error')

    try:
        connection = get_database_connection()
        cursor = connection.cursor(dictionary=True)
        query = "SELECT ID_PRODUTO, MARCA, VALOR_PROD, QTD_ESTOQUE FROM PRODUTO"
        cursor.execute(query)
        produtos = cursor.fetchall()
        cursor.close()
        connection.close()
    except Error as e:
        print(f"Erro ao listar produtos: {e}")
        produtos = []

    return render_template('adicionar_produto.html', produtos=produtos)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        cpf = request.form['cpf']
        senha = request.form['password']
        senha_hash = generate_password_hash(senha)

        conn = get_database_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO CLIENTE (NOME, EMAIL, TELEFONE, CPF, SENHA) VALUES (%s, %s, %s, %s, %s)',
                (nome, email, telefone, cpf, senha_hash)
            )
            conn.commit()
            flash('Registro bem-sucedido! Você pode fazer login agora.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError as e:
            if "duplicate" in str(e):
                flash('Email ou CPF já registrado. Escolha outro.', 'error')
            else:
                flash('Erro ao registrar. Tente novamente.', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

def obter_carrinho():
    return session.get('carrinho', [])

def calcular_total(carrinho):
    total = 0
    for item in carrinho:
        total += item['preco'] * item['quantidade']
    return total

@app.route('/compra', methods=['GET', 'POST'])
def compra():
    carrinho = obter_carrinho()
    total_geral = calcular_total(carrinho)
    return render_template('compra.html', carrinho=carrinho, total_geral=total_geral)


@app.route('/imagem/<int:produto_id>')
def mostrar_imagem(produto_id):
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        query = "SELECT imagem FROM PRODUTO WHERE ID_PRODUTO = %s"
        cursor.execute(query, (produto_id,))
        imagem = cursor.fetchone()
        cursor.close()
        connection.close()

        if imagem:
            return send_file(
                io.BytesIO(imagem[0]),
                mimetype='image/jpeg',
                as_attachment=False,
                download_name='imagem.jpg'
            )
        else:
            return "Imagem não encontrada", 404
    except Error as e:
        print(f"Erro ao recuperar imagem: {e}")
        return f"Erro ao recuperar imagem: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)