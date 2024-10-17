from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import io
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'altf4'

def get_database_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Joao0105",
            database="ecomerce"
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



@app.route('/pagamento_pix', methods=['GET'])
def pagamento_pix():
    # Aqui você pode adicionar a lógica para processar o pagamento via PIX
    return render_template('pagamento_pix.html')

@app.route('/pagamento_cartao', methods=['GET'])
def pagamento_cartao():
    # Aqui você pode adicionar a lógica para processar o pagamento via cartão
    return render_template('pagamento_cartao.html')




@app.route('/carrinho')
def ver_carrinho():
    carrinho = session.get('carrinho', [])
    total = sum(item['preco'] * item['quantidade'] for item in carrinho)
    return render_template('carrinho.html', carrinho=carrinho, total=total)

@app.route('/comprar/<int:produto_id>', methods=['POST'])
def adicionar_ao_carrinho(produto_id):
    # Verifica se o usuário está logado
    if 'user_id' not in session:
        flash("Você precisa estar logado para adicionar ao carrinho.", "warning")
        return redirect(url_for('login'))
    
    connection = get_database_connection()
    cursor = connection.cursor(dictionary=True)

    # Busca o produto pelo ID
    cursor.execute("SELECT * FROM PRODUTO WHERE ID_PRODUTO = %s", (produto_id,))
    produto = cursor.fetchone()
    cursor.close()
    connection.close()
    
    # Verifica se o produto foi encontrado
    if not produto:
        flash("Produto não encontrado.", "error")
        return redirect(url_for('index'))
    
    # Inicializa o carrinho se não existir
    if 'carrinho' not in session:
        session['carrinho'] = []

    carrinho = session['carrinho']
    
    # Verifica se o produto já está no carrinho
    for item in carrinho:
        if item['produto_id'] == produto_id:
            item['quantidade'] += 1
            break
    else:
        # Adiciona um novo item ao carrinho
        carrinho.append({
            'produto_id': produto['ID_PRODUTO'],
            'nome': produto['MARCA'],
            'preco': produto['VALOR_PROD'],
            'quantidade': 1
        })
    
    # Atualiza a sessão com o carrinho modificado
    session['carrinho'] = carrinho
    flash(f"{produto['MARCA']} foi adicionado ao carrinho.", "success")
    
    # Redireciona para a página do carrinho
    return redirect(url_for('ver_carrinho'))  # Substitua 'ver_carrinho' pelo nome da rota do carrinho



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
    
    session.pop('carrinho', None)  # Limpa o carrinho
    flash("Compra finalizada com sucesso!", "success")
    session['carrinho'] = []  # Limpa o carrinho
    return redirect(url_for('index'))

@app.route('/remover_do_carrinho/<int:produto_id>', methods=['POST'])
def remover_do_carrinho(produto_id):
    if 'carrinho' in session:
        carrinho = session['carrinho']
        session['carrinho'] = [item for item in carrinho if item['produto_id'] != produto_id]
        flash("Produto removido do carrinho.", "success")
    else:
        flash("Carrinho está vazio.", "warning")
    
    return redirect(url_for('ver_carrinho'))  # Redireciona para a página do carrinho


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
            return redirect(url_for('index'))
        else:
            flash('Email ou senha inválidos!', 'error')

    return render_template('login.html')

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
                'INSERT INTO CLIENTE (NOME, EMAIL, TELEFONE, CPF, SENHA, PERFIL) VALUES (%s, %s, %s, %s, %s, %s)',
                (nome, email, telefone, cpf, senha_hash, 0)
            )
            conn.commit()
            flash('Registro bem-sucedido! Você pode fazer login agora.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Email ou CPF já registrado. Escolha outro.', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')


def obter_carrinho():
    # Supondo que o carrinho seja armazenado na sessão
    return session.get('carrinho', [])

# Função para calcular o total do carrinho
def calcular_total(carrinho):
    total = 0
    for item in carrinho:
        total += item['preco'] * item['quantidade']  # Calcula o total baseado no preço e quantidade
    return total

@app.route('/compra', methods=['GET', 'POST'])
def compra():
    carrinho = obter_carrinho()  # Obtém os itens do carrinho
    total_geral = calcular_total(carrinho)  # Calcula o total
    return render_template('compra.html', carrinho=carrinho, total_geral=total_geral)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Você saiu com sucesso!', 'success')
    return redirect(url_for('login'))

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

if __name__ == '__main__':
    app.run(debug=True)
